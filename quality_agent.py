#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工单质量检查 Agent
基于提示工程，让 LLM 审核工单质量

功能：
- 自动审核已完成的工单
- 检查照片、测量数据是否齐全
- 比对"维修前vs维修后"数据，判断是否达到验收标准
- 发现问题自动退回并标注原因

注意：不需要 RAG 手段，直接根据用户输入输出
支持文本上传
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
    temperature=0.3,  # 低温度保证评审的一致性
    model=model_name
)


# ===================== 系统提示词 =====================
QUALITY_CHECK_SYSTEM_PROMPT = """你是一位严谨专业的轨道交通维修工单质量审核专家。你的职责是确保每一份维修工单都符合质量标准。

## 你的审核职责
1. **完整性检查**：确保工单信息完整
2. **数据核验**：检查测量数据的合理性
3. **前后对比**：比对维修前后的数据变化
4. **标准符合**：判断是否达到验收标准
5. **问题标注**：发现问题时明确指出原因

## 审核检查项

### 必填信息检查
- [ ] 工单编号
- [ ] 维修日期和时间
- [ ] 维修人员信息
- [ ] 设备/位置信息
- [ ] 缺陷描述
- [ ] 维修内容描述
- [ ] 维修前数据/状态
- [ ] 维修后数据/状态

### 照片记录检查（如适用）
- [ ] 维修前照片
- [ ] 维修过程照片
- [ ] 维修后照片
- [ ] 照片清晰度是否满足要求
- [ ] 照片是否能体现维修效果

### 测量数据检查
- [ ] 数据是否在合理范围内
- [ ] 数据单位是否正确
- [ ] 测量方法是否规范
- [ ] 是否有异常数据需要解释

### 维修效果评估
- [ ] 维修后数据是否达到标准
- [ ] 问题是否已完全解决
- [ ] 是否需要后续跟踪

## 输出格式要求

### 审核结果
请输出以下格式的审核报告：

```
## ✅/❌ 审核结论

**审核结果**: 通过 / 退回
**审核时间**: YYYY-MM-DD HH:MM
**工单编号**: XXX

---

### 📋 完整性检查
| 检查项 | 状态 | 备注 |
|--------|------|------|
| 工单编号 | ✅/❌ | |
| 维修日期 | ✅/❌ | |
| ... | | |

### 📊 数据核验
| 数据项 | 维修前 | 维修后 | 标准值 | 判定 |
|--------|--------|--------|--------|------|

### 📸 照片记录
| 照片类型 | 是否提供 | 质量评价 |
|----------|----------|----------|

### 🔍 问题清单
（如果有问题）
1. **问题描述**: XXX
   **问题位置**: XXX
   **整改要求**: XXX

### 📝 审核意见
详细的审核意见和建议...

### ⚡ 退回原因（如退回）
明确列出退回的主要原因和需要补充/修改的内容
```

## 审核原则
1. **客观公正**：基于事实和标准进行判断
2. **严格把关**：不放过任何质量问题
3. **指导性强**：退回时要明确说明问题和改进方向
4. **人性化**：考虑实际情况，避免过于苛刻
"""


