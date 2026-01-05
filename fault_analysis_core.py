#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
故障分析核心模块
从 inspection_analysis_demo.py 抽取的核心分析功能
提供独立的函数接口，可被 inspection_agent.py 或其他模块调用

功能特性：
- 通过 WebSocket 实时推送分析进度和结果
- 支持同步和异步执行
- 支持进度回调
"""
import os
import json
import pickle
import re
import asyncio
from datetime import datetime
from typing import Annotated, List, Dict, Any, Optional, Callable, Awaitable
from typing_extensions import TypedDict
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
import logging

# LangChain/LangGraph 相关
try:
    from langchain_core.pydantic_v1 import BaseModel, Field
except ImportError:
    from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langchain_core.prompts import ChatPromptTemplate

# 禁用 Neo4j 的日志
logging.getLogger("neo4j").setLevel(logging.ERROR)

load_dotenv()


# ===================== WebSocket 消息类型定义 =====================
# 用于前后端交互的消息类型常量
class WSMessageTypes:
    """WebSocket 消息类型"""
    # 分析进度消息
    ANALYSIS_START = "analysis_start"           # 分析开始
    ANALYSIS_COMPLETE = "analysis_complete"     # 分析完成
    
    # 节点执行消息
    NODE_START = "node_start"                   # 节点开始执行
    NODE_PROGRESS = "node_progress"             # 节点执行中（带详细信息）
    NODE_COMPLETE = "node_complete"             # 节点执行完成
    NODE_OUTPUT = "node_output"                 # 节点输出数据
    
    # 思考过程消息
    THINKING_STEP = "thinking_step"             # 思考过程步骤
    
    # 最终报告
    FINAL_REPORT = "final_report"               # 最终故障分析报告
    
    # 错误消息
    ERROR = "error"


# ===================== 前后端交互数据结构 =====================
@dataclass
class NodeProgressData:
    """节点进度数据"""
    node_name: str                    # 节点名称
    node_index: int                   # 节点索引 (1-5)
    total_nodes: int = 5              # 总节点数
    status: str = "running"           # 状态: running, completed, error
    message: str = ""                 # 进度消息
    input_summary: str = ""           # 输入摘要
    output_summary: str = ""          # 输出摘要
    duration: float = 0               # 执行时长（秒）
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ThinkingStepData:
    """思考过程步骤数据"""
    step_index: int                   # 步骤索引
    node_name: str                    # 所属节点
    title: str                        # 步骤标题
    content: str                      # 步骤内容
    timestamp: str = ""               # 时间戳
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%H:%M:%S")
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FinalReportData:
    """最终报告数据"""
    defect_input: Dict[str, Any]              # 故障输入
    extraction_result: Dict[str, Any]         # 提取结果
    fault_analysis_result: Dict[str, Any]     # 故障分析结果
    maintenance_plan_result: Dict[str, Any]   # 维护方案
    report_markdown: str                      # Markdown 格式报告
    retry_count: int                          # 检索次数
    total_duration: float                     # 总耗时（秒）
    timestamp: str = ""                       # 生成时间
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ===================== 全局变量 =====================
_graph_db = None
_vector_retriever = None
_llm = None
_entity_chain = None
_is_initialized = False

# 进度回调函数（通过 WebSocket 发送消息）
_ws_callback: Optional[Callable[[str, str, dict], Awaitable[None]]] = None

# 思考过程步骤计数器
_thinking_step_counter = 0


def set_ws_callback(callback: Optional[Callable[[str, str, dict], Awaitable[None]]]):
    """设置 WebSocket 回调函数"""
    global _ws_callback
    _ws_callback = callback


def get_ws_callback() -> Optional[Callable[[str, str, dict], Awaitable[None]]]:
    """获取 WebSocket 回调函数"""
    return _ws_callback


async def _send_ws_message(action: str, data: dict):
    """发送 WebSocket 消息（如果有回调）"""
    if _ws_callback:
        try:
            await _ws_callback("analysis", action, data)
        except Exception as e:
            print(f"⚠️ WebSocket 消息发送失败: {e}")


async def _send_thinking_step(node_name: str, title: str, content: str):
    """发送思考过程步骤"""
    global _thinking_step_counter
    _thinking_step_counter += 1
    
    step_data = ThinkingStepData(
        step_index=_thinking_step_counter,
        node_name=node_name,
        title=title,
        content=content
    )
    
    await _send_ws_message(WSMessageTypes.THINKING_STEP, step_data.to_dict())


async def _send_node_progress(
    node_name: str, 
    node_index: int, 
    status: str, 
    message: str,
    input_summary: str = "",
    output_summary: str = "",
    duration: float = 0
):
    """发送节点进度消息"""
    progress_data = NodeProgressData(
        node_name=node_name,
        node_index=node_index,
        status=status,
        message=message,
        input_summary=input_summary,
        output_summary=output_summary,
        duration=duration
    )
    
    action = WSMessageTypes.NODE_START if status == "running" else WSMessageTypes.NODE_COMPLETE
    await _send_ws_message(action, progress_data.to_dict())


# ===================== 数据模型 =====================
@dataclass
class FaultInput:
    """故障输入数据"""
    detect_time: str = ""
    part_name: str = ""
    part_position: str = ""
    defect_type: str = ""
    detect_confidence: float = 0.95

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AnalysisResult:
    """分析结果"""
    defect_input: Dict[str, Any]
    retrieval_result: str
    extraction_result: Dict[str, Any]
    fault_analysis_result: Dict[str, Any]
    maintenance_plan_result: Dict[str, Any]
    thinking_processes: List[str]
    final_report: str
    retry_count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class State(TypedDict):
    """LangGraph 状态类型"""
    messages: Annotated[list, add_messages]
    defect_input: Dict[str, Any]
    retrieval_result: str
    extraction_result: Dict[str, Any]
    fault_analysis_result: Dict[str, Any]
    maintenance_plan_result: Dict[str, Any]
    thinking_processes: List[str]
    query_entities: List[str]
    is_info_sufficient: bool
    supplementary_queries: List[str]
    retry_count: int
    max_retry: int


# ===================== 初始化函数 =====================
def initialize(
    neo4j_uri: str = None,
    neo4j_username: str = None,
    neo4j_password: str = None,
    openai_base_url: str = None,
    openai_api_key: str = None,
    openai_model: str = None,
    graph_data_path: str = None
) -> bool:
    """
    初始化故障分析模块
    
    Args:
        neo4j_uri: Neo4j 连接 URI
        neo4j_username: Neo4j 用户名
        neo4j_password: Neo4j 密码
        openai_base_url: OpenAI API Base URL
        openai_api_key: OpenAI API Key
        openai_model: 模型名称
        graph_data_path: 图谱数据文件路径（可选）
    
    Returns:
        bool: 初始化是否成功
    """
    global _graph_db, _vector_retriever, _llm, _entity_chain, _is_initialized

    # 如果已初始化，但提供了图谱数据路径，仍然尝试加载图谱数据
    if _is_initialized:
        if graph_data_path and os.path.exists(graph_data_path) and _graph_db is not None:
            try:
                print(f"📂 正在加载图谱数据（模块已初始化）: {graph_data_path}")
                with open(graph_data_path, "rb") as f:
                    graph_documents = pickle.load(f)
                    _graph_db.add_graph_documents(
                        graph_documents,
                        baseEntityLabel=True,
                        include_source=True
                    )
                print(f"✅ 图谱数据加载成功！")
            except Exception as e:
                print(f"⚠️ 图谱数据加载失败: {e}")
        return True

    # 从环境变量获取配置
    neo4j_uri = neo4j_uri or os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
    neo4j_username = neo4j_username or os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = neo4j_password or os.getenv("NEO4J_PASSWORD", "12345678")
    openai_base_url = openai_base_url or os.getenv("OPENAI_BASE_URL")
    openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
    openai_model = openai_model or os.getenv("OPENAI_MODEL", "gpt-4")

    # 处理 URI 协议
    if neo4j_uri.startswith("neo4j://"):
        neo4j_uri = neo4j_uri.replace("neo4j://", "bolt://")
        print(f"⚠️ 检测到 neo4j:// 协议，已自动转换为 bolt://")

    # 初始化 LLM
    print(f"🔌 正在初始化 LLM...")
    try:
        _llm = ChatOpenAI(
            base_url=openai_base_url,
            api_key=openai_api_key,
            temperature=0,
            model=openai_model
        )
        print(f"✅ LLM 初始化成功！")
    except Exception as e:
        print(f"❌ LLM 初始化失败: {e}")
        return False

    # 初始化 Neo4j 连接
    print(f"🔌 正在连接 Neo4j: {neo4j_uri}")
    try:
        from langchain_neo4j import Neo4jGraph
        _graph_db = Neo4jGraph(
            url=neo4j_uri,
            username=neo4j_username,
            password=neo4j_password
        )
        print(f"✅ Neo4j 连接成功！")

        # 检查并创建全文索引
        _ensure_fulltext_index()

        # 加载图谱数据（如果提供了路径）
        if graph_data_path and os.path.exists(graph_data_path):
            print(f"📂 正在加载图谱数据: {graph_data_path}")
            with open(graph_data_path, "rb") as f:
                graph_documents = pickle.load(f)
                _graph_db.add_graph_documents(
                    graph_documents,
                    baseEntityLabel=True,
                    include_source=True
                )
            print(f"✅ 图谱数据加载成功！")

    except Exception as e:
        print(f"⚠️ Neo4j 连接失败（将使用模拟数据）: {e}")
        _graph_db = None

    # 初始化向量检索
    try:
        from langchain_community.vectorstores import Neo4jVector
        from langchain_ollama import OllamaEmbeddings

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
        _vector_retriever = vector_index.as_retriever()
        print(f"✅ 向量检索初始化成功！")
    except Exception as e:
        print(f"⚠️ 向量检索初始化失败: {e}")
        _vector_retriever = None

    # 初始化实体提取链
    try:
        class Entities(BaseModel):
            names: list[str] = Field(
                ...,
                description="从文本中提取的所有人物、组织或工业部件实体名称列表"
            )

        entity_prompt = ChatPromptTemplate.from_messages([
            ("system", "你需要从文本中提取组织和人物、工业部件实体，严格按照指定格式返回结果。"),
            ("human", "使用给定的格式从以下输入中提取信息：{question}"),
        ])
        _entity_chain = entity_prompt | _llm.with_structured_output(Entities)
        print(f"✅ 实体提取链初始化成功！")
    except Exception as e:
        print(f"⚠️ 实体提取链初始化失败: {e}")
        _entity_chain = None

    _is_initialized = True
    return True


def _ensure_fulltext_index():
    """确保全文索引存在"""
    if _graph_db is None:
        return

    try:
        check_query = """
        SHOW INDEXES
        YIELD name, type, state
        WHERE name = 'entity' AND type = 'FULLTEXT'
        RETURN count(*) as exists
        """
        result = _graph_db.query(check_query)
        if result and result[0]['exists'] > 0:
            print(f"✅ 全文索引 'entity' 已存在")
            return

        # 尝试创建索引
        print(f"📝 创建全文索引 'entity'...")
        check_nodes = """
        MATCH (n)
        WHERE n:__Entity__ OR n:Entity
        WITH n LIMIT 1
        RETURN labels(n) as labels, keys(n) as keys
        """
        node_info = _graph_db.query(check_nodes)
        if node_info:
            labels = node_info[0].get('labels', [])
            keys = node_info[0].get('keys', [])
            index_property = 'id' if 'id' in keys else ('name' if 'name' in keys else keys[0] if keys else 'id')
            entity_label = labels[0] if labels else '__Entity__'

            create_query = f"""
            CREATE FULLTEXT INDEX entity IF NOT EXISTS
            FOR (n:`{entity_label}`)
            ON EACH [n.{index_property}]
            """
            _graph_db.query(create_query)
            print(f"✅ 全文索引创建成功！")
    except Exception as e:
        print(f"⚠️ 索引检查/创建失败: {e}")


# ===================== 辅助函数 =====================
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


def format_confidence(confidence: Any) -> str:
    """
    格式化置信度为百分比字符串
    
    Args:
        confidence: 置信度值，可能是 0-1 的浮点数或 0-100 的整数
    
    Returns:
        str: 格式化的百分比字符串，如 "90%"
    """
    try:
        conf_value = float(confidence)
        # 如果值小于等于 1，认为是 0-1 格式，需要乘以 100
        if conf_value <= 1.0:
            conf_value = conf_value * 100
        return f"{conf_value:.1f}%"
    except (ValueError, TypeError):
        return "0%"


def generate_full_text_query(input_text: str) -> str:
    """生成 Neo4j 全文检索查询"""
    try:
        from langchain_neo4j.vectorstores.neo4j_vector import remove_lucene_chars
        words = [el for el in remove_lucene_chars(input_text).split() if el]
        if not words:
            return ""
        return " AND ".join([f"{word}~2" for word in words])
    except Exception:
        return input_text


def graph_retriever(question: str) -> str:
    """基于问题检索 Neo4j 图谱中的关系"""
    if _graph_db is None:
        return "【模拟数据】未连接知识图谱，返回模拟检索结果。"

    result = ""
    found_entities = []  # 记录找到结果的实体
    try:
        if _entity_chain:
            entities = _entity_chain.invoke({"question": question})
            for entity in entities.names:
                entity_result = ""
                query_text = generate_full_text_query(entity)
                if not query_text:  # 如果查询文本为空，跳过
                    continue
                
                # 首先尝试使用全文索引查询
                try:
                    # 使用与 inspection_analysis_demo.py 相同的查询方式
                    cypher_query = """
                    CALL db.index.fulltext.queryNodes('entity', $query, {limit:2})
                    YIELD node,score
                    CALL (node) { 
                      WITH node
                      MATCH (node)-[r:!MENTIONS]->(neighbor)
                      RETURN node.id + ' - ' + type(r) + ' -> ' + neighbor.id AS output
                      UNION ALL
                      WITH node
                      MATCH (node)<-[r:!MENTIONS]-(neighbor)
                      RETURN neighbor.id + ' - ' + type(r) + ' -> ' +  node.id AS output
                    }
                    RETURN output LIMIT 50
                    """
                    response = _graph_db.query(cypher_query, {"query": query_text})
                    entity_result = "\n".join([el['output'] for el in response])
                    
                    if entity_result:
                        found_entities.append(entity)
                        result += entity_result + "\n"
                except Exception as idx_error:
                    # 检查是否是索引不存在的问题
                    if "no such fulltext schema index" in str(idx_error).lower():
                        # 索引不存在，使用降级查询（只打印一次警告）
                        if not hasattr(graph_retriever, '_index_warning_printed'):
                            print(f"⚠️ 全文索引不存在，使用降级查询方案")
                            graph_retriever._index_warning_printed = True
                
                # 如果全文索引查询无结果（无论是否异常），尝试降级查询
                if not entity_result:
                    try:
                        # 降级查询：直接通过节点属性匹配，查找所有关系
                        # 使用 OPTIONAL MATCH 确保即使没有关系也能找到节点
                        fallback_query = """
                        MATCH (node)
                        WHERE node.id CONTAINS $entity OR toLower(node.id) CONTAINS toLower($entity)
                        WITH node LIMIT 5
                        OPTIONAL MATCH (node)-[r:!MENTIONS]->(neighbor)
                        WITH node, r, neighbor
                        WHERE r IS NOT NULL
                        RETURN node.id + ' - ' + type(r) + ' -> ' + neighbor.id AS output
                        UNION ALL
                        MATCH (node)
                        WHERE node.id CONTAINS $entity OR toLower(node.id) CONTAINS toLower($entity)
                        WITH node LIMIT 5
                        OPTIONAL MATCH (node)<-[r:!MENTIONS]-(neighbor)
                        WITH node, r, neighbor
                        WHERE r IS NOT NULL
                        RETURN neighbor.id + ' - ' + type(r) + ' -> ' + node.id AS output
                        LIMIT 50
                        """
                        response = _graph_db.query(fallback_query, {"entity": entity})
                        entity_result = "\n".join([el['output'] for el in response])
                        
                        if entity_result:
                            found_entities.append(entity)
                            result += entity_result + "\n"
                    except Exception as fallback_error:
                        # 降级查询也失败，静默处理（这是正常情况，实体可能不存在）
                        pass
        else:
            # 没有实体提取链，使用简单查询
            simple_query = """
            MATCH (n)-[r]->(m)
            WHERE n.id CONTAINS $keyword OR m.id CONTAINS $keyword
            RETURN n.id + ' - ' + type(r) + ' -> ' + m.id AS output
            LIMIT 20
            """
            response = _graph_db.query(simple_query, {"keyword": question[:20]})
            result = "\n".join([el['output'] for el in response])
    except Exception as e:
        # 只在严重错误时打印
        import logging
        logging.error(f"图谱检索异常: {e}")

    # 如果没有找到任何结果，返回提示信息（但不打印警告）
    if not result.strip():
        return "未找到相关图谱数据"
    
    return result.strip()


def full_retriever(question: str) -> str:
    """混合检索（图谱 + 向量）"""
    # 图谱检索
    graph_data = graph_retriever(question)

    # 向量检索
    vector_data = []
    if _vector_retriever is not None:
        try:
            vector_data = [el.page_content for el in _vector_retriever.invoke(question)]
        except Exception as e:
            print(f"⚠️ 向量检索失败: {e}")

    return f"""图谱数据:
{graph_data}

