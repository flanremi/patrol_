#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
巡检智能体 WebSocket 后端服务
提供 WebSocket 接口与前端通信
消息类型：system、chat、tool
"""
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Set
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 从 backend 所在目录加载 .env，保证无论从哪启动都能读到 RAG_MODE 等配置
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(_env_path)

# 导入巡检智能体（其内部会按 rag_config.RAG_MODE 决定是否连接 Neo4j）
from inspection_agent import InspectionAgent, InspectionInput


# ===================== WebSocket 消息协议 =====================
class WSMessage(BaseModel):
    """WebSocket 消息基类"""
    type: str  # system | chat | tool
    action: str  # 具体动作
    data: Optional[Dict[str, Any]] = None
    timestamp: str = None
    message_id: str = None

    def __init__(self, **data):
        if 'timestamp' not in data or data['timestamp'] is None:
            data['timestamp'] = datetime.now().isoformat()
        if 'message_id' not in data or data['message_id'] is None:
            data['message_id'] = str(uuid.uuid4())[:8]
        super().__init__(**data)


# ===================== 连接管理器 =====================
class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.connection_info: Dict[WebSocket, Dict] = {}

    async def connect(self, websocket: WebSocket) -> str:
        """接受连接"""
        await websocket.accept()
        self.active_connections.add(websocket)
        connection_id = str(uuid.uuid4())[:8]
        self.connection_info[websocket] = {
            "id": connection_id,
            "connected_at": datetime.now().isoformat()
        }
        print(f"✅ 新连接: {connection_id}")
        return connection_id

    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        if websocket in self.active_connections:
            conn_id = self.connection_info.get(websocket, {}).get("id", "unknown")
            self.active_connections.discard(websocket)
            self.connection_info.pop(websocket, None)
            print(f"❌ 断开连接: {conn_id}")

    async def send_message(self, websocket: WebSocket, message: WSMessage):
        """发送消息到指定连接"""
        try:
            await websocket.send_json(message.model_dump())
        except Exception as e:
            print(f"⚠️ 发送消息失败: {e}")

    async def broadcast(self, message: WSMessage):
        """广播消息到所有连接"""
        for connection in self.active_connections:
            await self.send_message(connection, message)


# ===================== 全局变量 =====================
manager = ConnectionManager()
inspection_agent: Optional[InspectionAgent] = None


# ===================== RAG 接入方案配置 =====================
# 与 rag_config 保持一致，单一数据源，避免与 inspection_agent 不同步
def _get_rag_mode():
    from rag_config import RAG_MODE
    return RAG_MODE


# ===================== FastAPI 应用 =====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global inspection_agent
    script_dir = os.path.dirname(os.path.abspath(__file__))
    rag_mode = _get_rag_mode()
    print(f"📌 当前 RAG 接入方案: {rag_mode} (graph=知识图谱+向量, vector=纯向量文档)")

    # 1. 根据 RAG_MODE 初始化故障分析核心模块
    if rag_mode == "vector":
        # ---------- 向量库方案：校验向量库是否存在，不存在则执行激活脚本 ----------
        try:
            from rag_config import vector_db_exists, INIT_VECTOR_DB_SCRIPT
            if not vector_db_exists():
                print("⚠️ 向量数据库不存在，正在执行激活脚本...")
                import subprocess
                ret = subprocess.run(
                    [sys.executable, INIT_VECTOR_DB_SCRIPT],
                    cwd=script_dir,
                    capture_output=False,
                    timeout=600,
                )
                if ret.returncode != 0:
                    print("⚠️ 向量数据库激活脚本执行失败，将尝试继续启动（可能使用空库）")
            else:
                print("✅ 向量数据库已存在，跳过激活脚本")
        except Exception as e:
            print(f"⚠️ 向量库校验/激活异常: {e}")
            import traceback
            traceback.print_exc()

        print("🚀 正在初始化故障分析核心模块（纯向量库 RAG）...")
        try:
            from fault_analysis_core_vector import initialize as init_vector
            success = init_vector()
            if success:
                print("✅ 故障分析核心模块（向量库版）初始化成功！")
            else:
                print("⚠️ 故障分析核心模块（向量库版）初始化失败，但将继续启动服务")
        except Exception as e:
            print(f"⚠️ 故障分析核心模块（向量库版）初始化异常: {e}")
            import traceback
            traceback.print_exc()
    else:
        # ---------- 图谱方案：原有逻辑 ----------
        print("🚀 正在初始化故障分析核心模块（知识图谱+向量）...")
        try:
            from fault_analysis_core import initialize
            graph_data_path = os.path.join(script_dir, "inspection_analysis_demo", "zhongche_graph_documents.pkl")
            if not os.path.exists(graph_data_path):
                graph_data_path = os.path.join("inspection_analysis_demo", "zhongche_graph_documents.pkl")
            if os.path.exists(graph_data_path):
                print(f"📂 找到图谱数据文件: {graph_data_path}")
                success = initialize(graph_data_path=graph_data_path)
            else:
                print("⚠️ 图谱数据文件不存在，将使用空知识库启动")
                success = initialize()
            if success:
                print("✅ 故障分析核心模块初始化成功，知识库已导入！")
            else:
                print("⚠️ 故障分析核心模块初始化失败，但将继续启动服务")
        except Exception as e:
            print(f"⚠️ 故障分析核心模块初始化异常: {e}")
            import traceback
            traceback.print_exc()
            try:
                from fault_analysis_core import initialize
                initialize()
            except Exception:
                pass

    # 2. 初始化巡检智能体
    print("🚀 正在初始化巡检智能体...")
    try:
        inspection_agent = InspectionAgent()
        print("✅ 巡检智能体初始化成功！")
    except Exception as e:
        print(f"❌ 巡检智能体初始化失败: {e}")
        import traceback
        traceback.print_exc()
    
    yield
    print("👋 服务关闭")


app = FastAPI(
    title="巡检智能体 WebSocket API",
    version="1.0.0",
    lifespan=lifespan
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===================== HTTP 端点 =====================
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "巡检智能体 WebSocket API",
        "version": "1.0.0",
        "status": "running",
        "websocket_endpoint": "/ws",
        "agent_ready": inspection_agent is not None
    }


@app.get("/status")
async def get_status():
    """获取系统状态"""
    return {
        "connected": inspection_agent is not None,
        "active_connections": len(manager.active_connections),
        "agent_ready": inspection_agent is not None,
        "rag_mode": _get_rag_mode(),
        "last_update": datetime.now().isoformat()
    }


@app.get("/graph/info")
async def get_graph_info():
    """获取图结构信息"""
    if inspection_agent is None:
        return {"error": "智能体未初始化", "graph_structure": None}

    try:
        graph_structure = inspection_agent.get_graph_structure()
        return {
            "graph_ready": True,
            "graph_structure": graph_structure,
            "tools": inspection_agent.get_tools_info()
        }
    except Exception as e:
        return {"error": str(e), "graph_structure": None}


# ===================== WebSocket 端点 =====================
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 主端点"""
    connection_id = await manager.connect(websocket)

    # 发送连接成功消息
    await manager.send_message(websocket, WSMessage(
        type="system",
        action="connected",
        data={
            "connection_id": connection_id,
            "agent_ready": inspection_agent is not None
        }
    ))

    try:
        while True:
            # 接收消息
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
                await handle_message(websocket, data)
            except json.JSONDecodeError:
                await manager.send_message(websocket, WSMessage(
                    type="system",
                    action="error",
                    data={"error": "无效的 JSON 格式"}
                ))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"❌ WebSocket 错误: {e}")
        manager.disconnect(websocket)


