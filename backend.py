#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
巡检智能体 WebSocket 后端服务
提供 WebSocket 接口与前端通信
消息类型：system、chat、tool
支持会话历史记录（生命周期：WebSocket 连接建立到断开）
"""
import asyncio
import json
import os
import sys
import uuid
import concurrent.futures
from datetime import datetime
from typing import Dict, Any, Optional, Set, List
from contextlib import asynccontextmanager
from functools import partial

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

# 从 backend 所在目录加载 .env，保证无论从哪启动都能读到 RAG_MODE 等配置
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(_env_path)

# 导入巡检智能体（其内部会按 rag_config.RAG_MODE 决定是否连接 Neo4j）
from inspection_agent import InspectionAgent, InspectionInput

# 导入新的模块化 Agent
from message_queue import (
    MessageQueue, MessageQueueManager, MessageRole, AgentType,
    generate_message_header, WSMessageBuilder, message_queue_manager
)
from planning_agent import PlanningAgent
from repair_agent import RepairAgent
from quality_agent import QualityAgent
from training_agent import TrainingAgent
from field_guidance_agent import FieldGuidanceAgent


# ===================== 会话历史管理 =====================
class SessionHistory:
    """会话历史记录 - 每个 WebSocket 连接独立维护"""
    
    def __init__(self, connection_id: str):
        self.connection_id = connection_id
        self.messages: List[Dict[str, Any]] = []  # 存储消息历史
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
    
    def add_user_message(self, content: str):
        """添加用户消息"""
        self.messages.append({
            "role": "user",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.last_activity = datetime.now()
        print(f"📝 [会话 {self.connection_id}] 添加用户消息，当前消息数: {len(self.messages)}")
    
    def add_ai_message(self, content: str):
        """添加 AI 消息"""
        self.messages.append({
            "role": "assistant",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.last_activity = datetime.now()
        print(f"📝 [会话 {self.connection_id}] 添加 AI 消息，当前消息数: {len(self.messages)}")
    
    def add_system_message(self, content: str):
        """添加系统消息"""
        self.messages.append({
            "role": "system",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.last_activity = datetime.now()
    
    def get_langchain_messages(self) -> List:
        """转换为 LangChain 消息格式"""
        lc_messages = []
        for msg in self.messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_messages.append(AIMessage(content=msg["content"]))
        return lc_messages
    
    def get_message_count(self) -> int:
        """获取消息数量"""
        return len(self.messages)
    
    def clear(self):
        """清空历史"""
        self.messages = []
        print(f"🗑️ [会话 {self.connection_id}] 历史已清空")
    
    def add_analysis_report(self, task_id: str, report_summary: str):
        """添加分析报告摘要到历史（作为系统消息供 LLM 参考）"""
        self.messages.append({
            "role": "assistant",
            "content": f"[故障分析报告 {task_id}]\n{report_summary}",
            "timestamp": datetime.now().isoformat(),
            "type": "analysis_report",
            "task_id": task_id
        })
        self.last_activity = datetime.now()
        print(f"📊 [会话 {self.connection_id}] 添加分析报告到历史，task_id: {task_id}")


# ===================== 分析任务管理 =====================
class AnalysisTask:
    """分析任务 - 存储分析状态和结果"""
    
    def __init__(self, task_id: str, connection_id: str, input_data: Dict[str, Any]):
        self.task_id = task_id
        self.connection_id = connection_id
        self.input_data = input_data  # 工单输入数据
        self.status = "pending"  # pending | running | completed | error
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.steps: List[Dict[str, Any]] = []  # 分析步骤
        self.final_report: Optional[str] = None  # 最终报告（Markdown）
        self.thinking_processes: List[Dict[str, Any]] = []  # 思考过程
        self.error: Optional[str] = None
        self.retry_count: int = 0
    
    def start(self):
        """开始分析"""
        self.status = "running"
        self.updated_at = datetime.now()
    
    def add_step(self, step: Dict[str, Any]):
        """添加分析步骤"""
        self.steps.append({
            **step,
            "timestamp": datetime.now().isoformat()
        })
        self.updated_at = datetime.now()
    
    def complete(self, final_report: str, thinking_processes: List[Dict[str, Any]] = None):
        """完成分析"""
        self.status = "completed"
        self.final_report = final_report
        self.thinking_processes = thinking_processes or []
        self.updated_at = datetime.now()
    
    def fail(self, error: str):
        """分析失败"""
        self.status = "error"
        self.error = error
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "connection_id": self.connection_id,
            "input_data": self.input_data,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "steps": self.steps,
            "final_report": self.final_report,
            "thinking_processes": self.thinking_processes,
            "error": self.error,
            "retry_count": self.retry_count
        }
    
    def get_report_summary(self, max_length: int = 500) -> str:
        """获取报告摘要（用于加入对话历史）"""
        if not self.final_report:
            return f"分析任务 {self.task_id} 尚未完成"
        
        # 提取报告的关键部分作为摘要
        summary_parts = []
        summary_parts.append(f"部件: {self.input_data.get('part_name', '未知')}")
        summary_parts.append(f"缺陷: {self.input_data.get('defect_type', '未知')}")
        summary_parts.append(f"位置: {self.input_data.get('part_position', '未知')}")
        
        # 截取报告内容
        report_preview = self.final_report[:max_length]
        if len(self.final_report) > max_length:
            report_preview += "...(报告已截断)"
        
        return f"基本信息: {', '.join(summary_parts)}\n报告摘要:\n{report_preview}"


class AnalysisTaskManager:
    """分析任务管理器 - 全局单例"""
    
    def __init__(self):
        self.tasks: Dict[str, AnalysisTask] = {}
        self._lock = asyncio.Lock()
    
    def create_task(self, connection_id: str, input_data: Dict[str, Any]) -> AnalysisTask:
        """创建新的分析任务"""
        task_id = str(uuid.uuid4())[:8]
        task = AnalysisTask(task_id, connection_id, input_data)
        self.tasks[task_id] = task
        print(f"📋 [任务管理] 创建分析任务: {task_id}, 输入: {input_data.get('part_name', '')} - {input_data.get('defect_type', '')}")
        return task
    
    def get_task(self, task_id: str) -> Optional[AnalysisTask]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def get_tasks_by_connection(self, connection_id: str) -> List[AnalysisTask]:
        """获取连接的所有任务"""
        return [t for t in self.tasks.values() if t.connection_id == connection_id]
    
    def cleanup_connection(self, connection_id: str):
        """清理连接的任务（可选：保留已完成的）"""
        to_remove = [tid for tid, t in self.tasks.items() 
                     if t.connection_id == connection_id and t.status != "completed"]
        for tid in to_remove:
            del self.tasks[tid]
        print(f"🗑️ [任务管理] 清理连接 {connection_id} 的未完成任务: {len(to_remove)} 个")


# 全局分析任务管理器
analysis_task_manager = AnalysisTaskManager()


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
    """WebSocket 连接管理器 - 支持会话历史"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.connection_info: Dict[WebSocket, Dict] = {}
        self.session_histories: Dict[WebSocket, SessionHistory] = {}  # 会话历史

    async def connect(self, websocket: WebSocket) -> str:
        """接受连接并创建会话历史"""
        await websocket.accept()
        self.active_connections.add(websocket)
        connection_id = str(uuid.uuid4())[:8]
        self.connection_info[websocket] = {
            "id": connection_id,
            "connected_at": datetime.now().isoformat()
        }
        # 创建会话历史
        self.session_histories[websocket] = SessionHistory(connection_id)
        print(f"✅ 新连接: {connection_id}，已创建会话历史")
        return connection_id

    def disconnect(self, websocket: WebSocket):
        """断开连接并清理会话历史和分析任务"""
        if websocket in self.active_connections:
            conn_id = self.connection_info.get(websocket, {}).get("id", "unknown")
            history = self.session_histories.get(websocket)
            msg_count = history.get_message_count() if history else 0
            
            self.active_connections.discard(websocket)
            self.connection_info.pop(websocket, None)
            self.session_histories.pop(websocket, None)  # 清理会话历史
            
            # 清理该连接的分析任务（可选保留已完成的）
            analysis_task_manager.cleanup_connection(conn_id)
            
            print(f"❌ 断开连接: {conn_id}，会话历史已清理（共 {msg_count} 条消息）")

    def get_session_history(self, websocket: WebSocket) -> Optional[SessionHistory]:
        """获取会话历史"""
        return self.session_histories.get(websocket)
    
    def get_connection_id(self, websocket: WebSocket) -> str:
        """获取连接 ID"""
        return self.connection_info.get(websocket, {}).get("id", "unknown")

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