向量数据:
{"#Document ".join(vector_data) if vector_data else "无向量检索结果"}
"""


def _common_llm(prompt: str, node_name: str):
    """生成绑定 prompt 的 LLM 调用函数"""
    def llm_node(state: State):
        system_prompt = SystemMessage(content=prompt)
        try:
            response = _llm.invoke([system_prompt])
            return {"messages": [response]}
        except Exception as e:
            print(f"⚠️ [{node_name}] LLM 调用失败: {e}")
            raise
    return llm_node


# ===================== LangGraph 节点定义 =====================
def retrieval_node(state: State) -> State:
    """数据检索节点"""
    defect_input = state["defect_input"]
    supplementary_queries = state.get("supplementary_queries", [])
    retry_count = state.get("retry_count", 0)

    # 确定检索查询
    if supplementary_queries and retry_count > 0:
        query = " ".join(supplementary_queries)
        node_prefix = f"数据检索节点（补充检索{retry_count}次）"
    else:
        part_name = defect_input.get("part_name", "轴承")
        defect_type = defect_input.get("defect_type", "温度异常")
        query = f"{part_name}的{defect_type}相关巡检记录、故障原因、维修方案和部件规格是什么？"
        node_prefix = "数据检索节点（初始检索）"
        query_entities = [part_name, defect_type, defect_input.get("part_position", "")]
        state["query_entities"] = [ent for ent in query_entities if ent]

    # 记录思考过程 - 开始检索
    state["thinking_processes"].append({
        "node": node_prefix,
        "title": "开始执行 GraphRAG 混合检索",
        "content": f"检索目标：{query}\n检索范围：知识图谱 + 向量数据库"
    })

    # 执行混合检索
    raw_data = full_retriever(query)

    # 记录思考过程 - 检索完成
    state["thinking_processes"].append({
        "node": node_prefix,
        "title": "混合检索完成",
        "content": f"检索结果长度：{len(raw_data)} 字符\n开始 LLM 整理检索结果..."
    })

    # 调用 LLM 整理检索结果
    retrieval_prompt = f"""
    你是轨道运输巡检数据专家，擅长整理电客车故障文本信息。请仔细阅读输入信息，以简洁的语言进行重述，总结出其中的关键信息。
    输入信息为：
    检索问题：{query}
    混合检索结果：{raw_data}（文本中"#Document"为分隔符，需合并所有文本片段提取信息）
    """
    retrieval_agent = _common_llm(retrieval_prompt, "数据检索节点")
    response = retrieval_agent(state)
    response_content = response["messages"][0].content

    # 合并或覆盖结果
    if retry_count > 0 and state.get("retrieval_result"):
        state["retrieval_result"] = f"{state['retrieval_result']}\n\n【补充检索{retry_count}次结果】：{response_content}"
    else:
        state["retrieval_result"] = response_content

    state["retry_count"] = retry_count + 1

    # 记录思考过程 - 整理完成
    state["thinking_processes"].append({
        "node": node_prefix,
        "title": "检索结果整理完成",
        "content": f"整理后结果长度：{len(state['retrieval_result'])} 字符"
    })

    return state


def extraction_node(state: State) -> State:
    """信息提取节点"""
    retrieval_result = state["retrieval_result"]
    defect_input = state["defect_input"]

    # 记录思考过程 - 开始提取
    state["thinking_processes"].append({
        "node": "信息提取节点",
        "title": "开始凝练核心信息",
        "content": f"输入：检索结果 ({len(retrieval_result)} 字符)\n目标：提取核心故障现象、关键部件信息、时间序列、环境参数、维护要点"
    })

    extraction_prompt = f"""
        你是轨道运输巡检数据专家，擅长整理电客车故障文本信息。
        当前巡检结果为：{defect_input}
        往年巡检记录中，与该结果相关的故障文本内容为：{retrieval_result}
        请凝练以下检索结果为结构化JSON，仅返回JSON：
        输出结构：
        {{
            "core_fault_phenomenon": [],
            "key_part_info": [],
            "time_series": [],
            "critical_env_params": [],
            "maintenance_key_points": []
        }}
    """

    extraction_agent = _common_llm(extraction_prompt, "信息提取节点")
    response = extraction_agent(state)

    try:
        json_data = clean_json_output(response["messages"][0].content)
        extraction_result = json.loads(json_data)
        
        # 记录思考过程 - 提取成功
        summary_parts = []
        if extraction_result.get('core_fault_phenomenon'):
            summary_parts.append(f"核心故障现象: {len(extraction_result['core_fault_phenomenon'])} 项")
        if extraction_result.get('key_part_info'):
            summary_parts.append(f"关键部件信息: {len(extraction_result['key_part_info'])} 项")
        if extraction_result.get('maintenance_key_points'):
            summary_parts.append(f"维护要点: {len(extraction_result['maintenance_key_points'])} 项")
        
        state["thinking_processes"].append({
            "node": "信息提取节点",
            "title": "信息提取完成",
            "content": "\n".join(summary_parts) if summary_parts else "已提取结构化信息"
        })
    except Exception:
        extraction_result = {
            "core_fault_phenomenon": ["无"],
            "key_part_info": ["无"],
            "time_series": ["无"],
            "critical_env_params": ["无"],
            "maintenance_key_points": ["无"]
        }
        state["thinking_processes"].append({
            "node": "信息提取节点",
            "title": "信息提取失败",
            "content": "使用默认结构，建议检查检索结果质量"
        })

    state["extraction_result"] = extraction_result
    state["messages"].extend(response["messages"])

    return state


def fault_analysis_node(state: State) -> State:
    """故障分析节点"""
    defect_input = state["defect_input"]
    extraction_result = state["extraction_result"]

    # 记录思考过程 - 开始分析
    state["thinking_processes"].append({
        "node": "故障分析节点",
        "title": f"分析 {defect_input.get('part_name')}{defect_input.get('defect_type')}",
        "content": f"基于提取的核心信息，分析潜在故障原因和风险等级"
    })

    fault_prompt = f"""
        请分析{defect_input.get('part_name')}{defect_input.get('defect_type')}的故障原因和风险，返回JSON：
        提取结果：{json.dumps(extraction_result, ensure_ascii=False)}
        输出结构：
        {{
            "potential_causes": [{{"原因": "", "置信度": 0, "关联依据": ""}}],
            "risk_assessment": [{{"risk_level": "", "expected_fault_time": "", "impact_scope": ""}}]
        }}
        注意：置信度应为 0-100 之间的整数，表示百分比（如 90 表示 90%）
    """

    fault_agent = _common_llm(fault_prompt, "故障分析节点")
    response = fault_agent(state)

    try:
        json_data = clean_json_output(response["messages"][0].content)
        fault_analysis_result = json.loads(json_data)
        causes_count = len(fault_analysis_result.get('potential_causes', []))
        
        # 记录思考过程 - 分析完成
        causes_summary = []
        for i, cause in enumerate(fault_analysis_result.get('potential_causes', [])[:3], 1):
            confidence_str = format_confidence(cause.get('置信度', 0))
            causes_summary.append(f"{i}. {cause.get('原因', '未知')} (置信度: {confidence_str})")
        
        risk = fault_analysis_result.get('risk_assessment', [{}])[0]
        risk_info = f"风险等级: {risk.get('risk_level', '未知')}"
        
        state["thinking_processes"].append({
            "node": "故障分析节点",
            "title": f"分析完成，发现 {causes_count} 个潜在原因",
            "content": "\n".join(causes_summary) + f"\n{risk_info}"
        })
    except Exception:
        fault_analysis_result = {
            "potential_causes": [{"原因": defect_input.get('defect_type'), "置信度": 50, "关联依据": "基于通用部件特性分析"}],
            "risk_assessment": [{"risk_level": "中", "expected_fault_time": "未来7天内", "impact_scope": "局部设备异常"}]
        }
        state["thinking_processes"].append({
            "node": "故障分析节点",
            "title": "分析失败，使用默认评估",
            "content": f"默认原因: {defect_input.get('defect_type')}\n风险等级: 中"
        })

    state["fault_analysis_result"] = fault_analysis_result
    state["messages"].extend(response["messages"])

    return state


def reflection_node(state: State) -> State:
    """信息充足性反思节点"""
    defect_input = state["defect_input"]
    extraction_result = state["extraction_result"]
    fault_analysis_result = state["fault_analysis_result"]
    retry_count = state["retry_count"]
    max_retry = state["max_retry"]

    # 记录思考过程 - 开始反思
    state["thinking_processes"].append({
        "node": "信息充足性反思",
        "title": "评估信息充足性",
        "content": f"当前检索次数: {retry_count}/{max_retry}\n评估维度: 故障现象完整性、参数覆盖度、原因充分性、历史案例"
    })

    reflection_prompt = f"""
    你是轨道运输巡检领域的资深专家，请严格评估当前信息是否足够生成详细、可执行的{defect_input.get('part_name')}{defect_input.get('defect_type')}维护方案。
    评估标准（需全部满足才判定为充足）：
    1. 核心故障现象明确且具体（非泛泛而谈）；
    2. 关键运行参数（温度、转速、压力等）覆盖故障相关维度；
    3. 潜在故障原因至少2个，且每个原因有明确关联依据；
    4. 包含至少1条历史维护案例或同类故障处理经验；
    5. 包含部件规格、备件信息等可执行维护的基础数据。

    当前已有信息：
    - 核心提取结果：{json.dumps(extraction_result, ensure_ascii=False)}
    - 故障分析结果：{json.dumps(fault_analysis_result, ensure_ascii=False)}
    - 检索结果摘要：{state.get('retrieval_result', '无')[:500]}...

    请严格按照以下JSON格式返回评估结果：
    {{
        "is_info_sufficient": true/false,
        "insufficient_reasons": ["原因1", "原因2"],
        "supplementary_queries": ["补充查询1", "补充查询2"]
    }}

    注意：
    1. 补充查询需精准、可执行，能直接补充缺失信息（例如："辅助逆变器显黄的历史维护案例及备件型号"）；
    2. 补充查询数量控制在1-2个；
    3. 若已达最大重试次数，即使信息不足也返回true。
    """

    reflection_agent = _common_llm(reflection_prompt, "信息充足性反思")
    response = reflection_agent(state)

    try:
        json_data = clean_json_output(response["messages"][0].content)
        reflection_result = json.loads(json_data)
        state["is_info_sufficient"] = reflection_result.get("is_info_sufficient", False)
        state["supplementary_queries"] = reflection_result.get("supplementary_queries", [])

        if state["is_info_sufficient"]:
            state["thinking_processes"].append({
                "node": "信息充足性反思",
                "title": "信息充足",
                "content": "可以生成维护方案"
            })
        else:
            reasons = reflection_result.get('insufficient_reasons', ['未说明'])
            state["thinking_processes"].append({
                "node": "信息充足性反思",
                "title": "信息不足，需要补充检索",
                "content": f"不足原因: {', '.join(reasons)}\n补充查询: {', '.join(state['supplementary_queries'])}"
            })
    except Exception:
        if retry_count < max_retry:
            state["is_info_sufficient"] = False
            state["supplementary_queries"] = [f"{defect_input.get('part_name')}{defect_input.get('defect_type')} 详细维护案例"]
            state["thinking_processes"].append({
                "node": "信息充足性反思",
                "title": "评估失败，触发补充检索",
                "content": f"补充查询: {state['supplementary_queries'][0]}"
            })
        else:
            state["is_info_sufficient"] = True
            state["thinking_processes"].append({
                "node": "信息充足性反思",
                "title": "已达最大重试次数",
                "content": "使用现有信息生成维护方案"
            })

    state["messages"].extend(response["messages"])

    return state


def maintenance_node(state: State) -> State:
    """维护方案生成节点"""
    defect_input = state["defect_input"]
    extraction_result = state["extraction_result"]
    fault_analysis_result = state["fault_analysis_result"]

    # 记录思考过程 - 开始生成
    causes_count = len(fault_analysis_result.get('potential_causes', []))
    state["thinking_processes"].append({
        "node": "维护方案生成节点",
        "title": f"为 {defect_input.get('part_name')} 生成维护方案",
        "content": f"基于 {causes_count} 个潜在原因，生成针对性维护方案"
    })

    maintenance_prompt = f"""
        请为{defect_input.get('part_name')}{defect_input.get('defect_type')}生成维护方案，返回JSON：
        提取结果：{json.dumps(extraction_result, ensure_ascii=False)}
        故障分析：{json.dumps(fault_analysis_result, ensure_ascii=False)}
        输出结构：
        {{
            "suggested_maintenance_time": "",
            "spare_parts_list": [{{"备件名称": "", "型号": "", "quantity": 0, "specs": ""}}],
            "maintenance_steps": [],
            "fault_summary": "",
            "risk_reminder": ""
        }}
    """

    maintenance_agent = _common_llm(maintenance_prompt, "维护方案生成节点")
    response = maintenance_agent(state)

    try:
        json_data = clean_json_output(response["messages"][0].content)
        maintenance_plan_result = json.loads(json_data)
        steps_count = len(maintenance_plan_result.get('maintenance_steps', []))
        parts_count = len(maintenance_plan_result.get('spare_parts_list', []))
        
        # 记录思考过程 - 生成完成
        state["thinking_processes"].append({
            "node": "维护方案生成节点",
            "title": f"方案生成完成",
            "content": f"维护时间: {maintenance_plan_result.get('suggested_maintenance_time', '立即')}\n备件数量: {parts_count}\n执行步骤: {steps_count} 步"
        })
    except Exception:
        part_name = defect_input.get("part_name", "未知部件")
        maintenance_plan_result = {
            "suggested_maintenance_time": "立即检查",
            "spare_parts_list": [{"备件名称": part_name, "型号": "通用型号", "quantity": 1, "specs": "通用规格"}],
            "maintenance_steps": [f"1. 停机检查{part_name}状态", f"2. 更换损坏部件", f"3. 测试设备运行"],
            "fault_summary": f"{part_name}{defect_input.get('defect_type', '异常')}",
            "risk_reminder": "建议优先现场人工检测"
        }
        state["thinking_processes"].append({
            "node": "维护方案生成节点",
            "title": "方案生成失败，使用默认方案",
            "content": "建议: 立即检查、更换部件、测试运行"
        })

    state["maintenance_plan_result"] = maintenance_plan_result
    state["messages"].extend(response["messages"])

    return state


# ===================== 报告生成 =====================
def generate_final_report(state: State) -> str:
    """生成最终分析报告"""
    defect_input = state["defect_input"]
    extraction_result = state.get("extraction_result", {})
    fault_analysis_result = state.get("fault_analysis_result", {})
    maintenance_plan_result = state.get("maintenance_plan_result", {})
    retry_count = state.get("retry_count", 1) - 1

    report = f"""# 轨道巡检故障分析报告

