import os
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()


# 假设您已设置 OpenAI API Key 和 Base URL
llm = ChatOpenAI(
    base_url=os.getenv('OPENAI_BASE_URL'), # 确保在 .env 中设置 OPENAI_BASE_URL
    api_key="123", # 推荐从环境变量获取 API Key
    temperature=0.7,
    max_tokens=10000
)

class common_llm:

    def __init__(self, prompt: str, additional: str = ""):
        super().__init__()
        self.prompt = prompt
        self.additional = additional


    def __call__(self, state):
        """调用 LLM 并返回其响应作为状态更新。"""

        # 获取完整的对话历史
        messages = state["messages"]

        # --- 关键修改：将 SystemMessage 插入到历史消息列表的最前面 ---
        # 这样 LLM 在推理时，System Message 总是作为第一个指令。
        full_input = messages + [SystemMessage(content=self.prompt)]

        # 调用 LLM
        response = llm.invoke(full_input)

        # 返回 LLM 的响应，LangGraph 会自动将其追加到 messages 列表中
        return {"messages": [response]}