# 新的模块化 Agent 实例
planning_agent: Optional[PlanningAgent] = None
repair_agent: Optional[RepairAgent] = None
quality_agent: Optional[QualityAgent] = None
training_agent: Optional[TrainingAgent] = None
field_guidance_agent: Optional[FieldGuidanceAgent] = None

# 当前工具/模块选择（每个连接独立维护）
connection_tools: Dict[WebSocket, str] = {}  # websocket -> tool_name


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
    
    # 3. 初始化模块化 Agent
    global planning_agent, repair_agent, quality_agent, training_agent, field_guidance_agent
    
    print("🚀 正在初始化模块化 Agent...")
    try:
        planning_agent = PlanningAgent()
        repair_agent = RepairAgent()
        quality_agent = QualityAgent()
        training_agent = TrainingAgent()
        field_guidance_agent = FieldGuidanceAgent()
        print("✅ 模块化 Agent 初始化成功！")
        print(f"   📅 巡检计划生成 Agent")
        print(f"   🔧 维修方案咨询 Agent")
        print(f"   ✅ 工单质量检查 Agent")
        print(f"   📚 新员工培训 Agent")
        print(f"   📍 现场作业指导 Agent")
    except Exception as e:
        print(f"⚠️ 模块化 Agent 初始化失败: {e}")
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


