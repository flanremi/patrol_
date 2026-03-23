#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
现场作业指导 Agent
支持多模态交互（图片+文字）+ 位置感知的上下文检索

功能特点：
1. 支持图片（base64）+ 文字描述的多模态输入
2. 基于位置信息推送相关历史病害和注意事项
3. 支持语音交互转文字（前端处理）
4. 支持焊缝、裂纹等缺陷的标准查询

输入：图片(base64)、问题描述、位置信息
输出：技术标准、评判依据、历史病害、注意事项
"""
import os
import json
import asyncio
import base64
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

# 文本 LLM
llm = ChatOpenAI(
    base_url=base_url,
    api_key=api_key,
    temperature=0.5,
    model=model_name
)

# TODO: 多模态 LLM（支持图片输入）
# 如果使用支持视觉的模型（如 qwen-vl-plus），可以替换为：
# vision_model_name = os.getenv("OPENAI_VISION_MODEL", "qwen-vl-plus")
# vision_llm = ChatOpenAI(
#     base_url=base_url,
#     api_key=api_key,
#     temperature=0.3,
#     model=vision_model_name
# )


# ===================== 系统提示词 =====================
FIELD_GUIDANCE_SYSTEM_PROMPT = """你是一位资深的轨道交通现场作业技术专家。你在现场为工人提供实时技术指导和标准查询服务。

## 你的能力
1. **缺陷评判标准查询**：根据缺陷类型（如焊缝裂纹、轮对磨耗等）提供相关技术标准
2. **历史病害分析**：基于位置信息检索该区段的历史病害记录和注意事项
3. **现场技术指导**：根据图片和描述提供专业的处置建议
4. **安全提醒**：强调现场作业的安全注意事项
5. **标准文档引用**：引用相关的技术规范和作业指导书

## 输入信息
用户可能提供以下信息：
- **问题描述**：工人询问的具体问题
- **图片**：现场拍摄的缺陷照片（可选）
- **位置信息**：当前作业区段（如"1号线 K12+500"）

## 常见问题类型
1. 焊缝缺陷评判（裂纹、气孔、夹渣、咬边等）
2. 轮对磨耗限度判定
3. 轴承异常诊断
4. 车体结构缺陷
5. 电气设备故障
6. 制动系统问题

## 输出格式要求
请以 Markdown 格式输出，根据问题类型包含以下部分：

### 📋 问题分析
- 问题类型识别
- 关键信息提取

### 📐 评判标准
提供相关的技术标准和限度值：
- 标准名称和编号
- 具体的判定依据
- 合格/不合格界限值

### ⚠️ 历史病害记录
基于位置信息，提供该区段的历史病害：
| 时间 | 位置 | 缺陷类型 | 处理方式 | 备注 |
|------|------|----------|----------|------|

### 🔧 处置建议
1. 立即处置措施
2. 后续跟踪要求
3. 上报流程

### 📌 注意事项
- 现场作业安全提醒
- 特殊工况注意点
- 防护要求

### 📚 参考标准
- 《XXX技术规范》
- 《XXX作业指导书》