## 一、故障基本信息

| 项目 | 内容 |
|------|------|
| 检测时间 | {defect_input.get('detect_time', '未知')} |
| 部件名称 | {defect_input.get('part_name', '未知')} |
| 部件位置 | {defect_input.get('part_position', '未知')} |
| 缺陷类型 | {defect_input.get('defect_type', '未知')} |
| 检测置信度 | {defect_input.get('detect_confidence', 0.0):.0%} |
| 检索次数 | 初始检索 + 补充检索{retry_count}次 |

## 二、核心信息提取

### 2.1 核心故障现象
"""
    core_phenomena = extraction_result.get('core_fault_phenomenon', ['无'])
    for i, phen in enumerate(core_phenomena, 1):
        if phen and phen != '无':
            report += f"{i}. {phen}\n"

    report += """
### 2.2 历史维护要点
"""
    maintenance_points = extraction_result.get('maintenance_key_points', ['无'])
    for i, point in enumerate(maintenance_points, 1):
        if point and point != '无':
            report += f"{i}. {point}\n"

    report += """
## 三、故障分析与风险评估

### 3.1 潜在故障原因
"""
    potential_causes = fault_analysis_result.get('potential_causes', [])
    for i, cause in enumerate(potential_causes, 1):
        confidence_str = format_confidence(cause.get('置信度', 0))
        report += f"""