@app.get("/tools/list")
async def get_tools_list():
    """获取可用的工具/模块列表"""
    tools = [
        {
            "id": "inspection",
            "name": "故障检测工单",
            "icon": "🔍",
            "description": "智能故障检测与分析",
            "ready": inspection_agent is not None
        },
        {
            "id": "planning",
            "name": "巡检计划",
            "icon": "📅",
            "description": "自动生成巡检计划",
            "ready": planning_agent is not None
        },
        {
            "id": "repair",
            "name": "维修方案",
            "icon": "🔧",
            "description": "维修方案咨询",
            "ready": repair_agent is not None
        },
        {
            "id": "quality",
            "name": "工单质检",
            "icon": "✅",
            "description": "工单质量检查",
            "ready": quality_agent is not None
        },
        {
            "id": "training",
            "name": "员工培训",
            "icon": "📚",
            "description": "新员工培训系统",
            "ready": training_agent is not None
        },
        {
            "id": "field_guidance",
            "name": "现场作业指导",
            "icon": "📍",
            "description": "现场作业技术指导",
            "ready": field_guidance_agent is not None
        }
    ]
    return {"tools": tools}


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


def _normalize_ws_action_payload(data: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    """解析并规范化 WebSocket 消息的 action / data，兼容多种客户端格式。"""
    payload = data.get("data", {})
    if not isinstance(payload, dict):
        payload = {}
    action = data.get("action", "")
    action = str(action).strip() if action is not None else ""
    # 兼容：仅把子动作放在 data 内，例如 { "type":"system", "data": { "action":"select_tool", "tool_id":"planning" } }
    if not action and payload.get("action") is not None:
        action = str(payload.get("action", "")).strip()
    return action, payload


async def _apply_tool_selection(websocket: WebSocket, payload: Dict[str, Any]) -> None:
    """切换当前连接使用的工具/模块（与 handle_system_message 中逻辑一致）。"""
    tool_id = payload.get("tool_id", "inspection")
    if not isinstance(tool_id, str):
        tool_id = str(tool_id)
    tool_id = tool_id.strip() or "inspection"
    connection_tools[websocket] = tool_id
    tool_info = _get_tool_info(tool_id)
    await manager.send_message(websocket, WSMessage(
        type="system",
        action="tool_selected",
        data={
            "tool_id": tool_id,
            "tool_info": tool_info,
            "message": f"已切换到 {tool_info.get('name', tool_id)} 模块"
        }
    ))
    print(f"🔄 连接 {manager.get_connection_id(websocket)} 切换到工具: {tool_id}")


async def handle_message(websocket: WebSocket, data: Dict[str, Any]):
    """处理接收到的消息"""
    msg_type = str(data.get("type", "") or "").strip()
    action, payload = _normalize_ws_action_payload(data)

    print(f"📨 收到消息: type={msg_type}, action={action}")

    if msg_type == "system":
        await handle_system_message(websocket, action, payload)
    elif msg_type == "chat":
        await handle_chat_message(websocket, action, payload)
    elif msg_type == "tool":
        await handle_tool_message(websocket, action, payload)
    elif msg_type == "module":
        # 新增：模块消息处理
        await handle_module_message(websocket, action, payload)
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
                "connections": len(manager.active_connections),
                "current_tool": connection_tools.get(websocket, "inspection")
            }
        ))
    elif action == "select_tool":
        await _apply_tool_selection(websocket, payload)
    else:
        await manager.send_message(websocket, WSMessage(
            type="system",
            action="error",
            data={"error": f"未知系统动作: {action}"}
        ))


