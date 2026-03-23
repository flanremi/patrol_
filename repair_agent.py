#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
维修方案咨询 Agent
基于提示工程，让 LLM 根据缺陷信息推荐维修方案

输入：缺陷描述、位置、紧急程度
输出：推荐维修工法、所需物料清单、参考工时、安全注意事项
自动关联相关作业指导书和技术标准
"""
import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Awaitable

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from message_queue import (
    MessageQueue, MessageRole, AgentType, 
    generate_message_header, WSMessageBuilder
)

load_dotenv()


# ===================== LLM 初始化 =====================
base_url = os.getenv("OPENAI_BASE_URL")
api_key = os.getenv("OPENAI_API_KEY")
model_name = os.getenv("OPENAI_MODEL", "qwen-plus")

llm = ChatOpenAI(
    base_url=base_url,
    api_key=api_key,
    temperature=0.5,
    model=model_name
)


# ===================== 系统提示词 =====================
REPAIR_SYSTEM_PROMPT = """你是一位资深的轨道交通维修专家和工程师。你拥有丰富的设备维护和故障修复经验。

## 你的能力
1. **故障诊断**：根据缺陷描述分析可能的故障原因
2. **维修方案制定**：推荐最佳的维修工法和流程
3. **物料管理**：列出所需的工具、备件和耗材
4. **工时评估**：根据维修难度估算所需时间
5. **安全指导**：强调维修过程中的安全注意事项
6. **标准关联**：关联相关的作业指导书和技术标准

## 输入信息
用户会提供以下信息：
- **缺陷描述**：故障现象和问题描述
- **缺陷位置**：设备或区段位置
- **紧急程度**：紧急/一般/可延期
- **设备信息**：设备型号、使用年限等（可选）

## 输出格式要求
请以 Markdown 格式输出维修方案，必须包含以下部分：

### 🔍 故障分析
- 故障现象描述
- 可能的故障原因（列举2-3个）
- 故障等级评估

### 🛠️ 推荐维修工法
1. 维修方案A（首选）
   - 维修步骤
   - 适用场景
   - 优缺点

2. 维修方案B（备选）
   - 维修步骤
   - 适用场景

### 📦 所需物料清单
| 序号 | 物料名称 | 规格型号 | 数量 | 用途 |
|------|----------|----------|------|------|

### ⏱️ 参考工时
| 维修阶段 | 预计耗时 | 所需人员 |
|----------|----------|----------|
| 准备阶段 |          |          |
| 维修阶段 |          |          |
| 检验阶段 |          |          |
| **合计** |          |          |

### ⚠️ 安全注意事项
1. 作业前安全检查
2. 作业中注意事项
3. 作业后验收要点

### 📚 相关作业指导书
- 《XXX作业指导书》- 章节X.X
- 《XXX技术标准》- 相关条款

### 📋 质量验收标准
列出维修完成后的验收要点和标准