async def handle_message(websocket: WebSocket, data: Dict[str, Any]):
    """处理接收到的消息"""
    msg_type = data.get("type", "")
    action = data.get("action", "")
    payload = data.get("data", {})

    print(f"📨 收到消息: type={msg_type}, action={action}")

    if msg_type == "system":
        await handle_system_message(websocket, action, payload)
    elif msg_type == "chat":
        await handle_chat_message(websocket, action, payload)
    elif msg_type == "tool":
        await handle_tool_message(websocket, action, payload)
    else:
        await manager.send_message(websocket, WSMessage(
            type="system",
            action="error",
            data={"error": f"未知消息类型: {msg_type}"}
        ))


async def handle_system_message(websocket: WebSocket, action: str, payload: Dict):
    """处理系统消息"""
    if action == "ping":
        await manager.send_message(websocket, WSMessage(
            type="system",
            action="pong",
            data={"time": datetime.now().isoformat()}
        ))
    elif action == "status":
        await manager.send_message(websocket, WSMessage(
            type="system",
            action="status",
            data={
                "agent_ready": inspection_agent is not None,
                "connections": len(manager.active_connections)
            }
        ))
    else:
        await manager.send_message(websocket, WSMessage(
            type="system",
            action="error",
            data={"error": f"未知系统动作: {action}"}
        ))


async def handle_chat_message(websocket: WebSocket, action: str, payload: Dict):
    """处理聊天消息"""
    if action == "send":
        message = payload.get("message", "")
        if not message:
            await manager.send_message(websocket, WSMessage(
                type="system",
                action="error",
                data={"error": "消息内容不能为空"}
            ))
            return

        if inspection_agent is None:
            await manager.send_message(websocket, WSMessage(
                type="system",
                action="error",
                data={"error": "智能体未初始化"}
            ))
            return

        # 开始处理
        await manager.send_message(websocket, WSMessage(
            type="chat",
            action="start",
            data={"message": "开始处理消息..."}
        ))

        try:
            # 创建回调函数用于流式输出
            async def send_callback(msg_type: str, action: str, data: dict):
                await manager.send_message(websocket, WSMessage(
                    type=msg_type,
                    action=action,
                    data=data
                ))

            # 调用智能体处理消息
            await inspection_agent.process_message(message, send_callback)

            # 发送完成消息
            await manager.send_message(websocket, WSMessage(
                type="chat",
                action="complete",
                data={"message": "处理完成"}
            ))

        except Exception as e:
            print(f"❌ 处理消息失败: {e}")
            import traceback
            traceback.print_exc()
            await manager.send_message(websocket, WSMessage(
                type="chat",
                action="error",
                data={"error": str(e)}
            ))
    else:
        await manager.send_message(websocket, WSMessage(
            type="system",
            action="error",
            data={"error": f"未知聊天动作: {action}"}
        ))