def _get_tool_info(tool_id: str) -> Dict[str, Any]:
    """获取工具信息"""
    tools = {
        "inspection": {
            "id": "inspection",
            "name": "故障检测工单",
            "icon": "🔍",
            "agent_type": "inspection",
            "has_form": True
        },
        "planning": {
            "id": "planning",
            "name": "巡检计划",
            "icon": "📅",
            "agent_type": "planning",
            "has_form": True
        },
        "repair": {
            "id": "repair",
            "name": "维修方案",
            "icon": "🔧",
            "agent_type": "repair",
            "has_form": True
        },
        "quality": {
            "id": "quality",
            "name": "工单质检",
            "icon": "✅",
            "agent_type": "quality",
            "has_form": False,
            "supports_upload": True
        },
        "training": {
            "id": "training",
            "name": "员工培训",
            "icon": "📚",
            "agent_type": "training",
            "has_form": False,
            "has_quiz": True
        },
        "field_guidance": {
            "id": "field_guidance",
            "name": "现场作业指导",
            "icon": "📍",
            "agent_type": "field_guidance",
            "has_form": True,
            "supports_image": True,
            "supports_voice": True,
            "supports_location": True
        }
    }
    return tools.get(tool_id, tools["inspection"])


async def handle_chat_message(websocket: WebSocket, action: str, payload: Dict):
    """处理聊天消息 - 非阻塞模式，支持并发对话和工具路由"""
    if action == "send":
        message = payload.get("message", "")
        if not message:
            await manager.send_message(websocket, WSMessage(
                type="system",
                action="error",
                data={"error": "消息内容不能为空"}
            ))
            return

        # 获取当前选择的工具
        current_tool = connection_tools.get(websocket, "inspection")
        
        # 生成消息 ID 用于追踪
        message_id = str(uuid.uuid4())[:8]
        
        # 获取工具信息
        tool_info = _get_tool_info(current_tool)

        # 开始处理 - 附带工具信息
        await manager.send_message(websocket, WSMessage(
            type="chat",
            action="start",
            data={
                "message": f"{tool_info.get('icon', '🤖')} 开始处理消息...",
                "message_id": message_id,
                "tool_id": current_tool,
                "agent_header": f"{tool_info.get('icon', '🤖')} 【{tool_info.get('name', '智能体')}】"
            }
        ))

        # 获取会话历史
        session_history = manager.get_session_history(websocket)
        if session_history:
            session_history.add_user_message(message)

        # 根据工具类型路由到不同的 Agent
        print(f"🚀 [主循环] 创建后台任务 [{message_id}] 工具={current_tool}: {message[:30]}...")
        
        if current_tool == "inspection":
            # 原有的故障检测 Agent
            if inspection_agent is None:
                await manager.send_message(websocket, WSMessage(
                    type="system",
                    action="error",
                    data={"error": "故障检测智能体未初始化"}
                ))
                return
            asyncio.create_task(_process_chat_in_background(
                websocket, message, message_id, session_history
            ))
        else:
            # 新的模块化 Agent
            asyncio.create_task(_process_module_chat_in_background(
                websocket, message, message_id, session_history, current_tool
            ))
        
        # 立即返回，允许接收下一条消息
        print(f"✅ [主循环] 已返回，可接收下一条消息")
        return

    elif action == "clear_history":
        # 清空会话历史
        session_history = manager.get_session_history(websocket)
        if session_history:
            session_history.clear()
        await manager.send_message(websocket, WSMessage(
            type="system",
            action="history_cleared",
            data={"message": "会话历史已清空"}
        ))
    else:
        await manager.send_message(websocket, WSMessage(
            type="system",
            action="error",
            data={"error": f"未知聊天动作: {action}"}
        ))


# 全局线程池执行器 - 用于并发处理多个聊天请求
_chat_executor = concurrent.futures.ThreadPoolExecutor(max_workers=10, thread_name_prefix="chat_worker")


def _sync_send_callback_wrapper(websocket: WebSocket, message_id: str, main_loop: asyncio.AbstractEventLoop):
    """创建一个同步可调用的回调包装器，用于在工作线程中调度消息发送到主事件循环"""
    ai_response_content = []
    
    async def async_send(msg_type: str, action: str, data: dict):
        # 收集 AI 消息内容
        if msg_type == "chat" and action == "message" and data.get("type") == "ai":
            content = data.get("content", "")
            if content:
                ai_response_content.append(content)
        
        # RAG 检索结果日志（用于调试）
        if action == "rag_retrieval":
            doc_count = len(data.get("documents", []))
            print(f"📤 [WebSocket] 发送 RAG 检索结果到前端: {doc_count} 个文档")
        
        # 附加 message_id
        data_with_id = {**data, "message_id": message_id}
        await manager.send_message(websocket, WSMessage(
            type=msg_type,
            action=action,
            data=data_with_id
        ))
    
    def sync_send(msg_type: str, action: str, data: dict):
        """同步调用，将异步发送调度到主事件循环"""
        if main_loop and main_loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                async_send(msg_type, action, data),
                main_loop
            )
            try:
                future.result(timeout=30)
            except Exception as e:
                print(f"⚠️ 发送消息失败: {e}")
    
    return sync_send, ai_response_content


