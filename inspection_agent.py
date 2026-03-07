#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
巡检智能体
基于 LangGraph 的故障检测智能体
"""
import os
import json
import pickle
import re
import asyncio
from datetime import datetime
from typing import Annotated, List, Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass

from dotenv import load_dotenv
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

# LangChain/LangGraph 相关
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
import logging

logging.getLogger("neo4j").setLevel(logging.ERROR)

# 从项目根目录加载 .env，保证 RAG_MODE 等配置被正确读取（与 backend 一致）
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


# ===================== 全局 WebSocket 回调 =====================
# 用于让工具函数能够直接发送 WebSocket 消息
_ws_send_callback: Optional[Callable[[str, str, dict], Awaitable[None]]] = None
_main_event_loop: Optional[Any] = None  # 主事件循环引用


def set_ws_callback(callback: Optional[Callable[[str, str, dict], Awaitable[None]]], loop: Optional[Any] = None):
    """设置 WebSocket 发送回调
    
    Args:
        callback: WebSocket 回调函数
        loop: 主事件循环（用于跨线程调用）
    """
    global _ws_send_callback, _main_event_loop
    _ws_send_callback = callback
    _main_event_loop = loop
    # 如果没有提供 loop，尝试获取当前运行的事件循环
    if loop is None:
        try:
            _main_event_loop = asyncio.get_running_loop()
        except RuntimeError:
            _main_event_loop = None


def get_ws_callback() -> Optional[Callable[[str, str, dict], Awaitable[None]]]:
    """获取 WebSocket 发送回调"""
    return _ws_send_callback


def get_main_event_loop() -> Optional[Any]:
    """获取主事件循环引用"""
    return _main_event_loop


# ===================== 数据模型 =====================
@dataclass
class InspectionInput:
    """巡检输入数据"""
    detect_time: str
    part_name: str
    part_position: str
    defect_type: str
    detect_confidence: float = 0.95


class AgentState(TypedDict):
    """智能体状态"""
    messages: Annotated[list, add_messages]
    inspection_input: Optional[Dict[str, Any]]
    analysis_result: Optional[Dict[str, Any]]
    current_node: Optional[str]


# ===================== Neo4j 连接（可选，仅 graph 模式） =====================
# vector 模式下不连接 Neo4j，与 backend / rag_config 使用同一 RAG_MODE
graph_db = None
vector_retriever = None

def _is_vector_rag_mode() -> bool:
    from rag_config import RAG_MODE
    return RAG_MODE == "vector"

if not _is_vector_rag_mode():
    try:
        from langchain_neo4j import Neo4jGraph
        from langchain_community.vectorstores import Neo4jVector
        from langchain_ollama import OllamaEmbeddings
        from langchain_neo4j.vectorstores.neo4j_vector import remove_lucene_chars

        neo4j_uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
        neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "12345678")

        if neo4j_uri.startswith("neo4j://"):
            neo4j_uri = neo4j_uri.replace("neo4j://", "bolt://")

        print(f"🔌 尝试连接 Neo4j: {neo4j_uri}")
        graph_db = Neo4jGraph(
            url=neo4j_uri,
            username=neo4j_username,
            password=neo4j_password
        )
        print("✅ Neo4j 连接成功！")

        try:
            embeddings = OllamaEmbeddings(
                model="mxbai-embed-large:latest",
                base_url="http://localhost:11434",
            )
            vector_index = Neo4jVector.from_existing_graph(
                embeddings,
                url=neo4j_uri,
                username=neo4j_username,
                password=neo4j_password,
                search_type="hybrid",
                node_label="Document",
                text_node_properties=["text"],
                embedding_node_property="embedding"
            )
            vector_retriever = vector_index.as_retriever()
            print("✅ 向量检索初始化成功！")
        except Exception as e:
            print(f"⚠️ 向量检索初始化失败: {e}")

    except Exception as e:
        print(f"⚠️ Neo4j 连接失败（将使用模拟数据）: {e}")
else:
    print("📌 RAG_MODE=vector，跳过 Neo4j 连接")


# ===================== LLM 初始化 =====================
base_url = os.getenv("OPENAI_BASE_URL")
api_key = os.getenv("OPENAI_API_KEY")
model_name = os.getenv("OPENAI_MODEL", "gpt-4")

llm = ChatOpenAI(
    base_url=base_url,
    api_key=api_key,
    temperature=0,
    model=model_name
)


# ===================== 工具函数 =====================
def clean_json_output(raw_output: str) -> str:
    """清理大模型输出的 JSON 字符串"""
    if not isinstance(raw_output, str):
        raise TypeError("输入必须为字符串类型")

    cleaned = raw_output.strip()
    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'```\s*$', '', cleaned)
    cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
    cleaned = re.sub(r'(?<!\\)\'', '"', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).replace(' }', '}').replace(' ]', ']')

    try:
        json.loads(cleaned)
        return cleaned
    except json.JSONDecodeError:
        return "{}"


def generate_full_text_query(input_text: str) -> str:
    """生成 Neo4j 全文检索查询"""
    try:
        words = [el for el in remove_lucene_chars(input_text).split() if el]
        if not words:
            return ""
        return " AND ".join([f"{word}~2" for word in words])
    except:
        return input_text


def graph_retriever(question: str) -> str:
    """基于问题检索 Neo4j 图谱中的关系。这里涉及RAG（图谱检索）。"""
    if graph_db is None:
        return "【模拟数据】未连接知识图谱，返回模拟检索结果。"

    result = ""
    try:
        # 简单的图谱查询
        cypher_query = """
        MATCH (n)-[r]->(m)
        WHERE n.id CONTAINS $keyword OR m.id CONTAINS $keyword
        RETURN n.id + ' - ' + type(r) + ' -> ' + m.id AS output
        LIMIT 20
        """
        response = graph_db.query(cypher_query, {"keyword": question[:20]})
        result = "\n".join([el['output'] for el in response])
    except Exception as e:
        print(f"⚠️ 图谱检索异常: {e}")
        result = f"检索异常: {e}"

    result = result if result else "未找到相关图谱数据"
    # RAG：将图谱检索结果输出到控制台
    print("\n" + "=" * 60 + "\n[RAG] 图谱检索 (inspection_agent)")
    print(f"[RAG] 检索 query: {question}")
    print(f"[RAG] 图谱检索结果长度: {len(result)} 字符")
    print("[RAG] 图谱检索结果内容:\n" + result + "\n" + "=" * 60)
    return result


def full_retriever(question: str) -> str:
    """混合检索（图谱 + 向量）。这里涉及RAG（混合检索）。"""
    # 这里涉及RAG：图谱检索
    graph_data = graph_retriever(question)

    # 这里涉及RAG：向量检索
    vector_data = []
    if vector_retriever is not None:
        try:
            vector_data = [el.page_content for el in vector_retriever.invoke(question)]
        except Exception as e:
            print(f"⚠️ 向量检索失败: {e}")

    combined = f"""图谱数据:
{graph_data}