async def handle_tool_message(websocket: WebSocket, action: str, payload: Dict):
    """处理工具消息"""
    if action == "form_submit":
        form_data = payload.get("form_data", {})
        if not form_data:
            await manager.send_message(websocket, WSMessage(
                type="system",
                action="error",
                data={"error": "表单数据不能为空"}
            ))
            return

        rag_mode = _get_rag_mode()
        detect_time = form_data.get("detect_time", datetime.now().strftime("%Y-%m-%d %H:%M"))
        part_name = form_data.get("part_name", "")
        part_position = form_data.get("part_position", "")
        defect_type = form_data.get("defect_type", "")
        detect_confidence = float(form_data.get("detect_confidence", 0.95))

        async def send_callback(msg_type: str, action: str, data: dict):
            await manager.send_message(websocket, WSMessage(type=msg_type, action=action, data=data))

        # vector 模式：独立逻辑，直接走 fault_analysis_core_vector，不经过 inspection_agent
        if rag_mode == "vector":
            try:
                await manager.send_message(websocket, WSMessage(
                    type="chat",
                    action="start",
                    data={"message": "正在分析故障工单信息（向量 RAG）..."}
                ))
                from fault_analysis_core_vector import initialize, run_fault_analysis_async
                if not initialize():
                    await manager.send_message(websocket, WSMessage(
                        type="tool",
                        action="analysis_error",
                        data={"error": "故障分析模块初始化失败", "message": "请检查向量数据库与 LLM 配置"}
                    ))
                    return
                result = await run_fault_analysis_async(
                    detect_time=detect_time,
                    part_name=part_name,
                    part_position=part_position,
                    defect_type=defect_type,
                    detect_confidence=detect_confidence,
                    ws_callback=send_callback,
                )
                await send_callback("tool", "analysis_complete", {
                    "final_report": result.final_report,
                    "retry_count": result.retry_count,
                    "thinking_processes": result.thinking_processes,
                    "input": {
                        "part_name": part_name,
                        "defect_type": defect_type,
                        "part_position": part_position,
                        "detect_time": detect_time,
                        "detect_confidence": detect_confidence,
                    },
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                await manager.send_message(websocket, WSMessage(
                    type="chat",
                    action="complete",
                    data={"message": "故障分析完成"}
                ))
            except Exception as e:
                print(f"❌ 向量模式故障分析失败: {e}")
                import traceback
                traceback.print_exc()
                await manager.send_message(websocket, WSMessage(
                    type="chat",
                    action="error",
                    data={"error": str(e)}
                ))
            return

        # graph 模式：经 inspection_agent，使用知识图谱+向量
        if inspection_agent is None:
            await manager.send_message(websocket, WSMessage(
                type="system",
                action="error",
                data={"error": "智能体未初始化"}
            ))
            return
        await manager.send_message(websocket, WSMessage(
            type="chat",
            action="start",
            data={"message": "正在分析故障工单信息..."}
        ))
        try:
            inspection_input = InspectionInput(
                detect_time=detect_time,
                part_name=part_name,
                part_position=part_position,
                defect_type=defect_type,
                detect_confidence=detect_confidence,
            )
            await inspection_agent.run_fault_analysis(inspection_input, send_callback)
            await manager.send_message(websocket, WSMessage(
                type="chat",
                action="complete",
                data={"message": "故障分析完成"}
            ))
        except Exception as e:
            print(f"❌ 处理表单失败: {e}")
            import traceback
            traceback.print_exc()
            await manager.send_message(websocket, WSMessage(
                type="chat",
                action="error",
                data={"error": str(e)}
            ))
    else:
        await manager.send_message(websocket, WSMessage(
            type="system",
            action="error",
            data={"error": f"未知工具动作: {action}"}
        ))


# ===================== 启动入口 =====================
def run_uvicorn():
    """使用 uvicorn 启动（开发模式）"""
    import uvicorn
    print("🚀 启动巡检智能体 WebSocket 服务 (Uvicorn)...")
    print("📍 HTTP API: http://localhost:8001")
    print("📍 WebSocket: ws://localhost:8001/ws")
    print("📚 API 文档: http://localhost:8001/docs")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")


if __name__ == "__main__":
    import importlib.util

    if importlib.util.find_spec("uvicorn"):
        run_uvicorn()
    else:
        print("❌ 请安装 uvicorn: pip install uvicorn")