def _run_agent_in_thread(
    message: str,
    history_messages: List,
    sync_callback,
    message_id: str
):
    """在独立线程中运行智能体（真正的并发）"""
    import asyncio
    import threading
    
    print(f"🧵 [线程 {threading.current_thread().name}] 开始处理消息 [{message_id}]")
    
    # 为这个线程创建新的事件循环
    thread_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(thread_loop)
    
    try:
        # 创建独立的 InspectionAgent 实例（避免共享状态）
        print(f"🧵 [线程 {message_id}] 创建 InspectionAgent 实例...")
        thread_agent = InspectionAgent()
        print(f"🧵 [线程 {message_id}] InspectionAgent 创建完成")
        
        # 创建异步回调包装器
        async def async_callback(msg_type: str, action: str, data: dict):
            sync_callback(msg_type, action, data)
        
        # 运行处理
        thread_loop.run_until_complete(
            thread_agent.process_message_with_history(message, history_messages, async_callback)
        )
        return True
    except Exception as e:
        print(f"❌ 线程处理失败 [{message_id}]: {e}")
        import traceback
        traceback.print_exc()
        sync_callback("chat", "error", {"error": str(e)})
        return False
    finally:
        thread_loop.close()


async def _process_chat_in_background(
    websocket: WebSocket, 
    message: str, 
    message_id: str,
    session_history: Optional[SessionHistory]
):
    """后台处理聊天消息 - 使用线程池实现真正的并发"""
    print(f"🔧 [后台任务 {message_id}] 开始执行")
    main_loop = asyncio.get_running_loop()
    
    try:
        # 创建同步回调包装器
        sync_callback, ai_response_content = _sync_send_callback_wrapper(websocket, message_id, main_loop)
        
        # 获取历史消息
        history_messages = session_history.get_langchain_messages() if session_history else []
        
        print(f"🔧 [后台任务 {message_id}] 提交到线程池...")
        # 在线程池中运行智能体（不阻塞主事件循环）
        success = await main_loop.run_in_executor(
            _chat_executor,
            partial(_run_agent_in_thread, message, history_messages, sync_callback, message_id)
        )
        print(f"🔧 [后台任务 {message_id}] 线程执行完成, success={success}")

        # 保存 AI 回复到历史
        if session_history and ai_response_content:
            full_response = "\n".join(ai_response_content)
            session_history.add_ai_message(full_response)

        # 发送完成消息
        await manager.send_message(websocket, WSMessage(
            type="chat",
            action="complete",
            data={"message": "处理完成", "message_id": message_id}
        ))

    except Exception as e:
        print(f"❌ 后台处理消息失败 [{message_id}]: {e}")
        import traceback
        traceback.print_exc()
        await manager.send_message(websocket, WSMessage(
            type="chat",
            action="error",
            data={"error": str(e), "message_id": message_id}
        ))