向量数据:
{"#Document ".join(vector_data) if vector_data else "无向量检索结果"}
"""
    # RAG：将混合检索结果输出到控制台
    print("\n" + "=" * 60 + "\n[RAG] 混合检索（图谱 + 向量） (inspection_agent)")
    print(f"[RAG] 检索 query: {question}")
    print(f"[RAG] 图谱部分长度: {len(graph_data)} 字符, 向量文档数: {len(vector_data)}")
    print("[RAG] 混合检索结果全文:\n" + combined + "=" * 60 + "\n")
    return combined


# ===================== 工具定义 =====================
@tool
def prepare_inspection_form(
    part_name: str = "辅助逆变器",
    defect_type: str = "显黄",
    part_position: str = "0116车",
    detect_time: str = "2025-11-23 10:30",
    detect_confidence: float = 0.95
) -> str:
    """唤醒故障检测工单表单，当用户想要进行故障排查、巡检、检测时必须调用此工具。

    Args:
        part_name: 部件名称，如"辅助逆变器"、"轴承"、"制动器"
        defect_type: 缺陷类型，如"显黄"、"温度异常"、"振动过大"
        part_position: 部件位置，如"0116车"、"A轴"、"前转向架"
        detect_time: 检测时间
        detect_confidence: 检测置信度，0到1之间
    """
    import asyncio
    
    # 如果检测时间为空，使用当前时间
    if not detect_time:
        detect_time = datetime.now().strftime("%Y-%m-%dT%H:%M")
    
    # 构建预填充数据
    prefill_data = {
        "part_name": part_name,
        "part_position": part_position,
        "defect_type": defect_type,
        "detect_time": detect_time,
        "detect_confidence": detect_confidence
    }
    
    # 通过 WebSocket 向前端发送激活工单的消息
    callback = get_ws_callback()
    if callback:
        # 在同步函数中调用异步回调
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(callback("tool", "activate_form", {
                "form_type": "fault_input",
                "message": "请填写故障信息以进行分析",
                "prefill_data": prefill_data
            }))
        except RuntimeError:
            # 如果没有运行中的事件循环，创建新的
            asyncio.run(callback("tool", "activate_form", {
                "form_type": "fault_input",
                "message": "请填写故障信息以进行分析",
                "prefill_data": prefill_data
            }))
    
    # 返回给 LLM 的消息
    return "已激活故障检测工单表单，请用户在右侧面板填写信息后提交。"


@tool
def run_fault_analysis(
    part_name: str,
    defect_type: str,
    part_position: str = "",
    detect_time: str = "",
    detect_confidence: float = 0.95
) -> str:
    """执行故障分析，基于故障信息进行知识库检索和智能分析。用户提交工单后调用此工具。

    Args:
        part_name: 部件名称，如"轴承"、"辅助逆变器"
        defect_type: 缺陷类型，如"温度异常"、"显黄"
        part_position: 部件位置，如"0116车"
        detect_time: 检测时间
        detect_confidence: 检测置信度
    """
    import asyncio
    import threading
    import concurrent.futures
    
    if not detect_time:
        detect_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 获取 WebSocket 回调和主事件循环
    callback = get_ws_callback()
    main_loop = get_main_event_loop()
    
    if callback:
        # 创建一个线程安全的回调包装器
        def make_thread_safe_callback(original_callback, loop):
            """创建线程安全的回调包装器，将回调调度到主事件循环"""
            async def safe_callback(msg_type: str, action: str, data: dict):
                if loop and loop.is_running():
                    # 使用 run_coroutine_threadsafe 将回调调度到主事件循环
                    future = asyncio.run_coroutine_threadsafe(
                        original_callback(msg_type, action, data),
                        loop
                    )
                    try:
                        # 等待完成，设置超时避免死锁
                        future.result(timeout=30)
                    except concurrent.futures.TimeoutError:
                        print(f"⚠️ 回调超时: {action}")
                    except Exception as e:
                        print(f"⚠️ 回调异常: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    # 如果没有主事件循环，尝试在当前事件循环中运行
                    try:
                        await original_callback(msg_type, action, data)
                    except Exception as e:
                        print(f"⚠️ 直接回调异常: {e}")
            return safe_callback
        
        # 在独立线程中运行异步分析任务
        def run_in_thread():
            # 创建线程安全的回调
            safe_callback = make_thread_safe_callback(callback, main_loop)
            
            # 创建新的事件循环用于后台线程
            thread_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(thread_loop)
            try:
                thread_loop.run_until_complete(_run_analysis_task(
                    safe_callback, part_name, defect_type, part_position, detect_time, detect_confidence
                ))
            except Exception as e:
                print(f"❌ 后台分析线程异常: {e}")
                import traceback
                traceback.print_exc()
            finally:
                thread_loop.close()
        
        # 启动后台线程（不阻塞当前执行）
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
        print(f"🚀 故障分析任务已在后台启动 (线程: {thread.name})")
    
    # 立即返回给 LLM 的消息（不等待分析完成）
    return "已开启巡检故障分析，你可以提醒用户进行等待，并关注执行面板的故障分析任务的执行情况，同时提示用户任务是后台进行的，此时仍然可以进行其他交互"


async def _run_analysis_task(callback, part_name: str, defect_type: str, part_position: str, detect_time: str, detect_confidence: float):
    """后台执行的分析任务"""
    try:
        # 发送分析开始消息 - 前端切换到分析视图
        await callback("tool", "analysis_start", {
            "message": "正在启动故障分析任务...",
            "input": {
                "part_name": part_name,
                "defect_type": defect_type,
                "part_position": part_position,
                "detect_time": detect_time,
                "detect_confidence": detect_confidence
            }
        })
        
        try:
            # 根据 RAG_MODE 选择故障分析模块：graph=知识图谱+向量，vector=纯向量文档 RAG
            rag_mode = os.getenv("RAG_MODE", "graph").strip().lower()
            if rag_mode not in ("graph", "vector"):
                rag_mode = "graph"
            if rag_mode == "vector":
                from fault_analysis_core_vector import run_fault_analysis_async, initialize
                init_msg = "请检查向量数据库与 LLM 配置"
            else:
                from fault_analysis_core import run_fault_analysis_async, initialize
                init_msg = "请检查 Neo4j 连接和 LLM 配置"

            if not initialize():
                await callback("tool", "analysis_error", {
                    "error": "故障分析模块初始化失败",
                    "message": init_msg
                })
                await _run_simplified_analysis(callback, part_name, defect_type, part_position, detect_time, detect_confidence)
                return

            result = await run_fault_analysis_async(
                detect_time=detect_time,
                part_name=part_name,
                part_position=part_position,
                defect_type=defect_type,
                detect_confidence=detect_confidence,
                ws_callback=callback
            )
            
            # 发送最终结果
            await callback("tool", "analysis_complete", {
                "final_report": result.final_report,
                "retry_count": result.retry_count,
                "thinking_processes": result.thinking_processes,
                "input": {
                    "part_name": part_name,
                    "defect_type": defect_type,
                    "part_position": part_position,
                    "detect_time": detect_time,
                    "detect_confidence": detect_confidence
                },
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
        except ImportError as e:
            # 如果无法导入 fault_analysis_core，使用简化的本地分析
            print(f"⚠️ 无法加载故障分析模块: {e}，使用简化模式")
            await _run_simplified_analysis(callback, part_name, defect_type, part_position, detect_time, detect_confidence)
            
    except Exception as e:
        print(f"❌ 分析任务异常: {e}")
        await callback("tool", "analysis_error", {
            "error": str(e),
            "message": f"分析过程出错: {e}"
        })


async def _run_simplified_analysis(callback, part_name: str, defect_type: str, part_position: str, detect_time: str, detect_confidence: float):
    """简化的故障分析（当 fault_analysis_core 不可用时）"""
    import asyncio
    
    # 模拟分析步骤
    steps = [
        {"node": "retrieval", "title": "知识检索", "summary": f"正在检索 {part_name} 相关知识..."},
        {"node": "extraction", "title": "信息提取", "summary": f"提取 {defect_type} 相关实体..."},
        {"node": "fault_analysis", "title": "故障分析", "summary": "分析潜在故障原因..."},
        {"node": "maintenance", "title": "维护建议", "summary": "生成维护建议..."},
    ]
    
    for step in steps:
        await callback("tool", "analysis_step", {
            "node": step["node"],
            "title": step["title"],
            "summary": step["summary"],
            "status": "running"
        })
        await asyncio.sleep(0.5)  # 模拟处理时间
        await callback("tool", "analysis_step", {
            "node": step["node"],
            "title": step["title"],
            "summary": step["summary"],
            "status": "complete"
        })
    
    # 生成简化报告
    report = f"""# 故障分析报告（简化模式）

