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
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Set
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

# 导入巡检智能体
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


# ===================== FastAPI 应用 =====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global inspection_agent
    
    # 1. 首先初始化故障分析核心模块并导入知识库
    print("🚀 正在初始化故障分析核心模块...")
    try:
        from fault_analysis_core import initialize
        
        # 获取图谱数据文件路径（相对于 backend.py 的位置）
        script_dir = os.path.dirname(os.path.abspath(__file__))
        graph_data_path = os.path.join(script_dir, "inspection_analysis_demo", "zhongche_graph_documents.pkl")
        
        # 如果文件不存在，尝试其他可能的路径
        if not os.path.exists(graph_data_path):
            # 尝试直接使用相对路径
            graph_data_path = os.path.join("inspection_analysis_demo", "zhongche_graph_documents.pkl")
        
        if os.path.exists(graph_data_path):
            print(f"📂 找到图谱数据文件: {graph_data_path}")
            success = initialize(graph_data_path=graph_data_path)
            if success:
                print("✅ 故障分析核心模块初始化成功，知识库已导入！")
            else:
                print("⚠️ 故障分析核心模块初始化失败，但将继续启动服务")
        else:
            print(f"⚠️ 图谱数据文件不存在: {graph_data_path}")
            print("   将使用空知识库启动（首次运行或数据文件未找到）")
            # 即使文件不存在，也尝试初始化（可能数据库已有数据）
            initialize()
    except Exception as e:
        print(f"⚠️ 故障分析核心模块初始化异常: {e}")
        import traceback
        traceback.print_exc()
        # 即使初始化失败，也尝试继续启动服务
        try:
            from fault_analysis_core import initialize
            initialize()
        except:
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
        # 用户提交了故障工单
        form_data = payload.get("form_data", {})
        query_message = payload.get("query_message", "")  # 包装好的查询消息
        
        if not form_data:
            await manager.send_message(websocket, WSMessage(
                type="system",
                action="error",
                data={"error": "表单数据不能为空"}
            ))
            return

        if inspection_agent is None:
            await manager.send_message(websocket, WSMessage(
                type="system",
                action="error",
                data={"error": "智能体未初始化"}
            ))
            return

        # 发送开始处理消息
        await manager.send_message(websocket, WSMessage(
            type="chat",
            action="start",
            data={"message": "正在分析故障工单信息..."}
        ))

        try:
            # 创建回调函数
            async def send_callback(msg_type: str, action: str, data: dict):
                await manager.send_message(websocket, WSMessage(
                    type=msg_type,
                    action=action,
                    data=data
                ))

            # 构造巡检输入
            inspection_input = InspectionInput(
                detect_time=form_data.get("detect_time", datetime.now().strftime("%Y-%m-%d %H:%M")),
                part_name=form_data.get("part_name", ""),
                part_position=form_data.get("part_position", ""),
                defect_type=form_data.get("defect_type", ""),
                detect_confidence=float(form_data.get("detect_confidence", 0.95))
            )

            # 调用故障分析
            await inspection_agent.run_fault_analysis(inspection_input, send_callback)

            # 发送完成消息
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
if __name__ == "__main__":
    import importlib.util

    print("🚀 启动巡检智能体 WebSocket 服务...")
    print("📍 HTTP API: http://localhost:8001")
    print("📍 WebSocket: ws://localhost:8001/ws")
    print("📚 API 文档: http://localhost:8001/docs")
    print()

    if importlib.util.find_spec("uvicorn"):
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
    else:
        print("❌ 请安装 uvicorn: pip install uvicorn")