async def _process_module_chat_in_background(
    websocket: WebSocket,
    message: str,
    message_id: str,
    session_history: Optional[SessionHistory],
    tool_id: str
):
    """后台处理模块化 Agent 聊天消息"""
    print(f"🔧 [模块后台任务 {message_id}] 工具={tool_id} 开始执行")
    main_loop = asyncio.get_running_loop()
    
    try:
        # 获取连接 ID 和消息队列
        connection_id = manager.get_connection_id(websocket)
        msg_queue = await message_queue_manager.get_or_create_queue(connection_id)
        
        # 创建异步回调
        async def ws_callback(msg_type: str, action: str, data: dict):
            data_with_id = {**data, "message_id": message_id, "tool_id": tool_id}
            await manager.send_message(websocket, WSMessage(
                type=msg_type,
                action=action,
                data=data_with_id
            ))
        
        ai_response = ""
        
        # 根据工具类型选择 Agent
        if tool_id == "planning":
            if planning_agent:
                ai_response = await planning_agent.process_message(
                    message, msg_queue, ws_callback
                )
        elif tool_id == "repair":
            if repair_agent:
                ai_response = await repair_agent.process_message(
                    message, msg_queue, ws_callback
                )
        elif tool_id == "quality":
            if quality_agent:
                ai_response = await quality_agent.process_message(
                    message, msg_queue, ws_callback
                )
        elif tool_id == "training":
            if training_agent:
                ai_response = await training_agent.process_message(
                    message, msg_queue, ws_callback
                )
        elif tool_id == "field_guidance":
            if field_guidance_agent:
                ai_response = await field_guidance_agent.process_message(
                    message, msg_queue, ws_callback
                )
        else:
            ai_response = f"未知的工具类型: {tool_id}"
        
        # 保存 AI 回复到会话历史
        if session_history and ai_response:
            session_history.add_ai_message(ai_response)
        
        # 发送完成消息
        await manager.send_message(websocket, WSMessage(
            type="chat",
            action="complete",
            data={"message": "处理完成", "message_id": message_id, "tool_id": tool_id}
        ))
        
    except Exception as e:
        print(f"❌ 模块后台处理消息失败 [{message_id}]: {e}")
        import traceback
        traceback.print_exc()
        await manager.send_message(websocket, WSMessage(
            type="chat",
            action="error",
            data={"error": str(e), "message_id": message_id, "tool_id": tool_id}
        ))


async def handle_module_message(websocket: WebSocket, action: str, payload: Dict):
    """处理模块特定消息"""
    # 兼容旧前端误将 kind 当作 action 发送（如 action=quality）
    if action == "quality":
        action = "upload_content"
        payload = {**payload, "tool_id": payload.get("tool_id") or "quality"}
        if not payload.get("content") and isinstance(payload.get("form_data"), dict):
            payload = {**payload, "content": payload["form_data"].get("content", "")}

    tool_id = payload.get("tool_id", "")
    message_id = str(uuid.uuid4())[:8]
    
    print(f"📦 [模块消息] action={action}, tool_id={tool_id}")
    
    # 获取连接 ID 和消息队列
    connection_id = manager.get_connection_id(websocket)
    msg_queue = await message_queue_manager.get_or_create_queue(connection_id)
    
    # 创建异步回调
    async def ws_callback(msg_type: str, action: str, data: dict):
        data_with_id = {**data, "message_id": message_id, "tool_id": tool_id}
        await manager.send_message(websocket, WSMessage(
            type=msg_type,
            action=action,
            data=data_with_id
        ))
    
    try:
        if action == "form_submit":
            # 处理表单提交
            form_data = payload.get("form_data", {})
            
            if tool_id == "planning":
                if planning_agent:
                    await ws_callback("system", "agent_start", {
                        "message": "📅 正在生成巡检计划..."
                    })
                    result = await planning_agent.generate_plan(form_data, msg_queue, ws_callback)
                    
            elif tool_id == "repair":
                if repair_agent:
                    await ws_callback("system", "agent_start", {
                        "message": "🔧 正在生成维修方案..."
                    })
                    result = await repair_agent.consult_repair(form_data, msg_queue, ws_callback)
            
            elif tool_id == "field_guidance":
                if field_guidance_agent:
                    await ws_callback("system", "agent_start", {
                        "message": "📍 正在分析现场问题..."
                    })
                    result = await field_guidance_agent.provide_guidance(form_data, msg_queue, ws_callback)
            
            else:
                await ws_callback("system", "error", {
                    "error": f"不支持的表单提交: {tool_id}"
                })
        
        elif action == "upload_content":
            # 处理内容上传（用于工单质检）
            content = payload.get("content", "")
            
            if tool_id == "quality" and quality_agent:
                await ws_callback("system", "agent_start", {
                    "message": "✅ 正在审核工单..."
                })
                result = await quality_agent.check_work_order(content, msg_queue, ws_callback)
                
                # 发送审核结果
                await ws_callback("tool", "quality_check_result", {
                    "passed": result.get("passed", False),
                    "report": result.get("report", ""),
                    "issues": result.get("issues", [])
                })
        
        elif action == "generate_quiz":
            # 生成培训试题
            topic = payload.get("topic", "")
            
            if tool_id == "training" and training_agent:
                await ws_callback("system", "agent_start", {
                    "message": "📚 正在生成培训试题..."
                })
                quiz = await training_agent.generate_quiz(topic, msg_queue, ws_callback)
                
                # 发送试题数据
                await ws_callback("tool", "quiz_generated", {
                    "quiz": quiz
                })
        
        elif action == "submit_answers":
            # 提交试题答案
            answers = payload.get("answers", {})
            
            if tool_id == "training" and training_agent:
                await ws_callback("system", "agent_start", {
                    "message": "📝 正在批改作业..."
                })
                grade = await training_agent.grade_answers(answers, msg_queue, ws_callback)
                
                # 发送批改结果
                await ws_callback("tool", "grade_result", {
                    "grade": grade
                })
        
        elif action == "get_courseware":
            # 获取培训课件
            if tool_id == "training" and training_agent:
                await ws_callback("system", "agent_start", {
                    "message": "📖 正在生成培训课件..."
                })
                courseware = await training_agent.generate_courseware(msg_queue, ws_callback)
                
                # 发送课件
                await ws_callback("tool", "courseware_generated", {
                    "courseware": courseware
                })
        
        else:
            await ws_callback("system", "error", {
                "error": f"未知的模块动作: {action}"
            })
            
    except Exception as e:
        print(f"❌ 模块消息处理失败: {e}")
        import traceback
        traceback.print_exc()
        await ws_callback("system", "error", {
            "error": str(e)
        })