## 重要提醒
- 安全第一，所有维修建议必须符合安全规范
- 优先推荐经过验证的标准维修方法
- 物料清单要考虑备用量
- 工时估算要留有余量
"""


class RepairAgent:
    """维修方案咨询 Agent"""
    
    def __init__(self):
        self.agent_type = AgentType.REPAIR
        self.consultation_history: List[Dict[str, Any]] = []
        print(f"\n{'='*70}")
        print(f"{generate_message_header(self.agent_type)} 初始化完成")
        print(f"{'='*70}\n")
    
    async def consult_repair(
        self,
        input_data: Dict[str, Any],
        message_queue: Optional[MessageQueue],
        ws_callback: Optional[Callable[[str, str, dict], Awaitable[None]]] = None
    ) -> str:
        """提供维修方案咨询
        
        Args:
            input_data: 包含缺陷描述、位置、紧急程度的输入数据
            message_queue: 消息队列
            ws_callback: WebSocket 回调函数
        
        Returns:
            维修方案 (Markdown 格式)
        """
        header = generate_message_header(self.agent_type, "正在分析故障并生成维修方案...")
        
        if ws_callback:
            await ws_callback("system", "agent_start", {
                "agent_type": self.agent_type.value,
                "message": header
            })
        
        # 构建用户提示
        user_prompt = self._build_user_prompt(input_data)
        
        # 获取历史消息
        history_messages = []
        if message_queue:
            history_messages = message_queue.get_langchain_messages(self.agent_type)
            message_queue.set_current_agent(self.agent_type)
            message_queue.add_message_sync(MessageRole.USER, user_prompt, self.agent_type)
        
        messages = [
            SystemMessage(content=REPAIR_SYSTEM_PROMPT),
            *history_messages[-10:],  # 只保留最近10条历史
            HumanMessage(content=user_prompt)
        ]
        
        try:
            # 发送思考步骤
            if ws_callback:
                await ws_callback("tool", "thinking_step", {
                    "agent_type": self.agent_type.value,
                    "node": "diagnosis",
                    "title": "故障诊断",
                    "summary": f"正在分析：{input_data.get('defect_description', '未知缺陷')[:50]}..."
                })
            
            # 调用 LLM
            response = await llm.ainvoke(messages)
            repair_plan = response.content
            
            # 记录咨询历史
            self.consultation_history.append({
                "input": input_data,
                "output": repair_plan,
                "timestamp": datetime.now().isoformat()
            })
            
            # 记录到消息队列
            if message_queue:
                message_queue.add_message_sync(MessageRole.ASSISTANT, repair_plan, self.agent_type)
            
            if ws_callback:
                await ws_callback("tool", "thinking_step", {
                    "agent_type": self.agent_type.value,
                    "node": "complete",
                    "title": "方案生成完成",
                    "summary": "维修方案已生成"
                })
                
                await ws_callback("chat", "message", {
                    "type": "ai",
                    "content": repair_plan,
                    "agent_type": self.agent_type.value,
                    "agent_header": generate_message_header(self.agent_type)
                })
            
            return repair_plan
            
        except Exception as e:
            error_msg = f"生成维修方案时出错: {str(e)}"
            print(f"❌ {error_msg}")
            
            if ws_callback:
                await ws_callback("system", "error", {
                    "agent_type": self.agent_type.value,
                    "error": error_msg
                })
            
            raise
    
    async def follow_up_question(
        self,
        question: str,
        message_queue: Optional[MessageQueue],
        ws_callback: Optional[Callable[[str, str, dict], Awaitable[None]]] = None
    ) -> str:
        """处理追问
        
        Args:
            question: 用户的追问
            message_queue: 消息队列
            ws_callback: WebSocket 回调
        
        Returns:
            追问回答
        """
        header = generate_message_header(self.agent_type, "处理追问中...")
        
        if ws_callback:
            await ws_callback("system", "agent_start", {
                "agent_type": self.agent_type.value,
                "message": header
            })
        
        # 构建包含上下文的提示
        context = ""
        if self.consultation_history:
            last_consultation = self.consultation_history[-1]
            context = f"""## 之前的咨询记录
### 缺陷信息
{json.dumps(last_consultation['input'], ensure_ascii=False, indent=2)}

### 我给出的维修方案
{last_consultation['output'][:1000]}...

"""
        
        follow_up_prompt = f"""{context}## 用户追问
{question}