#### 原因{i}
- 具体原因：{cause.get('原因', '未知')}
- 置信度：{confidence_str}
- 关联依据：{cause.get('关联依据', '无')}
"""

    report += """
### 3.2 风险评估
"""
    risk_assessments = fault_analysis_result.get('risk_assessment', [])
    for risk in risk_assessments:
        report += f"""
| 风险等级 | 预计故障时间 | 影响范围 |
|----------|--------------|----------|
| {risk.get('risk_level', '未知')} | {risk.get('expected_fault_time', '未知')} | {risk.get('impact_scope', '未知')} |
"""

    report += f"""
## 四、维护方案建议

### 4.1 建议维护时间
{maintenance_plan_result.get('suggested_maintenance_time', '立即维护')}

### 4.2 所需备件清单
"""
    spare_parts = maintenance_plan_result.get('spare_parts_list', [])
    if spare_parts:
        report += "| 备件名称 | 型号 | 数量 | 规格 |\n"
        report += "|----------|------|------|------|\n"
        for part in spare_parts:
            report += f"| {part.get('备件名称', '未知')} | {part.get('型号', '未知')} | {part.get('quantity', 0)} | {part.get('specs', '未知')} |\n"

    report += """
### 4.3 维护执行步骤
"""
    maintenance_steps = maintenance_plan_result.get('maintenance_steps', [])
    for step in maintenance_steps:
        report += f"{step}\n"

    report += f"""
