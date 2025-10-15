#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangGraph后端API服务器
提供前端所需的API接口
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, AsyncGenerator
import json
from datetime import datetime
import os
import asyncio

# 导入我们的LangGraph组件
from chatbot_node import city_weather, create_router_node
from fault_graph import search_fault
from summary_node import create_summary_node
from yolo_agent_tool import yolo_detect_tool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict
from typing import Annotated
from langgraph.graph.message import add_messages
import memory_graph

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

def initialize_graph():
    """初始化LangGraph"""
    global graph, graph_initialized
    
    if graph_initialized:
        return
    
    try:
        # 创建节点实例
        chatbot_node = create_router_node()
        summary_node = create_summary_node()

        # 创建工具节点
        search_tool = ToolNode([search_fault])
        
        # 创建记忆相关的独立节点
        memory_node = memory_graph.create_memory_node()
        memory_tool_node = memory_graph.create_memory_tool_node()

        # 创建图
        graph_builder = StateGraph(State)
        graph_builder.add_node("router", chatbot_node)
        graph_builder.add_node("memory", memory_node)
        graph_builder.add_node("memory_tool", memory_tool_node)
        graph_builder.add_node("search_tool", search_tool)
        graph_builder.add_node("summary", summary_node)

        # 设置图的流程
        graph_builder.add_edge(START, "memory")


        # 添加条件边 - 更新路由逻辑
        def should_continue(state: State):
            messages = state["messages"]
            last_message = messages[-1]
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "search_tool"
            # elif str(last_message.content).find("call_memory") != -1:
            #     return "memory"
            return "summary"
        
        graph_builder.add_conditional_edges("router", should_continue,
                                            {
                                                "search_tool": "search_tool",
                                                "summary": "summary"
                                            })
        
        # 添加边连接
        graph_builder.add_edge("search_tool", "summary")
        graph_builder.add_edge("memory", "memory_tool")  # memory节点调用工具后进入memory_tool
        graph_builder.add_edge("memory_tool", "router")  # memory_tool执行完成后回到路由
        graph_builder.add_edge("summary", END)
        
        graph = graph_builder.compile()
        graph_initialized = True
        print("✅ LangGraph初始化成功")
        
    except Exception as e:
        print(f"❌ LangGraph初始化失败: {e}")
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
        "nodes_count": 5 if graph_initialized else 0,  # router, memory, memory_tool, tool, summary
        "tools_count": 4 if graph_initialized else 0,  # yolo_detect_tool, city_weather, search_memory, store_memory
        "last_update": datetime.now().isoformat(),
        "graph_ready": graph is not None
    }

async def chat_stream_generator(chat_message: ChatMessage) -> AsyncGenerator[str, None]:
    """生成流式聊天响应 - 使用LangGraph流式执行"""
    if not graph_initialized or graph is None:
        yield f"data: {json.dumps({'error': 'LangGraph未初始化'})}\n\n"
        return
    
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
        yield f"data: {json.dumps({'type': 'message', 'data': user_msg})}\n\n"
        await asyncio.sleep(0.1)
        
        # 准备初始状态
        initial_state = {
            "messages": [{"role": "user", "content": chat_message.message}]
        }
        
        executed_nodes = []
        
        # 使用LangGraph的流式执行
        for chunk in graph.stream(initial_state):
            # chunk是一个字典，键是节点名，值是节点的输出
            for node_name, node_output in chunk.items():
                executed_nodes.append(node_name)
                
                # 发送节点执行状态
                yield f"data: {json.dumps({'type': 'node_start', 'node': node_name, 'message': f'执行节点: {node_name}'})}\n\n"
                await asyncio.sleep(0.1)
                
                # 处理节点输出的消息
                if isinstance(node_output, dict) and "messages" in node_output:
                    messages = node_output["messages"]
                    if isinstance(messages, list):
                        for msg in messages:
                            if hasattr(msg, 'type') and msg.type != 'human':  # 跳过用户消息
                                formatted_msg = format_message_for_frontend(msg)
                                
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
                yield f"data: {json.dumps({'type': 'node_complete', 'node': node_name, 'message': f'节点 {node_name} 执行完成'})}\n\n"
                await asyncio.sleep(0.1)

        # 发送完成消息
        metadata = {
            "processing_time": "完成",
            "nodes_executed": executed_nodes,
            "timestamp": datetime.now().isoformat()
        }
        yield f"data: {json.dumps({'type': 'complete', 'metadata': metadata})}\n\n"
        
    except Exception as e:
        print(f"❌ 处理聊天消息失败: {e}")
        import traceback
        print(traceback.format_exc())
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

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