## 一、故障基本信息

| 项目 | 内容 |
|------|------|
| 检测时间 | {detect_time} |
| 部件名称 | {part_name} |
| 部件位置 | {part_position or '未指定'} |
| 缺陷类型 | {defect_type} |
| 检测置信度 | {detect_confidence:.0%} |

## 二、初步分析

基于输入信息，系统检测到 **{part_name}** 存在 **{defect_type}** 异常。

## 三、建议措施

1. 安排专业人员现场检查
2. 记录详细故障现象
3. 根据检查结果制定维修方案

---
*报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*注：完整分析需要连接知识图谱数据库*
"""
    
    await callback("tool", "analysis_complete", {
        "final_report": report,
        "retry_count": 0,
        "thinking_processes": steps,
        "input": {
            "part_name": part_name,
            "defect_type": defect_type,
            "part_position": part_position,
            "detect_time": detect_time,
            "detect_confidence": detect_confidence
        },
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


# ===================== 巡检智能体类 =====================
class InspectionAgent:
    """巡检智能体 - 使用 ReAct 模式"""

    def __init__(self):
        self.tools = [prepare_inspection_form, run_fault_analysis]
        self.graph = self._build_graph()
        self.send_callback: Optional[Callable[[str, str, dict], Awaitable[None]]] = None

    def _build_graph(self):
        """构建 ReAct Agent 图 - 只有一个 agent 节点"""
        from langgraph.prebuilt import create_react_agent
        
        # 系统提示 - 更明确地要求使用工具
        system_prompt = """你是一个轨道交通巡检智能助手。你必须使用工具来完成任务。