## 重要提醒
- 安全第一，确保工人人身安全
- 遇到不确定情况，建议上报确认
- 引用的标准必须准确，不要编造标准号
"""


# ===================== 模拟数据：历史病害库 =====================
# TODO: 实际项目中应从数据库或知识库检索
HISTORY_DEFECTS_DB = {
    "1号线": [
        {
            "time": "2025-12-15",
            "location": "K12+300",
            "defect_type": "焊缝裂纹",
            "treatment": "打磨后补焊",
            "note": "该区段曾多次出现焊缝开裂"
        },
        {
            "time": "2025-11-20",
            "location": "K12+500",
            "defect_type": "轨道沉降",
            "treatment": "道床加固",
            "note": "地质条件较差，需定期监测"
        },
        {
            "time": "2025-10-08",
            "location": "K13+100",
            "defect_type": "接触网磨耗",
            "treatment": "更换接触线",
            "note": "弓网关系需重点关注"
        }
    ],
    "2号线": [
        {
            "time": "2025-11-30",
            "location": "K05+200",
            "defect_type": "轮对擦伤",
            "treatment": "旋修处理",
            "note": "该车多次出现轮对问题"
        }
    ],
    "default": [
        {
            "time": "2025-12-01",
            "location": "通用",
            "defect_type": "设备老化",
            "treatment": "定期检修",
            "note": "注意设备使用年限"
        }
    ]
}


# ===================== 模拟数据：技术标准库 =====================
# TODO: 实际项目中应从知识库检索
TECH_STANDARDS_DB = {
    "焊缝裂纹": {
        "standard_name": "《铁路钢桥制造规范》TB 10212-2009",
        "criteria": [
            "裂纹：不允许存在任何裂纹，一经发现必须处理",
            "裂纹长度超过5mm：需打磨后补焊",
            "裂纹深度超过壁厚20%：需更换部件"
        ],
        "reference": ["《焊接质量检验标准》GB/T 3323", "《钢结构工程施工质量验收规范》GB 50205"]
    },
    "轮对磨耗": {
        "standard_name": "《机车车辆轮对技术条件》TB/T 2395",
        "criteria": [
            "轮缘厚度：≥22mm（新造≥32mm）",
            "轮缘高度：≥25mm（新造≥28mm）",
            "踏面磨耗深度：≤8mm",
            "轮径差（同轴）：≤1mm"
        ],
        "reference": ["《城市轨道交通车辆通用技术条件》GB/T 7928"]
    },
    "轴承温度": {
        "standard_name": "《铁道车辆滚动轴承》TB/T 1183",
        "criteria": [
            "正常运行温度：≤90℃",
            "温升报警值：与环境温差≤50℃",
            "紧急停车值：绝对温度≥110℃"
        ],
        "reference": ["《城轨车辆走行部检修规程》"]
    },
    "default": {
        "standard_name": "通用检修标准",
        "criteria": [
            "目视检查无明显缺陷",
            "功能测试正常",
            "尺寸在公差范围内"
        ],
        "reference": ["参考相关专业技术规范"]
    }
}


class FieldGuidanceAgent:
    """现场作业指导 Agent"""
    
    def __init__(self):
        self.agent_type = AgentType.FIELD_GUIDANCE
        self.guidance_history: List[Dict[str, Any]] = []
        print(f"\n{'='*70}")
        print(f"{generate_message_header(self.agent_type)} 初始化完成")
        print(f"{'='*70}\n")
    
    def _extract_location_info(self, location: str) -> str:
        """从位置信息中提取线路名称"""
        if not location:
            return "default"
        
        # 简单匹配线路名称
        for line_name in HISTORY_DEFECTS_DB.keys():
            if line_name in location:
                return line_name
        return "default"
    
    def _get_history_defects(self, location: str) -> List[Dict[str, Any]]:
        """获取历史病害记录"""
        line_name = self._extract_location_info(location)
        return HISTORY_DEFECTS_DB.get(line_name, HISTORY_DEFECTS_DB["default"])
    
    def _get_tech_standard(self, defect_keywords: List[str]) -> Dict[str, Any]:
        """获取技术标准"""
        for keyword in defect_keywords:
            for key, standard in TECH_STANDARDS_DB.items():
                if keyword in key or key in keyword:
                    return standard
        return TECH_STANDARDS_DB["default"]
    
    def _extract_defect_keywords(self, question: str) -> List[str]:
        """从问题中提取缺陷关键词"""
        keywords = []
        defect_types = ["焊缝", "裂纹", "磨耗", "轮对", "轴承", "温度", "振动", "噪音"]
        for defect in defect_types:
            if defect in question:
                keywords.append(defect)
        return keywords if keywords else ["通用"]
    
    def _build_context_prompt(
        self,
        question: str,
        location: str,
        image_base64: Optional[str] = None
    ) -> str:
        """构建包含上下文的提示"""
        parts = []
        
        # 问题描述
        parts.append(f"## 工人问题\n{question}\n")
        
        # 位置信息
        if location:
            parts.append(f"## 当前位置\n{location}\n")
        
        # 历史病害
        history_defects = self._get_history_defects(location)
        if history_defects:
            parts.append("## 该区段历史病害记录")
            for defect in history_defects:
                parts.append(f"- {defect['time']} | {defect['location']} | {defect['defect_type']} | {defect['treatment']} | {defect['note']}")
            parts.append("")
        
        # 技术标准
        keywords = self._extract_defect_keywords(question)
        standard = self._get_tech_standard(keywords)
        parts.append(f"## 相关技术标准参考\n标准名称：{standard['standard_name']}")
        parts.append("判定依据：")
        for criterion in standard['criteria']:
            parts.append(f"- {criterion}")
        parts.append(f"参考文献：{', '.join(standard['reference'])}\n")
        
        # 图片说明
        if image_base64:
            parts.append("## 现场照片\n[用户已上传现场照片，请结合照片进行分析]\n")
        
        parts.append("请根据以上信息，为现场工人提供专业的技术指导。")
        
        return "\n".join(parts)
    
    async def provide_guidance(
        self,
        input_data: Dict[str, Any],
        message_queue: Optional[MessageQueue],
        ws_callback: Optional[Callable[[str, str, dict], Awaitable[None]]] = None
    ) -> str:
        """提供现场作业指导
        
        Args:
            input_data: 包含 question, location, image_base64 的输入数据
            message_queue: 消息队列
            ws_callback: WebSocket 回调函数
        
        Returns:
            技术指导内容 (Markdown 格式)
        """
        header = generate_message_header(self.agent_type, "正在分析现场问题...")
        
        if ws_callback:
            await ws_callback("system", "agent_start", {
                "agent_type": self.agent_type.value,
                "message": header
            })
        
        question = input_data.get("question", "")
        location = input_data.get("location", "")
        image_base64 = input_data.get("image_base64")
        
        # 构建上下文提示
        context_prompt = self._build_context_prompt(question, location, image_base64)
        
        # 记录用户消息
        if message_queue:
            message_queue.set_current_agent(self.agent_type)
            user_msg = f"问题：{question}"
            if location:
                user_msg += f"\n位置：{location}"
            if image_base64:
                user_msg += "\n[已上传现场照片]"
            message_queue.add_message_sync(MessageRole.USER, user_msg, self.agent_type)
        
        messages = [
            SystemMessage(content=FIELD_GUIDANCE_SYSTEM_PROMPT),
            HumanMessage(content=context_prompt)
        ]
        
        try:
            # 发送思考步骤
            if ws_callback:
                await ws_callback("tool", "thinking_step", {
                    "agent_type": self.agent_type.value,
                    "node": "context_retrieval",
                    "title": "上下文检索",
                    "summary": f"正在检索 {location or '当前区段'} 的历史病害和技术标准..."
                })
            
            # TODO: 如果有图片且使用多模态模型，可以构建多模态消息
            # 目前使用纯文本模式，图片信息作为提示说明
            # if image_base64 and vision_llm:
            #     # 构建多模态消息
            #     messages = [
            #         SystemMessage(content=FIELD_GUIDANCE_SYSTEM_PROMPT),
            #         HumanMessage(content=[
            #             {"type": "text", "text": context_prompt},
            #             {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
            #         ])
            #     ]
            #     response = await vision_llm.ainvoke(messages)
            # else:
            #     response = await llm.ainvoke(messages)
            
            # 当前使用纯文本模式
            response = await llm.ainvoke(messages)
            guidance = response.content
            
            # 记录指导历史
            self.guidance_history.append({
                "input": input_data,
                "output": guidance,
                "timestamp": datetime.now().isoformat()
            })
            
            # 记录到消息队列
            if message_queue:
                message_queue.add_message_sync(MessageRole.ASSISTANT, guidance, self.agent_type)
            
            if ws_callback:
                await ws_callback("tool", "thinking_step", {
                    "agent_type": self.agent_type.value,
                    "node": "complete",
                    "title": "指导生成完成",
                    "summary": "已生成现场作业指导"
                })
                
                await ws_callback("chat", "message", {
                    "type": "ai",
                    "content": guidance,
                    "agent_type": self.agent_type.value,
                    "agent_header": generate_message_header(self.agent_type)
                })
            
            return guidance
            
        except Exception as e:
            error_msg = f"生成现场指导时出错: {str(e)}"
            print(f"❌ {error_msg}")
            
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
            input_data: 结构化输入数据（可选，包含 image_base64, location 等）
        
        Returns:
            Agent 响应
        """
        if input_data:
            # 有结构化数据，进行现场指导
            return await self.provide_guidance(input_data, message_queue, ws_callback)
        elif self.guidance_history:
            # 有历史记录，视为追问
            return await self._handle_followup(message, message_queue, ws_callback)
        else:
            # 纯文本消息，尝试直接回答
            return await self.provide_guidance(
                {"question": message, "location": "", "image_base64": None},
                message_queue,
                ws_callback
            )
    
    async def _handle_followup(
        self,
        question: str,
        message_queue: Optional[MessageQueue],
        ws_callback: Optional[Callable[[str, str, dict], Awaitable[None]]] = None
    ) -> str:
        """处理追问"""
        header = generate_message_header(self.agent_type, "处理追问中...")
        
        if ws_callback:
            await ws_callback("system", "agent_start", {
                "agent_type": self.agent_type.value,
                "message": header
            })
        
        # 构建包含上下文的追问提示
        context = ""
        if self.guidance_history:
            last_guidance = self.guidance_history[-1]
            context = f"""## 之前的咨询记录
### 问题信息
{json.dumps(last_guidance['input'], ensure_ascii=False, indent=2)}

### 我给出的指导
{last_guidance['output'][:1500]}...

"""
        
        followup_prompt = f"""{context}## 工人追问
{question}

请基于之前的指导内容，回答工人的追问。如果涉及新的技术问题，请提供详细解答。"""
        
        if message_queue:
            message_queue.set_current_agent(self.agent_type)
            message_queue.add_message_sync(MessageRole.USER, question, self.agent_type)
        
        messages = [
            SystemMessage(content=FIELD_GUIDANCE_SYSTEM_PROMPT),
            HumanMessage(content=followup_prompt)
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


# ===================== 测试入口 =====================
if __name__ == "__main__":
    async def test():
        agent = FieldGuidanceAgent()
        
        # 测试现场指导
        test_input = {
            "question": "这个焊缝裂纹该用什么标准评判？裂纹长度大概3mm左右",
            "location": "1号线 K12+500 区段",
            "image_base64": None  # 实际使用时传入 base64 编码的图片
        }
        
        async def print_callback(msg_type: str, action: str, data: dict):
            print(f"[{msg_type}] {action}: {json.dumps(data, ensure_ascii=False, indent=2)[:300]}")
        
        result = await agent.provide_guidance(test_input, None, print_callback)
        print("\n现场指导：")
        print(result)
    
    asyncio.run(test())