# 需要重写逻辑
@app.get("/graph/info")
async def get_graph_info():
    """获取图结构信息 - 动态从实际图中获取"""
    if not graph_initialized or graph is None:
        return {
            "error": "图未初始化",
            "nodes": [],
            "edges": [],
            "tools": []
        }
    
    try:
        # 从编译后的图中获取节点信息
        nodes = []
        edges = []
        tools = []
        
        # 获取图的内部结构
        if hasattr(graph, 'nodes'):
            # 添加START和END特殊节点
            nodes.append({
                "id": "__start__", 
                "name": "START", 
                "label": "开始",
                "type": "start",
                "description": "图执行的起始点"
            })
            
            # 获取实际定义的节点
            for node_name in graph.nodes:
                if node_name not in ["__start__", "__end__"]:
                    # 动态识别节点类型和属性
                    node_info = {
                        "id": node_name,
                        "name": node_name,
                        "label": node_name,
                        "type": node_name,  # 使用节点名称作为类型
                        "description": f"{node_name}节点"
                    }
                    
                    # 尝试获取节点对象的更多信息
                    try:
                        node_obj = graph.nodes.get(node_name)
                        if node_obj:
                            # 检查是否是工具节点
                            if str(node_name).find("tool") != -1:
                                node_info["category"] = "tool"
                                node_info["tools"] = [tool_name for tool_name in node_obj.bound.tools_by_name]
                                for tool_name, tool_info in node_obj.bound.tools_by_name.items():
                                    tool_info = {
                                        "name": tool_name,
                                        "description": tool_info.description
                                    }
                                    tools.append(tool_info)
                                node_info["description"] = f"工具节点 - 包含{len(node_obj.bound.tools_by_name)}个工具"
                            # 检查是否是函数节点
                            elif callable(node_obj):
                                node_info["category"] = "function"
                                node_info["description"] = f"函数节点 - {node_name}"
                            else:
                                node_info["category"] = "custom"
                                node_info["description"] = f"自定义节点 - {node_name}"
                    except Exception as e:
                        print(f"⚠️ 获取节点{node_name}信息时出错: {e}")
                        node_info["category"] = "unknown"
                    
                    nodes.append(node_info)
            
            nodes.append({
                "id": "__end__", 
                "name": "END", 
                "label": "结束",
                "type": "end",
                "description": "图执行的结束点"
            })
        
        # 获取边信息 - 更全面地从图中提取
        try:
            # 获取直接边
            if graph.builder and hasattr(graph.builder, 'edges'):
                for edge in graph.builder.edges:
                    edge_info = {
                        "from": edge[0] if edge[0] != "__start__" else "__start__",
                        "to": edge[1] if edge[1] != "__end__" else "__end__",
                        "type": "direct",
                        "label": ""
                    }
                    edges.append(edge_info)
            
            # 获取条件边信息
            if  graph.builder and hasattr(graph.builder, 'branches'):
                for source, branches in graph.builder.branches.items():
                    if isinstance(branches, dict):
                        for condition_name, condition_info  in branches.items():
                            for end in condition_info.ends:
                                edge_info = {
                                    "from": source,
                                    "to": end if end != "__end__" else "__end__",
                                    "type": "conditional",
                                    "condition": condition_name,
                                    "label": condition_name if condition_name else ""
                                }
                                edges.append(edge_info)
                    else:
                        # 处理非字典类型的分支
                        edge_info = {
                            "from": source,
                            "to": branches if branches != "__end__" else "__end__",
                            "type": "conditional",
                            "label": "条件分支"
                        }
                        edges.append(edge_info)

                    
        except Exception as edge_error:
            print(f"⚠️ 获取边信息时出错: {edge_error}")


        return {
            "nodes": nodes,
            "edges": edges,
            "tools": tools,
            "graph_ready": True,
            "nodes_count": len(nodes),
            "edges_count": len(edges),
            "tools_count": len(tools)
        }
        
    except Exception as e:
        print(f"❌ 获取图信息失败: {e}")
        return {
            "error": f"获取图信息失败: {str(e)}",
            "nodes": [],
            "edges": [],
            "tools": []
        }

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
