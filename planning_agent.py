#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
巡检计划自动生成 Agent
基于提示工程，让 LLM 根据输入生成巡检计划

输入：历史缺陷分布、设备台账、天窗时间、人员排班
输出：自动生成月度/周度巡检计划，标注高风险区段
支持自然语言调整计划
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
    temperature=0.7,
    model=model_name
)


# ===================== 系统提示词 =====================
PLANNING_SYSTEM_PROMPT = """你是一位资深的轨道交通巡检计划专家。你的职责是根据用户提供的信息，智能生成科学合理的巡检计划。

## 你的能力
1. **分析历史缺陷分布**：识别高风险区段和设备
2. **制定巡检计划**：根据设备重要性、风险等级、天窗时间合理安排
3. **优化资源配置**：根据人员排班情况合理分配任务
4. **支持自然语言调整**：理解用户的调整需求并修改计划

## 输入信息说明
用户可能提供以下信息（部分或全部）：
- **历史缺陷分布**：各区段/设备的历史故障记录
- **设备台账**：设备清单、位置、维护周期等
- **天窗时间**：可用的作业时间窗口
- **人员排班**：可用的巡检人员及其排班

## 输出格式要求
请以 Markdown 格式输出巡检计划，包含：

### 巡检计划概览
- 计划周期：月度/周度
- 计划时间范围
- 涉及区段/设备数量
- 预计总工时

### 风险评估
用表格列出高风险区段：
| 区段/设备 | 风险等级 | 历史故障次数 | 建议巡检频率 |

### 详细巡检安排
按日期/班次列出：
| 日期 | 时段 | 区段 | 巡检内容 | 负责人 | 预计工时 |

### 注意事项
- 高风险区段的特别关注点
- 安全提醒

## 自然语言调整
当用户说类似"下周二的巡检优先安排隧道区段"这样的话时：
1. 理解用户意图
2. 在现有计划基础上进行调整
3. 输出调整后的计划，并标注变更内容

## 重要提醒
- 优先安排高风险区段
- 确保计划在天窗时间内可执行
- 考虑人员连续作业的疲劳问题
- 相邻区段可合并巡检以提高效率
"""


