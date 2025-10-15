#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SummaryNode - LangGraph总结节点
"""

import os
from typing import Annotated
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages


class State(TypedDict):
    """对话状态，使用add_messages自动处理消息列表更新"""
    messages: Annotated[list, add_messages]


class SummaryNode:
    """总结节点类"""
    
    def __init__(self, base_url: str = None, api_key: str = None, model: str = "gpt-3.5-turbo"):
        """
        初始化总结节点
        
        Args:
            base_url: OpenAI API基础URL
            api_key: OpenAI API密钥
            model: 使用的模型名称
        """
        self.base_url = os.getenv("OPENAI_BASE_URL", "")
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        
        if not self.api_key:
            raise ValueError("请设置OPENAI_API_KEY环境变量：summary_node.py")
        
        # 创建LLM实例
        self.llm = self._create_llm()
    
    def _create_llm(self) -> ChatOpenAI:
        """创建带有自定义baseurl的OpenAI客户端"""
        return ChatOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            model=self.model,
            temperature=0.7,
            max_tokens=1000
        )
    
    def _analyze_conversation(self, messages: list) -> tuple[bool, bool]:
        """
        分析对话内容，确定总结策略
        
        Args:
            messages: 消息列表
            
        Returns:
            (has_tool_calls, has_image_detection)
        """
        has_tool_calls = False
        has_image_detection = False
        
        # 检查是否包含工具调用和图像检测
        for message in messages:
            if hasattr(message, 'tool_calls') and message.tool_calls:
                has_tool_calls = True
                for tool_call in message.tool_calls:
                    if tool_call.get('name') == 'yolo_detect_tool':
                        has_image_detection = True
                        break
        
        return has_tool_calls, has_image_detection
    
    def _get_context_prompt(self, has_tool_calls: bool, has_image_detection: bool) -> str:
        """
        根据对话内容动态构建上下文提示
        
        Args:
            has_tool_calls: 是否包含工具调用
            has_image_detection: 是否包含图像检测
            
        Returns:
            上下文提示字符串
        """
        if has_image_detection:
            return """
你是一个专业的图像分析总结助手。请根据以下对话内容，特别关注图像检测结果，提供详细的总结。

总结要求：
1. 重点总结图像检测的结果和发现
2. 说明检测到的对象类型、数量和置信度
3. 分析检测结果的意义和可能的应用
4. 提供基于检测结果的建议或见解
5. 保持专业、准确的语调
6. 使用中文回复

请基于以下对话内容进行总结：
"""
        elif has_tool_calls:
            return """
你是一个专业的工具使用总结助手。请根据以下对话内容，总结工具的使用情况和结果。

总结要求：
1. 说明使用了哪些工具以及使用目的
2. 总结工具执行的结果和输出
3. 分析工具使用是否达到了预期目标
4. 提供基于工具结果的建议
5. 保持客观、准确的语调
6. 使用中文回复

请基于以下对话内容进行总结：
"""
        else:
            return """
你是一个专业的对话总结助手。请根据以下对话内容，提供简洁而全面的总结。

总结要求：
1. 提取对话中的关键信息和要点
2. 识别用户的主要需求和问题
3. 总结AI的回复和建议
4. 保持客观、准确的语调
5. 使用中文回复

请基于以下对话内容进行总结：
"""
    
    def _format_conversation_history(self, messages: list) -> list[str]:
        """
        格式化对话历史
        
        Args:
            messages: 消息列表
            
        Returns:
            格式化后的对话历史列表
        """
        conversation_history = []
        
        for message in messages:
            if hasattr(message, 'content'):
                role = "用户" if message.type == "human" else "AI助手"
                content = message.content
                # 如果是工具调用消息，添加特殊标记
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    tool_names = [tc.get('name', 'unknown') for tc in message.tool_calls]
                    content += f" [调用了工具: {tool_names}]"
                conversation_history.append(f"{role}: {content}")
            elif isinstance(message, dict):
                role = "用户" if message.get("role") == "user" else "AI助手"
                content = message.get('content', '')
                conversation_history.append(f"{role}: {content}")
        
        return conversation_history
    
    def __call__(self, state: State) -> dict:
        """
        总结节点执行函数 - 提供自定义上下文进行智能总结
        
        Args:
            state: 对话状态
            
        Returns:
            包含总结消息的状态字典
        """
        messages = state["messages"]
        
        # 分析对话内容，确定总结策略
        has_tool_calls, has_image_detection = self._analyze_conversation(messages)
        
        # 根据对话内容动态构建上下文
        context_prompt = self._get_context_prompt(has_tool_calls, has_image_detection)
        
        # 获取格式化的对话历史
        conversation_history = self._format_conversation_history(messages)
        
        # 构建完整的提示
        full_prompt = context_prompt + "\n".join(conversation_history)
        
        # 创建总结专用的消息
        summary_messages = [{"role": "user", "content": full_prompt}]
        
        # 调用LLM进行总结
        summary_response = self.llm.invoke(summary_messages)
        
        return {"messages": [summary_response]}
    
    def get_info(self) -> dict:
        """获取节点信息"""
        return {
            "name": "SummaryNode",
            "description": "总结节点，根据对话内容提供智能总结",
            "base_url": self.base_url,
            "model": self.model,
            "has_tools": False,
            "features": ["智能上下文分析", "动态提示构建", "多种总结模式"]
        }


# 便捷函数：创建默认的总结节点
def create_summary_node(**kwargs) -> SummaryNode:
    """
    创建默认的总结节点
    
    Args:
        **kwargs: 传递给SummaryNode的参数
        
    Returns:
        SummaryNode实例
    """
    return SummaryNode(**kwargs)


# 测试函数
def test_summary_node():
    """测试总结节点"""
    print("🧪 测试SummaryNode")
    print("=" * 40)
    
    try:
        # 创建节点
        node = create_summary_node()
        print(f"✅ 节点创建成功")
        
        # 显示节点信息
        info = node.get_info()
        print(f"📋 节点信息:")
        for key, value in info.items():
            print(f"  - {key}: {value}")
        
        # 测试总结功能
        test_state = {
            "messages": [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好！有什么可以帮助您的吗？"}
            ]
        }
        
        print(f"\n🔄 测试总结功能...")
        result = node(test_state)
        print(f"✅ 总结测试完成，返回消息数: {len(result['messages'])}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")


if __name__ == "__main__":
    test_summary_node()
