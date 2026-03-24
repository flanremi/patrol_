#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一消息队列管理模块
独立于各个 Agent 的上下文消息队列管理
所有 Agent 共享同一个消息队列
"""
import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


class MessageRole(Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class AgentType(Enum):
    """Agent 类型"""
    INSPECTION = "inspection"       # 故障检测智能体
    PLANNING = "planning"           # 巡检计划自动生成
    REPAIR = "repair"               # 维修方案咨询
    QUALITY = "quality"             # 工单质量检查
    TRAINING = "training"           # 新员工培训
    FIELD_GUIDANCE = "field_guidance"  # 现场作业指导


@dataclass
class Message:
    """统一消息结构"""
    id: str
    role: MessageRole
    content: str
    agent_type: Optional[AgentType] = None
    tool_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "agent_type": self.agent_type.value if self.agent_type else None,
            "tool_name": self.tool_name,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }
    
    def to_langchain(self):
        """转换为 LangChain 消息格式"""
        if self.role == MessageRole.USER:
            return HumanMessage(content=self.content)
        elif self.role == MessageRole.ASSISTANT:
            return AIMessage(content=self.content)
        elif self.role == MessageRole.SYSTEM:
            return SystemMessage(content=self.content)
        return None


def generate_message_header(agent_type: AgentType, action: str = None) -> str:
    """生成优雅的消息头
    
    Args:
        agent_type: Agent 类型
        action: 可选的动作描述
    
    Returns:
        格式化的消息头字符串
    """
    icons = {
        AgentType.INSPECTION: "🔍",
        AgentType.PLANNING: "📅",
        AgentType.REPAIR: "🔧",
        AgentType.QUALITY: "✅",
        AgentType.TRAINING: "📚",
        AgentType.FIELD_GUIDANCE: "📍"
    }
    
    names = {
        AgentType.INSPECTION: "故障检测工单",
        AgentType.PLANNING: "巡检计划",
        AgentType.REPAIR: "维修方案",
        AgentType.QUALITY: "工单质检",
        AgentType.TRAINING: "员工培训",
        AgentType.FIELD_GUIDANCE: "现场作业指导"
    }
    
    icon = icons.get(agent_type, "🤖")
    name = names.get(agent_type, "智能体")
    
    if action:
        return f"{icon} 【{name}】{action}"
    return f"{icon} 【{name}】"


class MessageQueue:
    """统一消息队列 - 每个连接独立维护"""
    
    def __init__(self, connection_id: str):
        self.connection_id = connection_id
        self.messages: List[Message] = []
        self.current_agent: Optional[AgentType] = None
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self._lock = asyncio.Lock()
    
    async def add_message(
        self,
        role: MessageRole,
        content: str,
        agent_type: Optional[AgentType] = None,
        tool_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """添加消息到队列"""
        async with self._lock:
            msg = Message(
                id=str(uuid.uuid4())[:8],
                role=role,
                content=content,
                agent_type=agent_type or self.current_agent,
                tool_name=tool_name,
                metadata=metadata or {}
            )
            self.messages.append(msg)
            self.last_activity = datetime.now()
            
            print(f"📝 [队列 {self.connection_id}] 添加消息: role={role.value}, agent={agent_type}, 当前消息数: {len(self.messages)}")
            return msg
    
    def add_message_sync(
        self,
        role: MessageRole,
        content: str,
        agent_type: Optional[AgentType] = None,
        tool_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """同步添加消息（供非异步上下文使用）"""
        msg = Message(
            id=str(uuid.uuid4())[:8],
            role=role,
            content=content,
            agent_type=agent_type or self.current_agent,
            tool_name=tool_name,
            metadata=metadata or {}
        )
        self.messages.append(msg)
        self.last_activity = datetime.now()
        return msg
    
    def set_current_agent(self, agent_type: AgentType):
        """设置当前活跃的 Agent"""
        self.current_agent = agent_type
        print(f"🔄 [队列 {self.connection_id}] 切换 Agent: {agent_type.value}")
    
    def get_langchain_messages(self, agent_type: Optional[AgentType] = None) -> List:
        """获取 LangChain 格式的消息列表
        
        Args:
            agent_type: 可选，只获取特定 Agent 的消息
        
        Returns:
            LangChain 消息列表
        """
        lc_messages = []
        for msg in self.messages:
            if agent_type and msg.agent_type != agent_type:
                continue
            lc_msg = msg.to_langchain()
            if lc_msg:
                lc_messages.append(lc_msg)
        return lc_messages
    
    def get_all_messages(self) -> List[Dict[str, Any]]:
        """获取所有消息（字典格式）"""
        return [msg.to_dict() for msg in self.messages]
    
    def get_messages_by_agent(self, agent_type: AgentType) -> List[Message]:
        """获取特定 Agent 的消息"""
        return [msg for msg in self.messages if msg.agent_type == agent_type]
    
    def get_recent_messages(self, count: int = 10) -> List[Message]:
        """获取最近的消息"""
        return self.messages[-count:] if len(self.messages) > count else self.messages[:]
    
    def clear(self, agent_type: Optional[AgentType] = None):
        """清空消息
        
        Args:
            agent_type: 可选，只清空特定 Agent 的消息
        """
        if agent_type:
            self.messages = [msg for msg in self.messages if msg.agent_type != agent_type]
            print(f"🗑️ [队列 {self.connection_id}] 清空 {agent_type.value} 的消息")
        else:
            self.messages = []
            print(f"🗑️ [队列 {self.connection_id}] 清空所有消息")
    
    def get_context_summary(self, max_messages: int = 20) -> str:
        """获取上下文摘要（用于跨 Agent 交互）"""
        recent = self.get_recent_messages(max_messages)
        if not recent:
            return "暂无历史对话"
        
        summary_parts = []
        for msg in recent:
            agent_prefix = generate_message_header(msg.agent_type) if msg.agent_type else ""
            summary_parts.append(f"{agent_prefix} [{msg.role.value}]: {msg.content[:100]}...")
        
        return "\n".join(summary_parts)
    
    def __len__(self):
        return len(self.messages)


class MessageQueueManager:
    """消息队列管理器 - 全局单例"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.queues: Dict[str, MessageQueue] = {}
        self._lock = asyncio.Lock()
        self._initialized = True
        print("📮 消息队列管理器初始化完成")
    
    async def get_or_create_queue(self, connection_id: str) -> MessageQueue:
        """获取或创建消息队列"""
        async with self._lock:
            if connection_id not in self.queues:
                self.queues[connection_id] = MessageQueue(connection_id)
                print(f"📮 创建消息队列: {connection_id}")
            return self.queues[connection_id]
    
    def get_queue(self, connection_id: str) -> Optional[MessageQueue]:
        """获取消息队列（不创建）"""
        return self.queues.get(connection_id)
    
    async def remove_queue(self, connection_id: str):
        """移除消息队列"""
        async with self._lock:
            if connection_id in self.queues:
                queue = self.queues.pop(connection_id)
                print(f"📮 移除消息队列: {connection_id}，共 {len(queue)} 条消息")
    
    def get_active_connections(self) -> List[str]:
        """获取所有活跃连接"""
        return list(self.queues.keys())