【重要】当用户提到以下任何关键词时，你必须立即调用 prepare_inspection_form 工具：
- 故障、检测、巡检、排查、缺陷、异常、维修、维护、检查、分析、诊断
- 温度异常、振动、噪音、磨损、松动、裂纹、显黄

你有以下工具：
1. prepare_inspection_form: 唤醒故障检测工单表单。当用户想要进行故障排查时必须调用此工具。
2. run_fault_analysis: 执行故障分析，进行知识库检索。

【工作流程】
1. 用户表达故障排查意图 → 必须调用 prepare_inspection_form
2. 从用户描述中提取信息填入工具参数（part_name, defect_type, part_position等）
3. 如果用户没有提供具体信息，使用默认值调用工具

现在，请根据用户输入决定是否调用工具。如果用户提到任何与故障、检测、巡检相关的内容，你必须调用 prepare_inspection_form 工具。"""

        # 创建 ReAct Agent
        return create_react_agent(
            model=llm,
            tools=self.tools,
            prompt=system_prompt
        )

    def get_graph_structure(self) -> Dict[str, Any]:
        """获取图结构信息 - ReAct Agent 结构"""
        return {
            "name": "巡检智能体",
            "type": "react_agent",
            "level": 0,
            "nodes": [
                {
                    "id": "__start__",
                    "name": "START",
                    "type": "start",
                    "level": 0,
                    "description": "图执行的起始点"
                },
                {
                    "id": "agent",
                    "name": "ReAct Agent",
                    "type": "react",
                    "level": 0,
                    "description": "ReAct 智能体节点，接入2个工具",
                    "tools": ["prepare_inspection_form", "run_fault_analysis"]
                },
                {
                    "id": "__end__",
                    "name": "END",
                    "type": "end",
                    "level": 0,
                    "description": "图执行的结束点"
                }
            ],
            "edges": [
                {"from": "__start__", "to": "agent", "type": "direct", "label": ""},
                {"from": "agent", "to": "agent", "type": "conditional", "label": "工具调用循环"},
                {"from": "agent", "to": "__end__", "type": "conditional", "label": "完成"}
            ],
            "statistics": {
                "node_count": 3,
                "edge_count": 3,
                "tool_count": 2
            }
        }

    def get_tools_info(self) -> List[Dict[str, Any]]:
        """获取工具信息"""
        return [
            {
                "id": "prepare_inspection_form",
                "name": "prepare_inspection_form",
                "description": "需求完善工具 - 唤醒前端的故障检测工单表单，预填充故障信息"
            },
            {
                "id": "run_fault_analysis",
                "name": "run_fault_analysis",
                "description": "执行故障分析，基于输入的故障信息进行检索和分析"
            }
        ]

    async def process_message(
        self,
        message: str,
        send_callback: Callable[[str, str, dict], Awaitable[None]]
    ):
        """处理用户消息"""
        import asyncio
        
        self.send_callback = send_callback
        
        # 获取当前运行的事件循环（主事件循环）
        try:
            main_loop = asyncio.get_running_loop()
        except RuntimeError:
            main_loop = None
        
        # 设置全局 WebSocket 回调和主事件循环，让工具函数可以直接发送消息
        set_ws_callback(send_callback, main_loop)

        # ReAct Agent 使用简单的消息输入
        inputs = {"messages": [HumanMessage(content=message)]}

        # 流式执行图（使用异步流式执行以支持异步工具）
        try:
            async for chunk in self.graph.astream(inputs):
                for node_name, node_output in chunk.items():
                    # 发送节点开始消息
                    await send_callback("system", "node_start", {
                        "node": node_name,
                        "message": f"执行节点: {node_name}"
                    })

                    # 处理消息
                    if "messages" in node_output:
                        for msg in node_output["messages"]:
                            if hasattr(msg, "type"):
                                if msg.type == "ai":
                                    # AI 消息（有内容时才发送）
                                    if msg.content:
                                        await send_callback("chat", "message", {
                                            "type": "ai",
                                            "content": msg.content,
                                            "node": node_name
                                        })

                                    # 检查是否有工具调用
                                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                                        for tool_call in msg.tool_calls:
                                            tool_name = tool_call.get("name", "")
                                            tool_args = tool_call.get("args", {})

                                            await send_callback("tool", "call", {
                                                "tool_name": tool_name,
                                                "tool_args": tool_args,
                                                "node": node_name
                                            })

                                elif msg.type == "tool":
                                    # 工具消息
                                    tool_content = msg.content
                                    tool_name = getattr(msg, "name", "unknown")

                                    await send_callback("tool", "result", {
                                        "tool_name": tool_name,
                                        "content": tool_content,
                                        "node": node_name
                                    })
                                    
                                    # 检查是否有分析结果（run_fault_analysis 工具）
                                    if tool_name == "run_fault_analysis":
                                        try:
                                            result = json.loads(tool_content)
                                            # 发送分析结果消息，前端会展示结果面板
                                            await send_callback("tool", "analysis_result", {
                                                "input": result.get("input", {}),
                                                "retrieval_result": result.get("retrieval_result", ""),
                                                "content": self._generate_analysis_report(result),
                                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                                "risk_level": "中",
                                                "thinking_processes": []
                                            })
                                        except json.JSONDecodeError:
                                            pass

                    # 发送节点完成消息
                    await send_callback("system", "node_complete", {
                        "node": node_name,
                        "message": f"节点 {node_name} 执行完成"
                    })

        except Exception as e:
            await send_callback("system", "error", {
                "error": str(e),
                "message": f"执行出错: {e}"
            })
            raise
        finally:
            # 清除全局回调
            set_ws_callback(None)

    def _generate_analysis_report(self, result: dict) -> str:
        """生成分析报告的 Markdown 内容"""
        input_data = result.get("input", {})
        retrieval_result = result.get("retrieval_result", "未找到相关数据")
        
        report = f"""# 故障分析报告

