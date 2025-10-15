#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChatbotNode - LangGraph聊天机器人节点
"""

import os
from typing import Annotated
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages

from fault_graph import search_fault
from yolo_agent_tool import yolo_detect_tool
from langchain_core.tools import tool

@tool
def city_weather(city: str) -> str:
    """
    一个查询天气的工具

    Args:
        city: 城市名

    Returns:
        检测结果的JSON字符串
    """

    return f"""{city} 现在正在发生超新星爆发"""


class State(TypedDict):
    """对话状态，使用add_messages自动处理消息列表更新"""
    messages: Annotated[list, add_messages]


class RouterNode:
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
            raise ValueError("请设置OPENAI_API_KEY环境变量：chatbot_node.py")
        
        # 创建LLM实例
        self.llm = self._create_llm()
        self.llm_with_tools = self.llm.bind_tools([search_fault])

        # 路由决策的系统提示词
        self.system_prompt = """你是一个决策专家。你的任务是决定当前任务的走向。
目前你可以决定的走向有：
1、如果你觉得当前的任务需要过去的经验帮助(默认每轮提问都先获得经验，然后再执行其他逻辑)，或者当前用户的行为可以总结经验以帮助未来的任务 -> 返回：call_memory
2、如果你觉得当前的任务需要调用自身工具（fault识别） -> 发起工具调用


请根据用户的消息内容，分析并返回对应的路由决策。只返回路由名称，不要返回其他内容。"""
    
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
        # messages = [{"role": "system", "content": self.system_prompt}]
        messages = []
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
            "routes": [ "call_tool", "call_summary"],
            "system_prompt": self.system_prompt
        }


# 便捷函数：创建默认的聊天机器人节点
def create_router_node(**kwargs) -> RouterNode:
    """
    创建默认的聊天机器人节点
    
    Args:
        **kwargs: 传递给ChatbotNode的参数
        
    Returns:
        ChatbotNode实例
    """
    return RouterNode(**kwargs)