class QualityAgent:
    """工单质量检查 Agent"""
    
    def __init__(self):
        self.agent_type = AgentType.QUALITY
        self.check_history: List[Dict[str, Any]] = []
        print(f"\n{'='*70}")
        print(f"{generate_message_header(self.agent_type)} 初始化完成")
        print(f"{'='*70}\n")
    
    async def check_work_order(
        self,
        work_order_content: str,
        message_queue: Optional[MessageQueue],
        ws_callback: Optional[Callable[[str, str, dict], Awaitable[None]]] = None,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """检查工单质量
        
        Args:
            work_order_content: 工单内容（文本格式）
            message_queue: 消息队列
            ws_callback: WebSocket 回调函数
            additional_info: 额外信息（如照片说明、测量数据等）
        
        Returns:
            审核结果字典，包含：
            - passed: 是否通过
            - report: 审核报告
            - issues: 问题列表
        """
        header = generate_message_header(self.agent_type, "正在审核工单...")
        
        if ws_callback:
            await ws_callback("system", "agent_start", {
                "agent_type": self.agent_type.value,
                "message": header
            })
        
        # 构建审核提示
        user_prompt = self._build_check_prompt(work_order_content, additional_info)
        
        # 记录到消息队列
        if message_queue:
            message_queue.set_current_agent(self.agent_type)
            message_queue.add_message_sync(MessageRole.USER, f"请审核以下工单:\n{work_order_content[:500]}...", self.agent_type)
        
        messages = [
            SystemMessage(content=QUALITY_CHECK_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ]
        
        try:
            # 发送审核步骤
            steps = [
                ("completeness", "完整性检查", "检查工单必填信息是否完整..."),
                ("data_verify", "数据核验", "核验测量数据的合理性..."),
                ("compare", "前后对比", "比对维修前后数据变化..."),
                ("standard", "标准符合", "判断是否达到验收标准...")
            ]
            
            for step_id, title, summary in steps:
                if ws_callback:
                    await ws_callback("tool", "thinking_step", {
                        "agent_type": self.agent_type.value,
                        "node": step_id,
                        "title": title,
                        "summary": summary
                    })
                await asyncio.sleep(0.3)  # 模拟处理时间
            
            # 调用 LLM 进行审核
            response = await llm.ainvoke(messages)
            check_report = response.content
            
            # 解析审核结果
            passed = self._parse_result(check_report)
            issues = self._extract_issues(check_report)
            
            result = {
                "passed": passed,
                "report": check_report,
                "issues": issues,
                "timestamp": datetime.now().isoformat()
            }
            
            # 记录审核历史
            self.check_history.append({
                "work_order": work_order_content[:500],
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
            
            # 记录到消息队列
            if message_queue:
                message_queue.add_message_sync(MessageRole.ASSISTANT, check_report, self.agent_type)
            
            if ws_callback:
                status = "✅ 审核通过" if passed else "❌ 审核不通过，需退回修改"
                await ws_callback("tool", "thinking_step", {
                    "agent_type": self.agent_type.value,
                    "node": "result",
                    "title": "审核完成",
                    "summary": status
                })
                
                await ws_callback("chat", "message", {
                    "type": "ai",
                    "content": check_report,
                    "agent_type": self.agent_type.value,
                    "agent_header": generate_message_header(self.agent_type)
                })
                
                # 发送审核结果
                await ws_callback("tool", "quality_result", {
                    "agent_type": self.agent_type.value,
                    "passed": passed,
                    "issues_count": len(issues),
                    "issues": issues
                })
            
            return result
            
        except Exception as e:
            error_msg = f"审核工单时出错: {str(e)}"
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
        uploaded_content: Optional[str] = None
    ) -> str:
        """处理用户消息
        
        Args:
            message: 用户消息
            message_queue: 消息队列
            ws_callback: WebSocket 回调
            uploaded_content: 上传的工单内容（文本）
        
        Returns:
            Agent 响应
        """
        # 如果有上传的内容，进行审核
        if uploaded_content:
            result = await self.check_work_order(
                uploaded_content, 
                message_queue, 
                ws_callback,
                {"user_note": message}
            )
            return result["report"]
        
        # 如果消息本身是工单内容（较长的结构化文本），进行审核
        if len(message) > 200 and any(keyword in message for keyword in ["工单", "维修", "检修", "设备", "日期"]):
            result = await self.check_work_order(message, message_queue, ws_callback)
            return result["report"]
        
        # 否则显示引导信息
        guide_msg = """✅ **工单质量检查助手**

我可以帮您审核维修工单的质量。请通过以下方式提交工单：

### 方式一：粘贴工单内容
直接在聊天框中粘贴工单的完整内容

### 方式二：上传工单文件
点击上传按钮，上传工单文本文件

### 我会检查的内容
1. 📋 **完整性检查**：必填信息是否齐全
2. 📊 **数据核验**：测量数据是否合理
3. 📸 **照片记录**：照片是否清晰完整
4. 🔄 **前后对比**：维修效果是否达标
5. ⚠️ **问题标注**：发现问题明确指出

### 审核结果
- ✅ **通过**：工单符合质量标准
- ❌ **退回**：列出问题清单和整改要求

请提交需要审核的工单内容。"""
        
        if ws_callback:
            await ws_callback("chat", "message", {
                "type": "ai",
                "content": guide_msg,
                "agent_type": self.agent_type.value,
                "agent_header": generate_message_header(self.agent_type)
            })
        
        return guide_msg
    
    def _build_check_prompt(
        self, 
        work_order_content: str, 
        additional_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """构建审核提示"""
        prompt_parts = [
            "请审核以下维修工单：",
            "",
            "## 工单内容",
            work_order_content,
            ""
        ]
        
        if additional_info:
            prompt_parts.append("## 补充信息")
            for key, value in additional_info.items():
                prompt_parts.append(f"- {key}: {value}")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "## 审核要求",
            "1. 检查工单完整性",
            "2. 核验数据合理性",
            "3. 比对维修前后数据",
            "4. 判断是否符合验收标准",
            "5. 列出所有发现的问题",
            "",
            "请按照规定格式输出审核报告。"
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_result(self, report: str) -> bool:
        """解析审核结果，判断是否通过"""
        # 通过关键词判断
        pass_keywords = ["通过", "✅", "合格", "符合标准"]
        fail_keywords = ["退回", "❌", "不通过", "不合格", "需要修改"]
        
        # 检查前几行确定结果
        first_lines = report[:500].lower()
        
        for keyword in fail_keywords:
            if keyword.lower() in first_lines:
                return False
        
        for keyword in pass_keywords:
            if keyword.lower() in first_lines:
                return True
        
        # 默认通过
        return True
    
    def _extract_issues(self, report: str) -> List[Dict[str, str]]:
        """从报告中提取问题列表"""
        issues = []
        
        # 简单的问题提取逻辑
        lines = report.split('\n')
        in_issues_section = False
        
        for line in lines:
            if '问题清单' in line or '退回原因' in line:
                in_issues_section = True
                continue
            
            if in_issues_section:
                if line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '-', '*')):
                    issues.append({
                        "description": line.strip().lstrip('0123456789.-* '),
                        "severity": "warning"
                    })
                elif line.strip().startswith('###') or line.strip().startswith('##'):
                    in_issues_section = False
        
        return issues


# ===================== 测试入口 =====================
if __name__ == "__main__":
    async def test():
        agent = QualityAgent()
        
        # 测试工单内容
        test_work_order = """
维修工单编号: WO-2026-03-001
维修日期: 2026-03-19
维修人员: 张三、李四

设备信息:
- 设备名称: 轴承组件
- 设备位置: 1号线0116车A转向架
- 设备型号: SKF 6208-2RS

缺陷描述:
轴承运行异常噪音，温度偏高

维修内容:
1. 拆卸轴承组件
2. 清洁轴承座
3. 更换新轴承
4. 添加润滑脂
5. 安装并调试

维修前数据:
- 轴承温度: 78℃
- 振动值: 4.5mm/s
- 噪音: 明显

维修后数据:
- 轴承温度: 45℃
- 振动值: 1.2mm/s
- 噪音: 正常

使用材料:
- SKF轴承 6208-2RS x 1
- 润滑脂 200g

照片记录: 
- 维修前照片: 已拍摄（3张）
- 维修后照片: 已拍摄（2张）
"""
        
        async def print_callback(msg_type: str, action: str, data: dict):
            print(f"[{msg_type}] {action}: {json.dumps(data, ensure_ascii=False, indent=2)[:200]}")
        
        result = await agent.check_work_order(test_work_order, None, print_callback)
        print("\n审核结果：")
        print(f"通过: {result['passed']}")
        print(f"问题数: {len(result['issues'])}")
        print(f"\n报告:\n{result['report']}")
    
    asyncio.run(test())