def _create_thread_safe_callback(websocket: WebSocket, task: AnalysisTask, main_loop: asyncio.AbstractEventLoop):
    """创建线程安全的回调函数，用于在工作线程中发送消息到主事件循环"""
    
    def sync_callback(msg_type: str, action: str, data: dict):
        """同步回调 - 在工作线程中调用"""
        print(f"📤 [回调 {task.task_id}] type={msg_type}, action={action}, data_keys={list(data.keys())}")
        
        # 附加 task_id 到所有消息
        data_with_task = {**data, "task_id": task.task_id}
        
        # 记录分析步骤
        if action in ("thinking_step", "node_start", "node_complete"):
            task.add_step({"action": action, **data})
        
        # 记录最终报告 - 处理多种字段名
        # fault_analysis_core_vector 使用 report_markdown
        # 其他地方可能使用 final_report
        if action == "final_report":
            final_report = data.get("report_markdown") or data.get("final_report", "")
            thinking_processes = data.get("thinking_processes", [])
            
            print(f"📊 [回调 {task.task_id}] 收到最终报告, 长度={len(final_report)}")
            
            if final_report:
                task.complete(final_report, thinking_processes)
                
                # 标准化输出字段名，确保前端能正确读取
                data_with_task["final_report"] = final_report
                data_with_task["report_markdown"] = final_report  # 保留兼容
                
                # 获取会话历史并添加报告
                session_history = manager.get_session_history(websocket)
                if session_history:
                    task_summary = task.get_report_summary()
                    session_history.add_analysis_report(task.task_id, task_summary)
        
        if action == "analysis_complete":
            # analysis_complete 可能在 final_report 之后发送
            # 如果任务还未完成，尝试从 data 中获取报告
            if task.status != "completed":
                final_report = data.get("report_markdown") or data.get("final_report", "")
                if final_report:
                    task.complete(final_report, data.get("thinking_processes", []))
                    data_with_task["final_report"] = final_report
        
        # 记录错误
        if action == "analysis_error" or action == "error":
            task.fail(data.get("error", "未知错误"))
        
        # 调度消息发送到主事件循环
        if main_loop and main_loop.is_running():
            async def send_msg():
                await manager.send_message(websocket, WSMessage(type=msg_type, action=action, data=data_with_task))
            
            future = asyncio.run_coroutine_threadsafe(send_msg(), main_loop)
            try:
                future.result(timeout=30)
            except Exception as e:
                print(f"⚠️ [分析回调] 发送消息失败: {e}")
        else:
            print(f"⚠️ [分析回调] 主事件循环未运行，无法发送消息")
    
    return sync_callback