# 全局消息队列管理器
message_queue_manager = MessageQueueManager()


# ===================== WebSocket 消息封装 =====================
class WSMessageBuilder:
    """WebSocket 消息构建器 - 带优雅消息头"""
    
    @staticmethod
    def build(
        msg_type: str,
        action: str,
        data: Dict[str, Any],
        agent_type: Optional[AgentType] = None
    ) -> Dict[str, Any]:
        """构建 WebSocket 消息
        
        Args:
            msg_type: 消息类型 (system, chat, tool)
            action: 动作
            data: 消息数据
            agent_type: Agent 类型
        
        Returns:
            格式化的消息字典
        """
        message = {
            "type": msg_type,
            "action": action,
            "data": {
                **data,
                "timestamp": datetime.now().isoformat(),
                "message_id": str(uuid.uuid4())[:8]
            }
        }
        
        if agent_type:
            message["data"]["agent_type"] = agent_type.value
            message["data"]["agent_header"] = generate_message_header(agent_type)
        
        return message
    
    @staticmethod
    def system_message(
        action: str,
        content: str,
        agent_type: Optional[AgentType] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """构建系统消息"""
        return WSMessageBuilder.build(
            "system",
            action,
            {"content": content, **kwargs},
            agent_type
        )
    
    @staticmethod
    def chat_message(
        content: str,
        agent_type: Optional[AgentType] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """构建聊天消息"""
        return WSMessageBuilder.build(
            "chat",
            "message",
            {"type": "ai", "content": content, **kwargs},
            agent_type
        )
    
    @staticmethod
    def tool_message(
        action: str,
        data: Dict[str, Any],
        agent_type: Optional[AgentType] = None
    ) -> Dict[str, Any]:
        """构建工具消息"""
        return WSMessageBuilder.build("tool", action, data, agent_type)


# ===================== 测试入口 =====================
if __name__ == "__main__":
    import asyncio
    
    async def test():
        # 创建消息队列
        queue = MessageQueue("test-connection")
        
        # 添加消息
        await queue.add_message(MessageRole.USER, "你好，我想进行故障检测")
        queue.set_current_agent(AgentType.INSPECTION)
        await queue.add_message(MessageRole.ASSISTANT, "好的，请提供故障信息")
        
        # 切换 Agent
        queue.set_current_agent(AgentType.PLANNING)
        await queue.add_message(MessageRole.USER, "生成下周的巡检计划")
        await queue.add_message(MessageRole.ASSISTANT, "已生成巡检计划")
        
        # 打印消息
        print("\n所有消息:")
        for msg in queue.get_all_messages():
            print(f"  {msg}")
        
        # 打印 LangChain 消息
        print("\nLangChain 消息:")
        for msg in queue.get_langchain_messages():
            print(f"  {msg}")
        
        # 测试消息头生成
        print("\n消息头测试:")
        for agent in AgentType:
            print(f"  {generate_message_header(agent, '处理中...')}")
    
    asyncio.run(test())
