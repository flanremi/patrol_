#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from typing import Annotated, List
import uuid
from datetime import datetime

from langgraph.constants import START, END
from langgraph.graph import StateGraph
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages
from yolo_agent_tool import yolo_detect_tool
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from DB_helper import EmbeddingDBHelper

collection_name = "memory_collection"

class State(TypedDict):
    """对话状态，使用add_messages自动处理消息列表更新"""
    messages: Annotated[list, add_messages]


# 初始化数据库助手
db_helper = EmbeddingDBHelper(embedding_path="memory_embedding")


@tool
def search_memory(query: str, top_k: int = 5) -> str:
    """
    从embedding数据库中搜索语义相近的记忆内容
    
    Args:
        query: 查询的记忆字符串
        top_k: 返回最相似的前k条记录，默认为5
        
    Returns:
        搜索到的相似内容，以JSON格式返回
    """
    try:
        # 使用默认的记忆集合名称
        
        
        # 检查集合是否存在
        collections = db_helper.list_collections()
        if collection_name not in collections:
            return f"记忆数据库中没有找到集合 '{collection_name}'，请先存储一些记忆内容。"
        
        # 搜索相似内容
        similar_contexts = db_helper.search_similar_contexts(collection_name, query, top_k)
        
        if not similar_contexts:
            return f"没有找到与 '{query}' 相关的记忆内容。"
        

        return f"你可以参考的过往相关记忆：\n" + "\n".join([str(pos + 1) + ": " + memory for pos, memory in enumerate(similar_contexts)])
        
    except Exception as e:
        return f"没有可用的记忆"


@tool
def store_memory(content: str) -> str:
    """
    将内容存储到embedding数据库中作为记忆
    
    Args:
        content: 要存储的记忆字符串
        
    Returns:
        存储结果的描述
    """
    try:
        # 使用默认的记忆集合名称
        collection_name = "memory_collection"
        
        # 检查集合是否存在，如果不存在则创建
        collections = db_helper.list_collections()
        if collection_name not in collections:
            # 创建新的集合
            collection = db_helper.chroma_client.create_collection(
                name=collection_name,
                embedding_function=db_helper.embedding_function
            )
            print(f"创建新的记忆集合: {collection_name}")
        else:
            # 获取现有集合
            collection = db_helper.chroma_client.get_collection(
                name=collection_name,
                embedding_function=db_helper.embedding_function
            )
        
        # 生成唯一的ID
        memory_id = f"memory_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
        
        # 添加内容到集合
        collection.add(
            documents=[content],
            ids=[memory_id],
            metadatas=[{
                "timestamp": datetime.now().isoformat(),
                "type": "user_memory"
            }]
        )
        
        return f"成功存储记忆内容，ID: {memory_id}。内容预览: {content[:50]}..."
        
    except Exception as e:
        return f"存储记忆时发生错误: {str(e)}"


class MemoryNode:
    """聊天机器人节点类"""

    def __init__(self, base_url: str = None, api_key: str = None, model: str = "gpt-3.5-turbo"):
        """
        初始化聊天机器人节点

        Args:
            base_url: OpenAI API基础URL
            api_key: OpenAI API密钥
            model: 使用的模型名称
        """
        self.base_url = os.getenv("OPENAI_BASE_URL", "")
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

        if not self.api_key:
            raise ValueError("请设置OPENAI_API_KEY环境变量: memory_graph.py")

        # 创建LLM实例
        self.llm = self._create_llm()
        self.llm_with_tools = self.llm.bind_tools([search_memory, store_memory])

        # 路由决策的系统提示词
        self.system_prompt = """你是用户交互专家，负责处理与用户交互的记忆。
        你的职责是阅读用户的过往操作，总结你觉得有必要的内容，然后调用你觉得合适的工具来完成任务。
        你的工作是：
        1、总结用户的问题（注意，你可能需要总结用户的完整对话内容，而不仅仅是问题或者部分参数,例如分析这张图片：xxxxx，
        你需要总结“分析这张图片：xxxxx”而不仅仅是“xxxxx”），
        读取3-10条相关的策略，并将任务下发给后面的agent完成（默认）；
        2、保存用户希望保存的内容。
        """



    def _create_llm(self) -> ChatOpenAI:
        """创建带有自定义baseurl的OpenAI客户端"""
        return ChatOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            model=self.model,
            temperature=0.7,
            max_tokens=1000
        )

    def __call__(self, state: State) -> dict:
        """
        路由节点执行函数 - 根据用户消息决定路由方向

        Args:
            state: 对话状态

        Returns:
            包含路由决策的状态字典
        """
        # 构建包含系统提示词的消息列表
        messages = [{"role": "system", "content": self.system_prompt}]
        # messages = []
        messages.extend(state["messages"])

        # 调用LLM获取路由决策
        response = self.llm_with_tools.invoke(messages)

        return {"messages": [response]}

    def get_info(self) -> dict:
        """获取节点信息"""
        return {
            "name": "RouterNode",
            "description": "路由节点，根据用户消息决定任务走向",
            "base_url": self.base_url,
            "model": self.model,
            "routes": ["call_memory", "call_tool", "call_summary"],
            "system_prompt": self.system_prompt
        }


# 创建全局节点实例，供外部使用
memory_node_instance = None
memory_tool_node_instance = None

def create_memory_node():
    """创建记忆处理节点"""
    global memory_node_instance
    if memory_node_instance is None:
        memory_node_instance = MemoryNode()
    return memory_node_instance

def create_memory_tool_node():
    """创建记忆工具节点"""
    global memory_tool_node_instance
    if memory_tool_node_instance is None:
        memory_tool_node_instance = ToolNode([search_memory, store_memory])
    return memory_tool_node_instance

def memory_graph_node(state: State) -> dict:
    """作为独立节点的记忆处理函数"""
    memory_node = create_memory_node()
    return memory_node(state)

def memory_tool_graph_node(state: State) -> dict:
    """作为独立节点的记忆工具函数"""
    tool_node = create_memory_tool_node()
    return tool_node(state)

# 保持原有函数用于兼容
def create_memory_subgraph(**kwargs):
    """创建记忆子图的函数（兼容性保留）"""
    subgraph = StateGraph(State)
    memory_node = MemoryNode()
    tool_node = ToolNode([search_memory, store_memory])
    subgraph.add_node("memory", memory_node)
    subgraph.add_node("tool", tool_node)
    subgraph.add_edge(START, "memory")
    subgraph.add_edge("memory", "tool")
    subgraph.add_edge("tool", END)
    return subgraph.compile(**kwargs)

def create_graph(**kwargs):
    return create_memory_subgraph(**kwargs)