请基于之前的维修方案，回答用户的追问。如果追问涉及新的问题，请提供详细解答。"""
        
        if message_queue:
            message_queue.set_current_agent(self.agent_type)
            message_queue.add_message_sync(MessageRole.USER, question, self.agent_type)
        
        messages = [
            SystemMessage(content=REPAIR_SYSTEM_PROMPT),
            HumanMessage(content=follow_up_prompt)
        ]
        
        try:
            response = await llm.ainvoke(messages)
            answer = response.content
            
            if message_queue:
                message_queue.add_message_sync(MessageRole.ASSISTANT, answer, self.agent_type)
            
            if ws_callback:
                await ws_callback("chat", "message", {
                    "type": "ai",
                    "content": answer,
                    "agent_type": self.agent_type.value,
                    "agent_header": generate_message_header(self.agent_type)
                })
            
            return answer
            
        except Exception as e:
            error_msg = f"处理追问时出错: {str(e)}"
            if ws_callback:
                await ws_callback("system", "error", {
                    "agent_type": self.agent_type.value,
                    "error": error_msg
                })
            raise
    
    async def process_message(
        self,
        message: str,
        message_queue: Optional[MessageQueue],
        ws_callback: Optional[Callable[[str, str, dict], Awaitable[None]]] = None,
        input_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """处理用户消息
        
        Args:
            message: 用户消息
            message_queue: 消息队列
            ws_callback: WebSocket 回调
            input_data: 表单输入数据（可选）
        
        Returns:
            Agent 响应
        """
        if input_data:
            # 有表单数据，进行维修咨询
            return await self.consult_repair(input_data, message_queue, ws_callback)
        elif self.consultation_history:
            # 有历史咨询，视为追问
            return await self.follow_up_question(message, message_queue, ws_callback)
        else:
            # 没有任何上下文，引导用户
            guide_msg = """🔧 **维修方案咨询助手**

我可以为您提供专业的维修方案咨询。请提供以下信息：

1. **缺陷描述**：详细描述故障现象
2. **缺陷位置**：设备位置或区段
3. **紧急程度**：紧急 / 一般 / 可延期
4. **设备信息**：设备型号、使用年限（可选）

我将为您提供：
- 🔍 故障原因分析
- 🛠️ 推荐维修工法
- 📦 物料清单
- ⏱️ 工时评估
- ⚠️ 安全注意事项
- 📚 相关技术标准

请使用右侧表单填写详细信息，或直接描述您遇到的问题。"""
            
            if ws_callback:
                await ws_callback("chat", "message", {
                    "type": "ai",
                    "content": guide_msg,
                    "agent_type": self.agent_type.value,
                    "agent_header": generate_message_header(self.agent_type)
                })
            
            return guide_msg
    
    def _build_user_prompt(self, input_data: Dict[str, Any]) -> str:
        """构建用户提示"""
        parts = ["请为以下缺陷提供维修方案咨询：\n"]
        
        if input_data.get("defect_description"):
            parts.append(f"## 缺陷描述\n{input_data['defect_description']}\n")
        
        if input_data.get("defect_location"):
            parts.append(f"## 缺陷位置\n{input_data['defect_location']}\n")
        
        if input_data.get("urgency_level"):
            urgency_map = {
                "urgent": "🔴 紧急",
                "normal": "🟡 一般",
                "deferred": "🟢 可延期"
            }
            urgency = urgency_map.get(input_data['urgency_level'], input_data['urgency_level'])
            parts.append(f"## 紧急程度\n{urgency}\n")
        
        if input_data.get("equipment_info"):
            parts.append(f"## 设备信息\n{input_data['equipment_info']}\n")
        
        if input_data.get("additional_info"):
            parts.append(f"## 补充信息\n{input_data['additional_info']}\n")
        
        return "\n".join(parts)


# ===================== 测试入口 =====================
if __name__ == "__main__":
    async def test():
        agent = RepairAgent()
        
        # 测试维修咨询
        test_input = {
            "defect_description": "轴承运行时发出异常噪音，伴随轻微振动，温度比正常值高出15℃",
            "defect_location": "1号线0116车A转向架左侧一轴",
            "urgency_level": "urgent",
            "equipment_info": "SKF轴承，型号6208-2RS，已运行3年",
            "additional_info": "上周例行检查时未发现异常"
        }
        
        async def print_callback(msg_type: str, action: str, data: dict):
            print(f"[{msg_type}] {action}: {json.dumps(data, ensure_ascii=False, indent=2)[:200]}")
        
        result = await agent.consult_repair(test_input, None, print_callback)
        print("\n维修方案：")
        print(result)
    
    asyncio.run(test())