def _run_analysis_in_thread(
    task: AnalysisTask,
    rag_mode: str,
    input_data: Dict[str, Any],
    sync_callback
):
    """在独立线程中执行分析（真正的并发）"""
    import threading
    
    print(f"🧵 [线程 {threading.current_thread().name}] 开始分析任务 [{task.task_id}]")
    
    detect_time = input_data["detect_time"]
    part_name = input_data["part_name"]
    part_position = input_data["part_position"]
    defect_type = input_data["defect_type"]
    detect_confidence = input_data["detect_confidence"]
    
    # 为这个线程创建新的事件循环
    thread_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(thread_loop)
    
    try:
        # 创建异步回调包装器
        async def async_callback(msg_type: str, action: str, data: dict):
            sync_callback(msg_type, action, data)
        
        # 发送开始消息
        sync_callback("chat", "start", {"message": f"正在分析故障工单信息（{rag_mode} 模式）..."})
        
        if rag_mode == "vector":
            from fault_analysis_core_vector import initialize, run_fault_analysis_async
            if not initialize():
                sync_callback("tool", "analysis_error", {
                    "error": "故障分析模块初始化失败", 
                    "message": "请检查向量数据库与 LLM 配置"
                })
                return False
            
            # 在线程事件循环中运行异步分析
            thread_loop.run_until_complete(run_fault_analysis_async(
                detect_time=detect_time,
                part_name=part_name,
                part_position=part_position,
                defect_type=defect_type,
                detect_confidence=detect_confidence,
                ws_callback=async_callback,
            ))
        else:
            # graph 模式 - 创建独立的 InspectionAgent
            thread_agent = InspectionAgent()
            inspection_input = InspectionInput(
                detect_time=detect_time,
                part_name=part_name,
                part_position=part_position,
                defect_type=defect_type,
                detect_confidence=detect_confidence,
            )
            thread_loop.run_until_complete(
                thread_agent.run_fault_analysis(inspection_input, async_callback)
            )
        
        # 发送完成消息
        sync_callback("chat", "complete", {"message": "故障分析完成"})
        print(f"✅ [线程 {task.task_id}] 分析完成")
        return True
        
    except Exception as e:
        print(f"❌ [线程 {task.task_id}] 分析失败: {e}")
        import traceback
        traceback.print_exc()
        task.fail(str(e))
        sync_callback("chat", "error", {"error": str(e)})
        return False
    finally:
        thread_loop.close()


async def _run_analysis_in_background(
    websocket: WebSocket,
    task: AnalysisTask,
    rag_mode: str,
    input_data: Dict[str, Any]
):
    """后台执行分析任务 - 使用线程池实现真正的非阻塞"""
    print(f"🔧 [后台分析 {task.task_id}] 提交到线程池")
    main_loop = asyncio.get_running_loop()
    
    # 创建线程安全的回调
    sync_callback = _create_thread_safe_callback(websocket, task, main_loop)
    
    # 在线程池中运行分析（不阻塞主事件循环）
    await main_loop.run_in_executor(
        _chat_executor,
        partial(_run_analysis_in_thread, task, rag_mode, input_data, sync_callback)
    )
    
    print(f"🔧 [后台分析 {task.task_id}] 执行完成")


async def handle_tool_message(websocket: WebSocket, action: str, payload: Dict):
    """处理工具消息 - 非阻塞模式"""
    # 兼容：部分前端/代理误将 select_tool 发到 type=tool
    if action == "select_tool":
        await _apply_tool_selection(websocket, payload)
        return

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

        # 获取连接 ID
        connection_id = manager.get_connection_id(websocket)
        
        # 创建分析任务
        input_data = {
            "detect_time": detect_time,
            "part_name": part_name,
            "part_position": part_position,
            "defect_type": defect_type,
            "detect_confidence": detect_confidence,
        }
        task = analysis_task_manager.create_task(connection_id, input_data)
        task.start()

        # 通知前端分析任务已创建（带 task_id）- 立即响应
        await manager.send_message(websocket, WSMessage(
            type="tool",
            action="task_created",
            data={
                "task_id": task.task_id,
                "input_data": input_data,
                "status": "running",
                "message": f"分析任务 {task.task_id} 已创建"
            }
        ))

        # 创建后台任务执行分析（非阻塞）
        print(f"🚀 [主循环] 创建分析任务 [{task.task_id}]: {part_name} - {defect_type}")
        asyncio.create_task(_run_analysis_in_background(
            websocket, task, rag_mode, input_data
        ))
        
        # 立即返回，允许接收下一条消息
        print(f"✅ [主循环] 分析任务已提交后台，可接收下一条消息")
        return
    
    elif action == "get_task":
        # 获取任务详情
        task_id = payload.get("task_id", "")
        task = analysis_task_manager.get_task(task_id)
        if task:
            await manager.send_message(websocket, WSMessage(
                type="tool",
                action="task_detail",
                data=task.to_dict()
            ))
        else:
            await manager.send_message(websocket, WSMessage(
                type="system",
                action="error",
                data={"error": f"任务不存在: {task_id}"}
            ))
    
    elif action == "list_tasks":
        # 列出当前连接的所有任务
        connection_id = manager.get_connection_id(websocket)
        tasks = analysis_task_manager.get_tasks_by_connection(connection_id)
        await manager.send_message(websocket, WSMessage(
            type="tool",
            action="task_list",
            data={
                "tasks": [t.to_dict() for t in tasks],
                "count": len(tasks)
            }
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