class PlanningAgent:
    """巡检计划自动生成 Agent"""
    
    def __init__(self):
        self.agent_type = AgentType.PLANNING
        self.current_plan: Optional[str] = None
        print(f"\n{'='*70}")
        print(f"{generate_message_header(self.agent_type)} 初始化完成")
        print(f"{'='*70}\n")
    
    async def generate_plan(
        self,
        input_data: Dict[str, Any],
        message_queue: Optional[MessageQueue],
        ws_callback: Optional[Callable[[str, str, dict], Awaitable[None]]] = None
    ) -> str:
        """生成巡检计划
        
        Args:
            input_data: 包含历史缺陷、设备台账、天窗时间、人员排班的输入数据
            message_queue: 消息队列
            ws_callback: WebSocket 回调函数
        
        Returns:
            生成的巡检计划 (Markdown 格式)
        """
        header = generate_message_header(self.agent_type, "正在生成巡检计划...")
        
        if ws_callback:
            await ws_callback("system", "agent_start", {
                "agent_type": self.agent_type.value,
                "message": header
            })
        
        # 构建用户提示
        user_prompt = self._build_user_prompt(input_data)
        
        # 获取历史消息（如果有）
        history_messages = []
        if message_queue:
            history_messages = message_queue.get_langchain_messages(self.agent_type)
            message_queue.set_current_agent(self.agent_type)
            message_queue.add_message_sync(MessageRole.USER, user_prompt, self.agent_type)
        
        # 构建完整消息列表
        messages = [
            SystemMessage(content=PLANNING_SYSTEM_PROMPT),
            *history_messages,
            HumanMessage(content=user_prompt)
        ]
        
        try:
            if ws_callback:
                await ws_callback("tool", "thinking_step", {
                    "agent_type": self.agent_type.value,
                    "node": "analysis",
                    "title": "分析输入数据",
                    "summary": "正在分析历史缺陷、设备台账、天窗时间和人员排班信息..."
                })
            
            # 调用 LLM
            response = await llm.ainvoke(messages)
            plan_content = response.content
            
            # 保存当前计划
            self.current_plan = plan_content
            
            # 记录到消息队列
            if message_queue:
                message_queue.add_message_sync(MessageRole.ASSISTANT, plan_content, self.agent_type)
            
            if ws_callback:
                await ws_callback("tool", "thinking_step", {
                    "agent_type": self.agent_type.value,
                    "node": "generate",
                    "title": "生成计划完成",
                    "summary": "巡检计划已生成"
                })
                
                await ws_callback("chat", "message", {
                    "type": "ai",
                    "content": plan_content,
                    "agent_type": self.agent_type.value,
                    "agent_header": generate_message_header(self.agent_type)
                })
            
            return plan_content
            
        except Exception as e:
            error_msg = f"生成计划时出错: {str(e)}"
            print(f"❌ {error_msg}")
            
            if ws_callback:
                await ws_callback("system", "error", {
                    "agent_type": self.agent_type.value,
                    "error": error_msg
                })
            
            raise
    
    async def adjust_plan(
        self,
        adjustment_request: str,
        message_queue: Optional[MessageQueue],
        ws_callback: Optional[Callable[[str, str, dict], Awaitable[None]]] = None
    ) -> str:
        """根据自然语言调整计划
        
        Args:
            adjustment_request: 用户的调整请求，如"下周二的巡检优先安排隧道区段"
            message_queue: 消息队列
            ws_callback: WebSocket 回调函数
        
        Returns:
            调整后的巡检计划
        """
        if not self.current_plan:
            return "❌ 当前没有可调整的计划，请先生成一个巡检计划。"
        
        header = generate_message_header(self.agent_type, "正在调整巡检计划...")
        
        if ws_callback:
            await ws_callback("system", "agent_start", {
                "agent_type": self.agent_type.value,
                "message": header
            })
        
        # 构建调整提示
        adjust_prompt = f"""## 当前计划
{self.current_plan}

## 用户调整请求
{adjustment_request}

## 要求
1. 理解用户的调整意图
2. 在现有计划基础上进行修改
3. 输出完整的调整后计划
4. 在计划末尾用 "📝 变更说明" 标注本次调整的内容
"""
        
        # 记录到消息队列
        if message_queue:
            message_queue.set_current_agent(self.agent_type)
            message_queue.add_message_sync(MessageRole.USER, adjustment_request, self.agent_type)
        
        messages = [
            SystemMessage(content=PLANNING_SYSTEM_PROMPT),
            HumanMessage(content=adjust_prompt)
        ]
        
        try:
            response = await llm.ainvoke(messages)
            adjusted_plan = response.content
            
            # 更新当前计划
            self.current_plan = adjusted_plan
            
            if message_queue:
                message_queue.add_message_sync(MessageRole.ASSISTANT, adjusted_plan, self.agent_type)
            
            if ws_callback:
                await ws_callback("chat", "message", {
                    "type": "ai",
                    "content": adjusted_plan,
                    "agent_type": self.agent_type.value,
                    "agent_header": generate_message_header(self.agent_type)
                })
            
            return adjusted_plan
            
        except Exception as e:
            error_msg = f"调整计划时出错: {str(e)}"
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
        # 判断是生成新计划还是调整现有计划
        if input_data:
            # 有表单数据，生成新计划
            return await self.generate_plan(input_data, message_queue, ws_callback)
        elif self.current_plan:
            # 有现有计划，视为调整请求
            return await self.adjust_plan(message, message_queue, ws_callback)
        else:
            # 没有计划也没有表单数据，引导用户
            guide_msg = """📅 **巡检计划生成助手**

我可以帮您生成智能巡检计划。请提供以下信息（可选）：

1. **历史缺陷分布**：各区段的历史故障记录
2. **设备台账**：需要巡检的设备清单
3. **天窗时间**：可用的作业时间窗口
4. **人员排班**：可用的巡检人员

您也可以直接告诉我您的需求，例如：
- "生成下周的隧道区段巡检计划"
- "安排周一到周五的日常巡检"

请使用右侧表单填写详细信息，或直接在此描述您的需求。"""
            
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
        parts = ["请根据以下信息生成巡检计划：\n"]
        
        if input_data.get("plan_type"):
            parts.append(f"## 计划类型\n{input_data['plan_type']}\n")
        
        if input_data.get("date_range"):
            parts.append(f"## 计划时间范围\n{input_data['date_range']}\n")
        
        if input_data.get("defect_history"):
            parts.append(f"## 历史缺陷分布\n{input_data['defect_history']}\n")
        
        if input_data.get("equipment_list"):
            parts.append(f"## 设备台账\n{input_data['equipment_list']}\n")
        
        if input_data.get("window_time"):
            parts.append(f"## 天窗时间\n{input_data['window_time']}\n")
        
        if input_data.get("staff_schedule"):
            parts.append(f"## 人员排班\n{input_data['staff_schedule']}\n")
        
        if input_data.get("special_requirements"):
            parts.append(f"## 特殊要求\n{input_data['special_requirements']}\n")
        
        return "\n".join(parts)


# ===================== 测试入口 =====================
if __name__ == "__main__":
    async def test():
        agent = PlanningAgent()
        
        # 测试生成计划
        test_input = {
            "plan_type": "周度计划",
            "date_range": "2026年3月23日 - 2026年3月29日",
            "defect_history": "隧道区段：本月故障3次；道岔区域：本月故障2次",
            "equipment_list": "1号线全线设备，重点关注隧道区段和道岔",
            "window_time": "每日 00:30-04:30",
            "staff_schedule": "巡检组A（周一、三、五）、巡检组B（周二、四、六）",
            "special_requirements": "周二优先安排隧道区段巡检"
        }
        
        async def print_callback(msg_type: str, action: str, data: dict):
            print(f"[{msg_type}] {action}: {json.dumps(data, ensure_ascii=False, indent=2)[:200]}")
        
        result = await agent.generate_plan(test_input, None, print_callback)
        print("\n生成的计划：")
        print(result)
    
    asyncio.run(test())