## 一、故障基本信息

| 项目 | 内容 |
|------|------|
| 检测时间 | {input_data.get('detect_time', '未知')} |
| 部件名称 | {input_data.get('part_name', '未知')} |
| 部件位置 | {input_data.get('part_position', '未知')} |
| 缺陷类型 | {input_data.get('defect_type', '未知')} |
| 检测置信度 | {input_data.get('detect_confidence', 0):.0%} |

## 二、知识库检索结果

{retrieval_result}

## 三、潜在故障原因分析

基于检索到的历史数据和知识图谱，分析可能的故障原因：

1. **设备老化** - 部件长期运行导致性能下降
2. **环境因素** - 温度、湿度等环境条件影响
3. **维护不当** - 维护周期或维护质量问题

## 四、建议维护措施

1. 立即检查{input_data.get('part_name', '相关部件')}状态
2. 核实{input_data.get('defect_type', '异常现象')}的具体表现
3. 根据检查结果制定维修方案
4. 做好维护记录，更新设备档案

## 五、风险提示

⚠️ 建议尽快处理，避免故障扩大影响正常运营。

---
*报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        return report

    async def run_fault_analysis(
        self,
        inspection_input: InspectionInput,
        send_callback: Callable[[str, str, dict], Awaitable[None]]
    ):
        """直接执行故障分析（从表单提交）"""
        # 构造分析消息
        analysis_message = f"""请分析以下故障信息：
- 检测时间：{inspection_input.detect_time}
- 部件名称：{inspection_input.part_name}
- 部件位置：{inspection_input.part_position}
- 缺陷类型：{inspection_input.defect_type}
- 检测置信度：{inspection_input.detect_confidence}

请使用 run_fault_analysis 工具进行详细分析，并给出维护建议。"""

        # 执行分析
        await self.process_message(analysis_message, send_callback)


# ===================== 测试入口 =====================
if __name__ == "__main__":
    import asyncio

    async def test():
        agent = InspectionAgent()

        async def print_callback(msg_type: str, action: str, data: dict):
            print(f"[{msg_type}] {action}: {json.dumps(data, ensure_ascii=False, indent=2)}")

        # 测试消息 - 测试需求完善工具
        print("=" * 50)
        print("测试1: 故障排查意图")
        print("=" * 50)
        await agent.process_message("我想检查一下轴承的温度异常故障", print_callback)

    asyncio.run(test())

