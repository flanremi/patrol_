#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangGraph后端API服务器
提供前端所需的API接口
"""
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, AsyncGenerator
import json
from datetime import datetime
import os
import asyncio
import re

# 导入我们的LangGraph组件
from langgraph_helper import common_llm
from typing_extensions import TypedDict
from typing import Annotated
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END

from requirement_diagnosis_graph import requirement_diagnosis_subgraph
from planning_strategy_graph import planning_strategy_subgraph
from data_analysis_graph import data_analysis_subgraph
from report_generation_graph import report_generation_subgraph

load_dotenv()
app = FastAPI(title="LangGraph API", version="1.0.0")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 数据模型
class ChatMessage(BaseModel):
    message: str


class ChatResponse(BaseModel):
    messages: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None


class State(TypedDict):
    """对话状态"""
    messages: Annotated[list, add_messages]


# 全局变量
graph = None
graph_initialized = False

# 聊天记录目录
CHAT_RECORD_DIR = "chat_record"


def ensure_chat_record_dir():
    """确保聊天记录目录存在"""
    if not os.path.exists(CHAT_RECORD_DIR):
        os.makedirs(CHAT_RECORD_DIR)


def sanitize_filename(text: str) -> str:
    """清理文件名，移除特殊字符"""
    # 移除或替换文件名中不允许的字符
    text = re.sub(r'[<>:"/\\|?*]', '_', text)
    # 移除多余的空格和换行符
    text = re.sub(r'\s+', '_', text.strip())
    # 限制长度
    return text[:100] if len(text) > 100 else text


def save_chat_record(question: str, messages: List[Dict[str, Any]], metadata: Dict[str, Any] = None):
    """保存聊天记录到JSON文件"""
    try:
        ensure_chat_record_dir()

        # 生成文件名
        filename = sanitize_filename(question)
        if not filename:
            filename = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 确保文件名唯一
        filepath = os.path.join(CHAT_RECORD_DIR, f"{filename}.json")
        counter = 1
        while os.path.exists(filepath):
            filepath = os.path.join(CHAT_RECORD_DIR, f"{filename}_{counter}.json")
            counter += 1

        # 构建聊天记录数据
        chat_data = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "messages": messages,
            "metadata": metadata or {},
            "total_messages": len(messages)
        }

        # 保存到文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(chat_data, f, ensure_ascii=False, indent=2)

        print(f"✅ 聊天记录已保存: {filepath}")
        return filepath

    except Exception as e:
        print(f"❌ 保存聊天记录失败: {e}")
        return None

#  todo 注意，总结节点名字里一定要有总结，工具节点的名字一定要带工具
def initialize_graph():
    """初始化LangGraph - 创建4个子Agent的串联结构"""
    global graph, graph_initialized

    if graph_initialized:
        return

    try:
        from langchain_openai import ChatOpenAI
        from langgraph.prebuilt import create_react_agent

        # 创建主图，串联4个子Agent
        main_graph = StateGraph(State)

        # 添加4个子Agent节点
        main_graph.add_node("需求诊断智能体", requirement_diagnosis_subgraph,
                            metadata={
                                "description": "作为系统入口，负责理解用户原始需求，进行任务分解和上下文丰富，为后续Agent提供结构化任务描述。"})
        
        main_graph.add_node("规划与策略智能体", planning_strategy_subgraph,
                            metadata={
                                "description": "根据需求诊断结果，制定具体执行策略，选择合适工具，编排工作流程，并设定质量控制标准。"})
        
        main_graph.add_node("数据分析与洞察智能体", data_analysis_subgraph,
                            metadata={
                                "description": "按照规划与策略Agent制定的执行计划，依次调用具体工具对多模态数据进行处理分析，最终生成可靠的检测结果。"})
        
        main_graph.add_node("报告生成智能体", report_generation_subgraph,
                            metadata={
                                "description": "将数据分析结果转化为专业、可读的巡检报告，包含可视化内容、预警信息和维护建议。"})

        # 设置主图结构：START -> 需求诊断 -> 规划与策略 -> 数据分析与洞察 -> 报告生成 -> END
        main_graph.add_edge(START, "需求诊断智能体")
        main_graph.add_edge("需求诊断智能体", "规划与策略智能体")
        main_graph.add_edge("规划与策略智能体", "数据分析与洞察智能体")
        main_graph.add_edge("数据分析与洞察智能体", "报告生成智能体")
        main_graph.add_edge("报告生成智能体", END)

        graph = main_graph.compile()
        graph_initialized = True

        print("✅ LangGraph初始化成功 - 使用串联结构：需求诊断智能体 -> 规划与策略智能体 -> 数据分析与洞察智能体 -> 报告生成智能体")

    except Exception as e:
        print(f"❌ LangGraph初始化失败: {e}")
        import traceback
        print(traceback.format_exc())
        graph_initialized = False


def format_message_for_frontend(message) -> Dict[str, Any]:
    """将消息格式化为前端需要的格式"""
    if hasattr(message, 'content'):
        msg_data = {
            'id': getattr(message, 'id', None) or str(hash(str(message))),
            'type': 'ai' if message.type == 'ai' else 'user' if message.type == 'human' else message.type,
            'content': message.content,
            'timestamp': datetime.now().isoformat()
        }

        # 添加工具调用信息
        if hasattr(message, 'tool_calls') and message.tool_calls:
            msg_data['tool_calls'] = [
                {
                    'name': tc.get('name', ''),
                    'args': tc.get('args', {})
                }
                for tc in message.tool_calls
            ]

        return msg_data

    elif isinstance(message, dict):
        return {
            'id': message.get('id', str(hash(str(message)))),
            'type': message.get('type', 'unknown'),
            'content': message.get('content', ''),
            'timestamp': message.get('timestamp', datetime.now().isoformat())
        }

    return {
        'id': str(hash(str(message))),
        'type': 'unknown',
        'content': str(message),
        'timestamp': datetime.now().isoformat()
    }


@app.on_event("startup")
async def startup_event():
    """启动时初始化图"""
    initialize_graph()


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "LangGraph API Server",
        "version": "1.0.0",
        "status": "running",
        "graph_initialized": graph_initialized
    }


@app.get("/status")
async def get_status():
    """获取系统状态"""
    return {
        "connected": graph_initialized,
        "nodes_count": 4 if graph_initialized else 0,  # 4个子Agent
        "subgraph_structure": {
            "需求诊断智能体": ["意图解析节点", "任务划分节点", "区域定位节点", "历史查询节点", "需求诊断总结节点"],
            "规划与策略智能体": ["策略规划节点", "工具选择节点", "工作流编排节点", "质量控制节点"],
            "数据分析与洞察智能体": ["数据预处理Agent", "检测分析Agent", "结果验证Agent", "数据分析总结节点"],
            "报告生成智能体": ["模板选择Agent", "文本生成Agent", "可视化制作Agent", "预警建议Agent", "报告格式化Agent", "报告生成总结节点"]
        } if graph_initialized else {},
        "last_update": datetime.now().isoformat(),
        "graph_ready": graph is not None
    }


async def chat_stream_generator(chat_message: ChatMessage) -> AsyncGenerator[str, None]:
    """生成流式聊天响应 - 使用LangGraph流式执行"""
    if not graph_initialized or graph is None:
        yield f"data: {json.dumps({'error': 'LangGraph未初始化'})}\n\n"
        return

    # 用于收集所有消息
    all_messages = []

    try:
        # 发送开始消息
        yield f"data: {json.dumps({'type': 'start', 'message': '开始处理消息...'})}\n\n"
        await asyncio.sleep(0.1)

        # 发送用户消息
        user_msg = {
            'id': f"user_{datetime.now().timestamp()}",
            'type': 'user',
            'content': chat_message.message,
            'timestamp': datetime.now().isoformat()
        }
        all_messages.append(user_msg)
        yield f"data: {json.dumps({'type': 'message', 'data': user_msg})}\n\n"
        await asyncio.sleep(0.1)

        # 准备初始状态
        initial_state = {
            "messages": [{"role": "user", "content": chat_message.message}]
        }

        executed_nodes = []

        # 使用LangGraph的流式执行
        for chunk in graph.stream(initial_state, subgraphs=True):
            # chunk是一个tuple: (节点路径tuple, 输出dict)
            if isinstance(chunk, tuple) and len(chunk) == 2:
                node_path_tuple, output_dict = chunk

                # 解析节点路径 - 最后一个元素是当前执行的节点
                if isinstance(node_path_tuple, tuple):
                    if len(node_path_tuple) == 0:
                        if isinstance(output_dict, dict) and len(output_dict) > 0 and str(list(output_dict.keys())[0]).find("总结") != -1:
                            last_node_with_id = list(output_dict.keys())[0]
                        else:
                            continue
                    else:
                        # 获取最后一个节点（当前执行的节点）
                        last_node_with_id = node_path_tuple[-1]

                    # 解析节点名和ID (格式: "节点名:UUID")
                    if ':' in last_node_with_id:
                        node_name, node_uuid = last_node_with_id.split(':', 1)
                    else:
                        node_name = last_node_with_id
                        node_uuid = last_node_with_id

                    # 构建完整的节点路径字符串（用于显示）
                    full_path = ' -> '.join([p.split(':')[0] for p in node_path_tuple])

                    # 记录执行的节点
                    if node_name not in executed_nodes:
                        executed_nodes.append(node_name)

                    # 发送节点执行状态
                    yield f"data: {json.dumps({'type': 'node_start', 'node': node_name, 'node_id': node_uuid, 'node_path': full_path, 'message': f'执行节点: {node_name}'})}\n\n"
                    await asyncio.sleep(0.1)

                    # 处理输出 - 检查agent键
                    node_output = None
                    if isinstance(output_dict, dict):
                        if 'agent' in output_dict:
                            node_output = output_dict['agent']
                        elif 'tools' in output_dict:
                            node_output = output_dict['tools']
                            _tool_name = find_tools_by_graph(full_path, node_output['messages'][0].name)
                            full_path = full_path.split(' -> ')[: -1]
                            full_path.append(_tool_name)
                            full_path = ' -> '.join(full_path)
                        else:
                            if len(output_dict) == 1:
                                # 1. 获取唯一的那个 key
                                unique_key = list(output_dict.keys())[0]
                                # 2. 检查 key 是否包含 "总结"
                                if str(unique_key).find('总结') != -1:
                                    # 3. 如果包含 "总结"，则取其对应的值
                                    node_output = output_dict[unique_key]
                                    full_path += ' -> ' + unique_key
                                elif str(unique_key).find('节点') != -1:
                                    node_output = output_dict[unique_key]
                                    full_path += ' -> ' + unique_key
                                else:
                                    # 4. 如果不包含 "总结"，则将整个字典赋值 (或者根据你的需求处理)
                                    node_output = None
                            else:
                                # 如果不是单键字典 (例如空字典或多键字典)，则将整个字典赋值
                                node_output = None

                    # 处理节点输出的消息
                    if isinstance(node_output, dict) and "messages" in node_output:
                        messages = node_output["messages"]
                        if isinstance(messages, list):
                            for msg in messages:
                                if hasattr(msg, 'type') and msg.type != 'human':  # 跳过用户消息
                                    formatted_msg = format_message_for_frontend(msg)

                                    # 为AI和tool消息添加节点ID信息
                                    if msg.type in ['ai', 'tool']:
                                        formatted_msg['node_id'] = node_uuid
                                        formatted_msg['node_name'] = node_name
                                        formatted_msg['node_path'] = full_path

                                    all_messages.append(formatted_msg)

                                    # 根据消息类型发送状态信息
                                    if msg.type == 'ai':
                                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                            yield f"data: {json.dumps({'type': 'status', 'message': '检测到工具调用...'})}\n\n"
                                        else:
                                            yield f"data: {json.dumps({'type': 'status', 'message': 'AI正在生成回复...'})}\n\n"
                                    elif msg.type == 'tool':
                                        tool_name = getattr(msg, 'name', '未知工具')
                                        yield f"data: {json.dumps({'type': 'status', 'message': f'工具执行: {tool_name}'})}\n\n"

                                    yield f"data: {json.dumps({'type': 'message', 'data': formatted_msg})}\n\n"
                                    await asyncio.sleep(0.1)

                    # 发送节点完成状态
                    yield f"data: {json.dumps({'type': 'node_complete', 'node': node_name, 'node_id': node_uuid, 'node_path': full_path, 'message': f'节点 {node_name} 执行完成'})}\n\n"
                    await asyncio.sleep(0.1)

        # 发送完成消息
        metadata = {
            "processing_time": "完成",
            "nodes_executed": executed_nodes,
            "timestamp": datetime.now().isoformat()
        }
        yield f"data: {json.dumps({'type': 'complete', 'metadata': metadata})}\n\n"

        # 保存聊天记录
        save_chat_record(chat_message.message, all_messages, metadata)

    except Exception as e:
        print(f"❌ 处理聊天消息失败: {e}")
        import traceback
        print(traceback.format_exc())
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

        # 即使出错也保存聊天记录
        if all_messages:
            error_metadata = {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            save_chat_record(chat_message.message, all_messages, error_metadata)


@app.post("/chat")
async def chat_stream(chat_message: ChatMessage):
    """流式聊天接口"""
    return StreamingResponse(
        chat_stream_generator(chat_message),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )


def find_tools_by_graph(path: str, tool_name: str) -> str:
    _paths = path.split(" -> ")
    node = graph
    for _path in _paths[: -1]:
        if hasattr(node, 'subgraphs') and len(node.subgraphs) > 0 and len(
                                node.subgraphs[0].nodes) >= 3:
            node = node.subgraphs[0].nodes.get(_path)
        else:
            node = node.nodes.get(_path)
    node = node.subgraphs[0].nodes
    for name, sub_node in node.items():
        if str(name).find("工具") != -1 and hasattr(sub_node, 'bound') and hasattr(sub_node.bound, 'tools_by_name'):
            tools_by_name = sub_node.bound.tools_by_name
            tool_names = list(tools_by_name.keys())
            for _tool_name in tool_names:
                if _tool_name == tool_name:
                    return name
    return ""

def analyze_graph_nested(graph_obj, parent_path="", level=0, tools_dict=None):
    """
    递归分析图结构，返回归一化的嵌套式结构
    主图和子图使用完全一致的结构

    Args:
        graph_obj: 图对象
        parent_path: 父路径，用于生成唯一ID
        level: 层级深度
        tools_dict: 工具字典，用于去重（内部使用）

    Returns:
        归一化的图结构
    """
    # 只在顶层初始化工具字典
    if tools_dict is None:
        tools_dict = {}

    result = {
        "name": parent_path.split('.')[-1] if parent_path else "主图",
        "level": level,
        "type": "graph",
        "nodes": [],
        "edges": [],
        "description": f"层级{level}的图结构",
        "statistics": {},
        "tools_dict": tools_dict  # 使用字典来去重工具
    }

    try:
        # 遍历图的所有节点
        if hasattr(graph_obj, 'nodes'):
            for node_name in graph_obj.nodes:
                if node_name in ["__start__", "__end__"]:
                    # 添加特殊节点 - 子图中的START/END也需要正确的ID
                    node_id = f"{parent_path}.{node_name}" if parent_path else node_name
                    if node_name == "__start__":
                        result["nodes"].append({
                            "id": node_id,
                            "name": "START",
                            "type": "start",
                            "level": level,
                            "description": "图执行的起始点",
                            "nodes": [],
                            "edges": []
                        })
                    elif node_name == "__end__":
                        result["nodes"].append({
                            "id": node_id,
                            "name": "END",
                            "type": "end",
                            "level": level,
                            "description": "图执行的结束点",
                            "nodes": [],
                            "edges": []
                        })
                    continue

                # 生成节点路径和ID
                node_path = f"{parent_path}.{node_name}" if parent_path else node_name

                # 归一化的节点信息 - 所有节点都有nodes和edges字段
                node_info = {
                    "id": node_path,  # 默认使用路径作为id
                    "name": node_name,
                    "type": "node",
                    "level": level,
                    "description": f"{node_name}节点",
                    "description2": f"",
                    "nodes": [],  # 归一化：所有节点都有nodes数组
                    "edges": []  # 归一化：所有节点都有edges数组
                }

                # 获取节点对象
                try:
                    node_obj = graph_obj.nodes.get(node_name)
                    if node_obj:
                        # 检查节点是否有metadata字段，并提取id和description2
                        if hasattr(node_obj, 'metadata') and node_obj.metadata:
                            if 'description' in node_obj.metadata:
                                node_info["description2"] = node_obj.metadata['description']
                        # 检查是否是子图
                        if hasattr(node_obj, 'subgraphs') and len(node_obj.subgraphs) > 0 and len(
                                node_obj.subgraphs[0].nodes) >= 3:
                            if level == 0:
                                node_info["type"] = "agent"
                                node_info["category"] = "gent"
                                node_info["description"] = f"智能体 - {node_name}"
                            else:
                                node_info["type"] = "subagent"
                                node_info["category"] = "subagent"
                                node_info["description"] = f"子智能体 - {node_name}"

                            # 递归分析子图，传递同一个tools_dict以实现去重
                            subgraph_structure = analyze_graph_nested(node_obj.subgraphs[0], node_path, level + 1,
                                                                      tools_dict)

                            # 归一化：子图结构和主图结构一致
                            node_info["nodes"] = subgraph_structure["nodes"]
                            node_info["edges"] = subgraph_structure["edges"]
                            node_info["statistics"] = subgraph_structure["statistics"]

                            # 工具已经在递归中添加到tools_dict，无需额外处理

                        # 检查是否是工具节点
                        elif hasattr(node_obj, 'bound') and hasattr(node_obj.bound, 'tools_by_name'):
                            node_info["type"] = "tool"
                            node_info["category"] = "tool"
                            tools_by_name = node_obj.bound.tools_by_name
                            tool_names = list(tools_by_name.keys())

                            # 收集工具详细信息，使用工具名称作为key去重
                            for tool_name, tool_obj in tools_by_name.items():
                                # 只在工具字典中不存在时添加（去重）
                                if tool_name not in tools_dict:
                                    tool_info = {
                                        "id": f"{node_path}.{tool_name}",
                                        "name": tool_name,
                                        "node_path": node_path,
                                        "node_name": node_name,
                                        "level": level,
                                        "description": getattr(tool_obj, 'description', '') or f"{tool_name}工具"
                                    }
                                    tools_dict[tool_name] = tool_info

                            node_info["description"] = f"工具节点 - 包含{len(tool_names)}个工具"
                            node_info["tool_names"] = tool_names  # 添加工具名称列表
                            node_info["statistics"] = {
                                "node_count": len(tool_names),
                                "edge_count": 0,
                                "subgraph_count": 0
                            }

                        else:
                            node_info["type"] = "summary"
                            node_info["category"] = "summary"
                            node_info["description"] = f"总结节点 - {node_name}"
                            node_info["statistics"] = {
                                "node_count": 0,
                                "edge_count": 0,
                                "subgraph_count": 0
                            }

                except Exception as e:
                    print(f"⚠️ 分析节点 {node_name} 时出错: {e}")
                    node_info["type"] = "unknown"
                    node_info["category"] = "unknown"
                    node_info["error"] = str(e)
                    node_info["statistics"] = {
                        "node_count": 0,
                        "edge_count": 0,
                        "subgraph_count": 0
                    }

                result["nodes"].append(node_info)

        # 获取边信息
        try:
            if hasattr(graph_obj, 'builder'):
                # 获取直接边
                if hasattr(graph_obj.builder, 'edges'):
                    for edge in graph_obj.builder.edges:
                        from_node = edge[0]
                        to_node = edge[1]

                        # 生成边的路径 - 修正：子图中的START/END也需要加上parent_path
                        if parent_path:
                            # 子图中，所有节点（包括START/END）都需要加上父路径
                            from_path = f"{parent_path}.{from_node}"
                            to_path = f"{parent_path}.{to_node}"
                        else:
                            # 主图中，直接使用节点名
                            from_path = from_node
                            to_path = to_node

                        result["edges"].append({
                            "from": from_path,
                            "to": to_path,
                            "type": "direct",
                            "label": ""
                        })

                # 获取条件边
                if hasattr(graph_obj.builder, 'branches'):
                    for source, branches in graph_obj.builder.branches.items():
                        # 修正：子图中的条件边路径也需要统一处理
                        if parent_path:
                            source_path = f"{parent_path}.{source}"
                        else:
                            source_path = source

                        if isinstance(branches, dict):
                            for condition_name, condition_info in branches.items():
                                if hasattr(condition_info, 'ends'):
                                    for end in condition_info.ends:
                                        if parent_path:
                                            end_path = f"{parent_path}.{end}"
                                        else:
                                            end_path = end

                                        result["edges"].append({
                                            "from": source_path,
                                            "to": end_path,
                                            "type": "conditional",
                                            "condition": condition_name,
                                            "label": condition_name or ""
                                        })

        except Exception as edge_error:
            print(f"⚠️ 获取边信息时出错: {edge_error}")

    except Exception as e:
        print(f"❌ 分析图结构失败 (level={level}): {e}")
        import traceback
        print(traceback.format_exc())

    # 添加统计信息
    result["statistics"] = {
        "node_count": len(result["nodes"]),
        "edge_count": len(result["edges"]),
        "subgraph_count": sum(1 for node in result["nodes"] if node.get("type") == "subagent"),
        "tool_count": len(tools_dict)  # 使用去重后的工具字典计数
    }

    return result


@app.get("/graph/info")
async def get_graph_info():
    """获取图结构信息 - 嵌套式JSON结构"""
    if not graph_initialized or graph is None:
        return {
            "error": "图未初始化",
            "graph_structure": None,
            "tools": []
        }

    try:
        # 递归分析图结构，返回嵌套式结构
        graph_structure = analyze_graph_nested(graph, "", 0)

        # 从tools_dict提取所有工具到最外层，并转换为列表
        tools_dict = graph_structure.pop("tools_dict", {})
        all_tools = list(tools_dict.values())

        return {
            "graph_ready": True,
            "graph_structure": graph_structure,
            "tools": all_tools,
            "summary": {
                "total_nodes": graph_structure["statistics"]["node_count"],
                "total_edges": graph_structure["statistics"]["edge_count"],
                "subgraph_count": graph_structure["statistics"]["subgraph_count"],
                "tool_count": len(all_tools),  # 使用去重后的工具数量
                "max_level": graph_structure["level"]
            }
        }

    except Exception as e:
        print(f"❌ 获取图信息失败: {e}")
        import traceback
        print(traceback.format_exc())
        return {
            "error": f"获取图信息失败: {str(e)}",
            "graph_structure": None,
            "tools": []
        }


@app.get("/chat/records")
async def get_chat_records():
    """获取聊天记录列表"""
    try:
        ensure_chat_record_dir()

        if not os.path.exists(CHAT_RECORD_DIR):
            return {"records": [], "count": 0}

        records = []
        for filename in os.listdir(CHAT_RECORD_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(CHAT_RECORD_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # 只返回基本信息，不包含完整消息内容
                    record_info = {
                        "filename": filename,
                        "timestamp": data.get("timestamp", ""),
                        "question": data.get("question", "")[:100] + "..." if len(
                            data.get("question", "")) > 100 else data.get("question", ""),
                        "total_messages": data.get("total_messages", 0),
                        "nodes_executed": data.get("metadata", {}).get("nodes_executed", [])
                    }
                    records.append(record_info)
                except Exception as e:
                    print(f"⚠️ 读取聊天记录文件 {filename} 失败: {e}")

        # 按时间戳排序，最新的在前
        records.sort(key=lambda x: x["timestamp"], reverse=True)

        return {
            "records": records,
            "count": len(records)
        }

    except Exception as e:
        print(f"❌ 获取聊天记录失败: {e}")
        return {"error": f"获取聊天记录失败: {str(e)}", "records": [], "count": 0}


@app.get("/chat/records/{filename}")
async def get_chat_record(filename: str):
    """获取指定聊天记录的详细内容"""
    try:
        ensure_chat_record_dir()

        # 安全检查，防止路径遍历攻击
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="无效的文件名")

        filepath = os.path.join(CHAT_RECORD_DIR, filename)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="聊天记录不存在")

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return data

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 获取聊天记录详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取聊天记录详情失败: {str(e)}")


if __name__ == "__main__":
    import importlib.util

    print("🚀 启动LangGraph测试API服务器...")
    print("📍 API地址: http://localhost:8001")
    print("📚 API文档: http://localhost:8001/docs")
    print("🔧 状态检查: http://localhost:8001/status")
    print()

    # 初始化图
    initialize_graph()

    # 查找可用的ASGI服务器并启动
    servers = [
        ("uvicorn", "uvicorn"),
        ("hypercorn", "hypercorn"),
    ]

    server_found = False
    for server_name, module_name in servers:
        if importlib.util.find_spec(module_name):
            print(f"✅ 使用 {server_name} 启动服务器...")

            if server_name == "uvicorn":
                import uvicorn

                uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
            elif server_name == "hypercorn":
                import subprocess
                import sys

                subprocess.run([sys.executable, "-m", "hypercorn", "backend_api:app", "--bind", "0.0.0.0:8001"])

            server_found = True
            break

    if not server_found:
        print("❌ 未找到可用的ASGI服务器")
        print("请安装以下任意一个:")
        print("  pip install uvicorn")
        print("  pip install hypercorn")
        print()
        print("或者使用FastAPI CLI:")
        print("  pip install 'fastapi[standard]'")
        print("  fastapi dev backend_api.py")