### 4.4 故障总结与风险提示

#### 故障总结
{maintenance_plan_result.get('fault_summary', '无')}

#### 风险提示
{maintenance_plan_result.get('risk_reminder', '无')}

---
*报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*数据来源：Neo4j知识图谱 + 向量数据库混合检索（共检索{retry_count + 1}次）*
"""
    return report


# ===================== LangGraph 图构建 =====================
def _create_fault_analysis_graph():
    """创建故障分析 LangGraph 图"""
    graph = StateGraph(State)

    # 添加节点
    graph.add_node("数据检索节点", retrieval_node)
    graph.add_node("信息提取节点", extraction_node)
    graph.add_node("故障分析节点", fault_analysis_node)
    graph.add_node("信息充足性反思", reflection_node)
    graph.add_node("维护方案生成节点", maintenance_node)

    # 条件判断
    def should_retrieve_more(state: State) -> str:
        if not state["is_info_sufficient"] and state["retry_count"] < state["max_retry"]:
            return "数据检索节点"
        else:
            return "维护方案生成节点"

    # 构建执行流程
    graph.add_edge(START, "数据检索节点")
    graph.add_edge("数据检索节点", "信息提取节点")
    graph.add_edge("信息提取节点", "故障分析节点")
    graph.add_edge("故障分析节点", "信息充足性反思")
    graph.add_conditional_edges(
        "信息充足性反思",
        should_retrieve_more,
        {
            "数据检索节点": "数据检索节点",
            "维护方案生成节点": "维护方案生成节点"
        }
    )
    graph.add_edge("维护方案生成节点", END)

    return graph.compile()


# 延迟初始化的图实例
_fault_analysis_graph = None


def _get_graph():
    """获取图实例（延迟初始化）"""
    global _fault_analysis_graph
    if _fault_analysis_graph is None:
        _fault_analysis_graph = _create_fault_analysis_graph()
    return _fault_analysis_graph


# ===================== 主入口函数 =====================
def run_fault_analysis(
    detect_time: str = "",
    part_name: str = "",
    part_position: str = "",
    defect_type: str = "",
    detect_confidence: float = 0.95,
    max_retry: int = 3
) -> AnalysisResult:
    """
    执行故障分析的主入口函数（同步版本）
    
    Args:
        detect_time: 检测时间
        part_name: 部件名称
        part_position: 部件位置
        defect_type: 缺陷类型
        detect_confidence: 检测置信度
        max_retry: 最大补充检索次数
    
    Returns:
        AnalysisResult: 分析结果
    """
    start_time = datetime.now()
    
    # 确保已初始化
    if not _is_initialized:
        initialize()

    # 构造输入
    defect_input = {
        "detect_time": detect_time or datetime.now().strftime("%Y-%m-%d %H:%M"),
        "part_name": part_name or "未知部件",
        "part_position": part_position or "未知位置",
        "defect_type": defect_type or "未知缺陷",
        "detect_confidence": detect_confidence
    }

    # 初始化状态
    initial_state: State = {
        "messages": [HumanMessage(content="请分析轨道巡检的故障并生成维护方案")],
        "defect_input": defect_input,
        "retrieval_result": "",
        "extraction_result": {},
        "fault_analysis_result": {},
        "maintenance_plan_result": {},
        "thinking_processes": [],
        "query_entities": [],
        "is_info_sufficient": False,
        "supplementary_queries": [],
        "retry_count": 0,
        "max_retry": max_retry
    }

    # 执行图
    graph = _get_graph()
    result = graph.invoke(initial_state)

    # 生成最终报告
    final_report = generate_final_report(result)

    return AnalysisResult(
        defect_input=result["defect_input"],
        retrieval_result=result["retrieval_result"],
        extraction_result=result["extraction_result"],
        fault_analysis_result=result["fault_analysis_result"],
        maintenance_plan_result=result["maintenance_plan_result"],
        thinking_processes=result["thinking_processes"],
        final_report=final_report,
        retry_count=result["retry_count"]
    )


async def run_fault_analysis_async(
    detect_time: str = "",
    part_name: str = "",
    part_position: str = "",
    defect_type: str = "",
    detect_confidence: float = 0.95,
    max_retry: int = 3,
    ws_callback: Optional[Callable[[str, str, dict], Awaitable[None]]] = None
) -> AnalysisResult:
    """
    异步执行故障分析（通过 WebSocket 实时推送进度和结果）
    
    Args:
        detect_time: 检测时间
        part_name: 部件名称
        part_position: 部件位置
        defect_type: 缺陷类型
        detect_confidence: 检测置信度
        max_retry: 最大补充检索次数
        ws_callback: WebSocket 回调函数 (msg_type, action, data)
    
    Returns:
        AnalysisResult: 分析结果
    """
    global _thinking_step_counter
    _thinking_step_counter = 0
    
    start_time = datetime.now()
    
    # 设置 WebSocket 回调
    set_ws_callback(ws_callback)

    try:
        # 确保已初始化
        if not _is_initialized:
            initialize()

        # 构造输入
        defect_input = {
            "detect_time": detect_time or datetime.now().strftime("%Y-%m-%d %H:%M"),
            "part_name": part_name or "未知部件",
            "part_position": part_position or "未知位置",
            "defect_type": defect_type or "未知缺陷",
            "detect_confidence": detect_confidence
        }

        # 发送分析开始消息
        await _send_ws_message(WSMessageTypes.ANALYSIS_START, {
            "message": "开始故障分析",
            "defect_input": defect_input,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_nodes": 5
        })

        # 初始化状态
        initial_state: State = {
            "messages": [HumanMessage(content="请分析轨道巡检的故障并生成维护方案")],
            "defect_input": defect_input,
            "retrieval_result": "",
            "extraction_result": {},
            "fault_analysis_result": {},
            "maintenance_plan_result": {},
            "thinking_processes": [],
            "query_entities": [],
            "is_info_sufficient": False,
            "supplementary_queries": [],
            "retry_count": 0,
            "max_retry": max_retry
        }

        # 节点名称映射
        node_name_map = {
            "数据检索节点": 1,
            "信息提取节点": 2,
            "故障分析节点": 3,
            "信息充足性反思": 4,
            "维护方案生成节点": 5
        }

        # 执行图（异步流式）
        graph = _get_graph()
        result = None
        last_thinking_count = 0

        async for chunk in graph.astream(initial_state):
            for node_name, node_output in chunk.items():
                node_index = node_name_map.get(node_name, 0)
                
                # 发送节点开始消息
                await _send_node_progress(
                    node_name=node_name,
                    node_index=node_index,
                    status="running",
                    message=f"正在执行 {node_name}..."
                )

                # 发送新增的思考过程步骤
                if isinstance(node_output, dict) and "thinking_processes" in node_output:
                    thinking_processes = node_output["thinking_processes"]
                    for i in range(last_thinking_count, len(thinking_processes)):
                        step = thinking_processes[i]
                        if isinstance(step, dict):
                            await _send_thinking_step(
                                node_name=step.get("node", node_name),
                                title=step.get("title", "执行中"),
                                content=step.get("content", "")
                            )
                    last_thinking_count = len(thinking_processes)

                # 发送节点完成消息
                await _send_node_progress(
                    node_name=node_name,
                    node_index=node_index,
                    status="completed",
                    message=f"{node_name} 执行完成"
                )

                result = node_output if isinstance(node_output, dict) else result

        # 从最终状态获取结果
        if result is None:
            result = initial_state

        # 生成最终报告
        final_report = generate_final_report(result)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # 构建最终报告数据
        final_report_data = FinalReportData(
            defect_input=result.get("defect_input", defect_input),
            extraction_result=result.get("extraction_result", {}),
            fault_analysis_result=result.get("fault_analysis_result", {}),
            maintenance_plan_result=result.get("maintenance_plan_result", {}),
            report_markdown=final_report,
            retry_count=result.get("retry_count", 0),
            total_duration=duration
        )

        # 发送最终报告
        await _send_ws_message(WSMessageTypes.FINAL_REPORT, final_report_data.to_dict())

        # 发送分析完成消息
        await _send_ws_message(WSMessageTypes.ANALYSIS_COMPLETE, {
            "message": "故障分析完成",
            "duration": duration,
            "retry_count": result.get("retry_count", 0),
            "thinking_steps": _thinking_step_counter
        })

        return AnalysisResult(
            defect_input=result.get("defect_input", defect_input),
            retrieval_result=result.get("retrieval_result", ""),
            extraction_result=result.get("extraction_result", {}),
            fault_analysis_result=result.get("fault_analysis_result", {}),
            maintenance_plan_result=result.get("maintenance_plan_result", {}),
            thinking_processes=result.get("thinking_processes", []),
            final_report=final_report,
            retry_count=result.get("retry_count", 0)
        )

    except Exception as e:
        # 发送错误消息
        await _send_ws_message(WSMessageTypes.ERROR, {
            "error": str(e),
            "message": f"故障分析执行失败: {e}"
        })
        raise

    finally:
        # 清除 WebSocket 回调
        set_ws_callback(None)


# ===================== 测试入口 =====================
if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="故障分析核心模块测试")
    parser.add_argument("--part-name", type=str, default="辅助逆变器", help="部件名称")
    parser.add_argument("--defect-type", type=str, default="显黄", help="缺陷类型")
    parser.add_argument("--part-position", type=str, default="0116车", help="部件位置")
    parser.add_argument("--async-mode", action="store_true", help="使用异步模式")
    args = parser.parse_args()
    
    print("=" * 60)
    print("故障分析核心模块测试")
    print("=" * 60)

    # 初始化
    print("\n1. 初始化模块...")
    success = initialize()
    print(f"   初始化结果: {'成功' if success else '失败'}")

    if not success:
        print("初始化失败，退出测试")
        exit(1)

    # 执行分析
    print("\n2. 执行故障分析...")
    print(f"   部件名称: {args.part_name}")
    print(f"   缺陷类型: {args.defect_type}")
    print(f"   部件位置: {args.part_position}")
    
    if args.async_mode:
        # 异步模式测试
        async def test_async():
            async def print_callback(msg_type: str, action: str, data: dict):
                print(f"[{msg_type}] {action}: {json.dumps(data, ensure_ascii=False, indent=2)[:200]}...")
            
            result = await run_fault_analysis_async(
                detect_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
                part_name=args.part_name,
                part_position=args.part_position,
                defect_type=args.defect_type,
                detect_confidence=0.95,
                ws_callback=print_callback
            )
            return result
        
        result = asyncio.run(test_async())
    else:
        # 同步模式
        result = run_fault_analysis(
            detect_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
            part_name=args.part_name,
            part_position=args.part_position,
            defect_type=args.defect_type,
            detect_confidence=0.95
        )

    # 输出结果
    print("\n3. 分析结果摘要:")
    print(f"   检索次数: {result.retry_count}")
    print(f"   思考过程: {len(result.thinking_processes)} 步")
    print(f"   报告长度: {len(result.final_report)} 字符")
    
    # 输出思考过程
    print("\n4. 思考过程详情:")
    for i, process in enumerate(result.thinking_processes, 1):
        if isinstance(process, dict):
            print(f"   步骤 {i}: [{process.get('node', '')}] {process.get('title', '')}")
        else:
            print(f"   步骤 {i}: {str(process)[:80]}...")

    print("\n5. 最终报告预览:")
    print("-" * 60)
    print(result.final_report[:1500])
    if len(result.final_report) > 1500:
        print("... (报告已截断)")
    print("-" * 60)

    print("\n✅ 测试完成！")

