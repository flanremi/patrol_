#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新员工培训 Agent
基于提示工程的角色扮演式教学系统

功能：
1. 模拟各类故障场景，让新员工判断处置方案
2. 自动批改培训作业，指出与标准流程的差异
3. 将典型故障案例转化为培训课件

流程：
1. 根据用户需求检索出 top5 个片段（模拟）
2. 基于这 top5 个片段设计试题
3. 用户提交作业后提供培训课件
"""
import os
import json
import asyncio
import random
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


# ===================== RAG 知识库检索 =====================
# 使用新的 RAG 模块替代模拟数据

# 保留模拟数据作为备用（当 RAG 模块不可用时）
FALLBACK_KNOWLEDGE_FRAGMENTS = [
    {
        "id": "frag_001",
        "title": "轴承温度异常处置流程",
        "content": """当发现轴承温度异常时，应按以下流程处置：
1. 立即记录当前温度值和时间
2. 观察温度变化趋势（每5分钟记录一次）
3. 如温度超过85℃，应立即报告调度
4. 检查润滑状况，必要时进行应急润滑
5. 安排专业人员现场检查
6. 根据检查结果决定是否停运检修""",
        "category": "故障处置",
        "difficulty": "medium"
    },
    {
        "id": "frag_002",
        "title": "道岔故障应急处置",
        "content": """道岔故障应急处置标准流程：
1. 确认故障类型（转辙机故障/道岔卡阻/信号异常）
2. 立即通知信号楼和调度中心
3. 在确认列车停稳后方可进入轨道区域
4. 按照《道岔应急处置手册》执行人工操作
5. 做好防护措施，设置防护信号
6. 详细记录故障现象和处置过程""",
        "category": "应急处置",
        "difficulty": "hard"
    },
    {
        "id": "frag_003",
        "title": "隧道巡检安全规范",
        "content": """隧道巡检必须遵守以下安全规范：
1. 严格在天窗时间内作业
2. 必须穿戴完整防护装备（反光背心、安全帽、防护手套）
3. 至少2人同行，保持通讯畅通
4. 携带照明设备和应急工具包
5. 熟悉逃生路线和紧急疏散点
6. 如遇紧急情况，立即撤离至安全区域""",
        "category": "安全规范",
        "difficulty": "easy"
    },
]

def _get_rag_module():
    """获取 RAG 模块实例"""
    try:
        from rag_module import RAGModule
        rag = RAGModule.get_instance()
        if rag.initialize():
            return rag
    except Exception as e:
        print(f"⚠️ [TrainingAgent] RAG 模块加载失败: {e}")
    return None


# ===================== 系统提示词 =====================
TRAINING_SYSTEM_PROMPT = """你是一位经验丰富的轨道交通培训讲师。你的职责是帮助新员工掌握故障处置技能。

## 你的能力
1. **场景模拟**：创建真实的故障场景让学员判断
2. **试题设计**：基于知识点设计高质量的培训试题
3. **作业批改**：评估学员的答案，指出差异和不足
4. **课件生成**：将案例转化为结构化的培训课件

## 试题设计原则
1. 题目要贴近实际工作场景
2. 选项要有区分度，避免明显错误
3. 每道题都要有明确的考察点
4. 难度适中，有一定挑战性

## 作业批改原则
1. 客观评分，给出具体分数
2. 指出与标准答案的差异
3. 解释正确做法和原因
4. 给出改进建议

## 课件生成要求
1. 结构清晰，层次分明
2. 重点突出，便于记忆
3. 包含案例和注意事项
4. 图文并茂（用文字描述）
"""


class TrainingAgent:
    """新员工培训 Agent"""
    
    def __init__(self):
        self.agent_type = AgentType.TRAINING
        self.current_quiz: Optional[Dict[str, Any]] = None
        self.quiz_history: List[Dict[str, Any]] = []
        self.session_state = "idle"  # idle | quiz | grading | courseware
        print(f"\n{'='*70}")
        print(f"{generate_message_header(self.agent_type)} 初始化完成")
        print(f"{'='*70}\n")
    
    async def search_knowledge(
        self,
        query: str,
        top_k: int = 5,
        ws_callback: Optional[Callable[[str, str, dict], Awaitable[None]]] = None
    ) -> List[Dict[str, Any]]:
        """从 RAG 向量库检索知识片段
        
        Args:
            query: 检索查询
            top_k: 返回数量
            ws_callback: WebSocket 回调（用于发送 RAG 检索结果到前端）
        
        Returns:
            知识片段列表，每个片段包含 id, title, content, category, source, page, file_path 等字段
        """
        rag = _get_rag_module()
        
        if rag is None:
            # RAG 模块不可用，使用备用模拟数据
            print("⚠️ [TrainingAgent] RAG 模块不可用，使用备用模拟数据")
            scored_fragments = []
            query_lower = query.lower()
            
            for frag in FALLBACK_KNOWLEDGE_FRAGMENTS:
                score = 0
                text = (frag["title"] + " " + frag["content"]).lower()
                keywords = query_lower.split()
                for keyword in keywords:
                    if keyword in text:
                        score += 1
                if frag["category"].lower() in query_lower:
                    score += 2
                scored_fragments.append((score, frag))
            
            scored_fragments.sort(key=lambda x: x[0], reverse=True)
            if scored_fragments[0][0] == 0:
                random.shuffle(scored_fragments)
            
            return [frag for _, frag in scored_fragments[:top_k]]
        
        # 使用 RAG 模块检索
        print(f"📚 [TrainingAgent] 使用 RAG 模块检索: {query}")
        
        try:
            rag_result = rag.retrieve(query, top_k=top_k)
            
            # 发送 RAG 检索结果到前端
            if ws_callback:
                await ws_callback("tool", "rag_retrieval", rag_result.to_dict())
            
            # 将 RAG 结果转换为知识片段格式
            fragments = []
            for i, doc in enumerate(rag_result.documents):
                # 从内容中提取标题（取第一行或前 50 个字符）
                content_lines = doc.text.strip().split('\n')
                title = content_lines[0][:50] if content_lines else f"知识片段 {i+1}"
                if len(content_lines[0]) > 50:
                    title = title + "..."
                
                fragment = {
                    "id": f"rag_{i+1}",
                    "title": title,
                    "content": doc.text,
                    "category": "RAG检索",
                    "difficulty": "medium",
                    "source": doc.source,
                    "page": doc.page,
                    "file_path": doc.file_path,
                    "score": doc.score
                }
                fragments.append(fragment)
            
            if not fragments:
                print("⚠️ [TrainingAgent] RAG 未检索到结果，使用备用数据")
                return FALLBACK_KNOWLEDGE_FRAGMENTS[:top_k]
            
            print(f"✅ [TrainingAgent] RAG 检索到 {len(fragments)} 个知识片段")
            return fragments
            
        except Exception as e:
            print(f"❌ [TrainingAgent] RAG 检索失败: {e}")
            import traceback
            traceback.print_exc()
            return FALLBACK_KNOWLEDGE_FRAGMENTS[:top_k]
    
    async def generate_quiz(
        self,
        topic: str,
        message_queue: Optional[MessageQueue],
        ws_callback: Optional[Callable[[str, str, dict], Awaitable[None]]] = None,
        difficulty: str = "medium"
    ) -> Dict[str, Any]:
        """生成培训试题
        
        Args:
            topic: 培训主题或用户需求
            message_queue: 消息队列
            ws_callback: WebSocket 回调
            difficulty: 难度级别
        
        Returns:
            试题数据
        """
        header = generate_message_header(self.agent_type, "正在检索知识库并生成试题...")
        
        if ws_callback:
            await ws_callback("system", "agent_start", {
                "agent_type": self.agent_type.value,
                "message": header
            })
        
        # Step 1: 检索相关知识片段（使用 RAG 模块）
        if ws_callback:
            await ws_callback("tool", "thinking_step", {
                "agent_type": self.agent_type.value,
                "node": "search",
                "title": "检索知识库",
                "summary": f"正在使用 RAG 向量库检索与「{topic}」相关的知识..."
            })
        
        fragments = await self.search_knowledge(topic, top_k=5, ws_callback=ws_callback)
        
        if ws_callback:
            # 发送知识片段信息到前端（包含 RAG 检索的额外字段）
            await ws_callback("tool", "knowledge_fragments", {
                "agent_type": self.agent_type.value,
                "fragments": [
                    {
                        "id": f["id"], 
                        "title": f["title"], 
                        "category": f["category"],
                        "source": f.get("source"),
                        "page": f.get("page"),
                        "file_path": f.get("file_path")
                    }
                    for f in fragments
                ]
            })
        
        # Step 2: 基于片段生成试题
        if ws_callback:
            await ws_callback("tool", "thinking_step", {
                "agent_type": self.agent_type.value,
                "node": "generate",
                "title": "生成试题",
                "summary": f"基于 {len(fragments)} 个知识片段设计试题..."
            })
        
        # 构建试题生成提示
        fragments_text = "\n\n".join([
            f"### 知识片段 {i+1}: {f['title']}\n{f['content']}"
            for i, f in enumerate(fragments)
        ])
        
        quiz_prompt = f"""基于以下知识片段，设计一套培训试题。

{fragments_text}

## 要求
1. 设计 5 道选择题（单选或多选）
2. 每道题有 4 个选项（A、B、C、D）
3. 明确标注正确答案
4. 每道题附带解析

## 输出格式（JSON）
请严格按照以下 JSON 格式输出：

```json
{{
  "quiz_title": "试卷标题",
  "total_questions": 5,
  "questions": [
    {{
      "id": 1,
      "type": "single",
      "question": "题目内容",
      "options": {{
        "A": "选项A",
        "B": "选项B",
        "C": "选项C",
        "D": "选项D"
      }},
      "correct_answer": "A",
      "explanation": "解析内容",
      "knowledge_point": "考察知识点"
    }}
  ]
}}
```
"""
        
        messages = [
            SystemMessage(content=TRAINING_SYSTEM_PROMPT),
            HumanMessage(content=quiz_prompt)
        ]
        
        try:
            response = await llm.ainvoke(messages)
            response_text = response.content
            
            # 解析 JSON
            quiz_data = self._parse_quiz_json(response_text)
            
            if not quiz_data:
                # 如果解析失败，生成默认试题结构
                quiz_data = self._generate_default_quiz(fragments, topic)
            
            # 保存当前试题
            self.current_quiz = quiz_data
            self.session_state = "quiz"
            
            # 记录到消息队列
            if message_queue:
                message_queue.set_current_agent(self.agent_type)
                message_queue.add_message_sync(
                    MessageRole.ASSISTANT, 
                    f"已生成试题：{quiz_data.get('quiz_title', '培训试题')}", 
                    self.agent_type
                )
            
            if ws_callback:
                await ws_callback("tool", "thinking_step", {
                    "agent_type": self.agent_type.value,
                    "node": "complete",
                    "title": "试题生成完成",
                    "summary": f"共生成 {len(quiz_data.get('questions', []))} 道试题"
                })
                
                # 发送试题数据（前端用 canvas 展示）
                await ws_callback("tool", "quiz_generated", {
                    "agent_type": self.agent_type.value,
                    "quiz": quiz_data
                })
            
            return quiz_data
            
        except Exception as e:
            error_msg = f"生成试题时出错: {str(e)}"
            print(f"❌ {error_msg}")
            
            if ws_callback:
                await ws_callback("system", "error", {
                    "agent_type": self.agent_type.value,
                    "error": error_msg
                })
            
            raise
    
    async def grade_answers(
        self,
        answers: Dict[str, str],
        message_queue: Optional[MessageQueue],
        ws_callback: Optional[Callable[[str, str, dict], Awaitable[None]]] = None
    ) -> Dict[str, Any]:
        """批改用户作业
        
        Args:
            answers: 用户答案 {question_id: answer}
            message_queue: 消息队列
            ws_callback: WebSocket 回调
        
        Returns:
            批改结果
        """
        if not self.current_quiz:
            return {"error": "没有进行中的试题"}
        
        header = generate_message_header(self.agent_type, "正在批改作业...")
        
        if ws_callback:
            await ws_callback("system", "agent_start", {
                "agent_type": self.agent_type.value,
                "message": header
            })
        
        # 计算得分
        questions = self.current_quiz.get("questions", [])
        total = len(questions)
        correct = 0
        results = []
        
        for q in questions:
            q_id = str(q["id"])
            user_answer = answers.get(q_id, "").upper()
            correct_answer = q["correct_answer"].upper()
            
            is_correct = user_answer == correct_answer
            if is_correct:
                correct += 1
            
            results.append({
                "question_id": q_id,
                "question": q["question"],
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "explanation": q.get("explanation", ""),
                "knowledge_point": q.get("knowledge_point", "")
            })
        
        score = (correct / total * 100) if total > 0 else 0
        
        grade_result = {
            "score": score,
            "correct_count": correct,
            "total_count": total,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
        # 记录历史
        self.quiz_history.append({
            "quiz": self.current_quiz,
            "answers": answers,
            "grade": grade_result
        })
        
        self.session_state = "grading"
        
        # 生成批改报告
        if ws_callback:
            await ws_callback("tool", "grade_result", {
                "agent_type": self.agent_type.value,
                "grade": grade_result
            })
            
            # 生成文字报告
            report = self._generate_grade_report(grade_result)
            await ws_callback("chat", "message", {
                "type": "ai",
                "content": report,
                "agent_type": self.agent_type.value,
                "agent_header": generate_message_header(self.agent_type)
            })
        
        return grade_result
    
    async def generate_courseware(
        self,
        message_queue: Optional[MessageQueue],
        ws_callback: Optional[Callable[[str, str, dict], Awaitable[None]]] = None
    ) -> str:
        """基于试题和批改结果生成培训课件
        
        Args:
            message_queue: 消息队列
            ws_callback: WebSocket 回调
        
        Returns:
            培训课件内容
        """
        if not self.quiz_history:
            return "暂无培训记录，请先完成试题作答。"
        
        header = generate_message_header(self.agent_type, "正在生成培训课件...")
        
        if ws_callback:
            await ws_callback("system", "agent_start", {
                "agent_type": self.agent_type.value,
                "message": header
            })
        
        # 获取最近一次的培训记录
        last_session = self.quiz_history[-1]
        quiz = last_session["quiz"]
        grade = last_session["grade"]
        
        # 找出错误的题目
        wrong_questions = [r for r in grade["results"] if not r["is_correct"]]
        
        # 构建课件生成提示
        courseware_prompt = f"""基于以下培训测试结果，生成一份针对性的培训课件。

## 测试信息
- 试卷: {quiz.get('quiz_title', '培训试题')}
- 得分: {grade['score']:.1f}分
- 正确: {grade['correct_count']}/{grade['total_count']}

## 错误题目分析
{"无错误题目" if not wrong_questions else ""}
"""
        
        for wq in wrong_questions:
            courseware_prompt += f"""
### 错题 {wq['question_id']}
- 题目: {wq['question']}
- 学员答案: {wq['user_answer']}
- 正确答案: {wq['correct_answer']}
- 知识点: {wq['knowledge_point']}
"""
        
        courseware_prompt += """

## 课件生成要求
1. 针对错误的知识点进行重点讲解
2. 提供正确的处理流程和方法
3. 包含实际案例和注意事项
4. 给出后续学习建议

请生成一份结构化的培训课件（Markdown 格式）。
"""
        
        messages = [
            SystemMessage(content=TRAINING_SYSTEM_PROMPT),
            HumanMessage(content=courseware_prompt)
        ]
        
        try:
            response = await llm.ainvoke(messages)
            courseware = response.content
            
            self.session_state = "courseware"
            
            if message_queue:
                message_queue.set_current_agent(self.agent_type)
                message_queue.add_message_sync(MessageRole.ASSISTANT, "已生成培训课件", self.agent_type)
            
            if ws_callback:
                await ws_callback("tool", "courseware_generated", {
                    "agent_type": self.agent_type.value,
                    "courseware": courseware
                })
                
                await ws_callback("chat", "message", {
                    "type": "ai",
                    "content": courseware,
                    "agent_type": self.agent_type.value,
                    "agent_header": generate_message_header(self.agent_type)
                })
            
            return courseware
            
        except Exception as e:
            error_msg = f"生成课件时出错: {str(e)}"
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
        action_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """处理用户消息
        
        Args:
            message: 用户消息
            message_queue: 消息队列
            ws_callback: WebSocket 回调
            action_data: 动作数据（如提交的答案）
        
        Returns:
            Agent 响应
        """
        # 处理特定动作
        if action_data:
            action = action_data.get("action")
            
            if action == "generate_quiz":
                topic = action_data.get("topic", message)
                quiz = await self.generate_quiz(topic, message_queue, ws_callback)
                return f"已生成试题：{quiz.get('quiz_title', '培训试题')}"
            
            elif action == "submit_answers":
                answers = action_data.get("answers", {})
                grade = await self.grade_answers(answers, message_queue, ws_callback)
                return f"批改完成，得分：{grade['score']:.1f}分"
            
            elif action == "get_courseware":
                courseware = await self.generate_courseware(message_queue, ws_callback)
                return courseware
        
        # 根据会话状态处理
        if self.session_state == "quiz" and "答案" in message:
            # 可能是提交答案
            return "请使用试题面板提交您的答案。"
        
        if self.session_state == "grading":
            # 批改完成后，询问是否需要课件
            if any(kw in message for kw in ["课件", "学习", "复习", "资料"]):
                return await self.generate_courseware(message_queue, ws_callback)
        
        # 默认：生成试题或显示引导
        if any(kw in message for kw in ["试题", "测试", "考试", "练习", "培训"]):
            quiz = await self.generate_quiz(message, message_queue, ws_callback)
            return f"已生成试题：{quiz.get('quiz_title', '培训试题')}"
        
        # 显示引导信息
        guide_msg = """📚 **新员工培训助手**

欢迎使用培训系统！我可以帮助您：

### 🎯 培训功能
1. **试题生成**：基于故障案例自动生成培训试题
2. **作业批改**：自动批改并指出与标准流程的差异
3. **课件生成**：将学习内容转化为培训课件

### 🚀 开始培训
请告诉我您想学习的主题，例如：
- "我想学习轴承故障处置"
- "生成关于隧道安全的试题"
- "测试一下道岔故障处理"

或者直接描述您的培训需求，我会为您推荐相关知识并生成试题。

### 💡 培训流程
1. 提出学习需求 → 系统检索相关知识
2. 自动生成试题 → 您完成作答
3. 系统批改试卷 → 查看成绩和解析
4. 生成培训课件 → 巩固薄弱知识点

准备好了吗？告诉我您想学习什么！"""
        
        if ws_callback:
            await ws_callback("chat", "message", {
                "type": "ai",
                "content": guide_msg,
                "agent_type": self.agent_type.value,
                "agent_header": generate_message_header(self.agent_type)
            })
        
        return guide_msg
    
    def _parse_quiz_json(self, response_text: str) -> Optional[Dict[str, Any]]:
        """解析 LLM 返回的 JSON 试题"""
        try:
            # 尝试提取 JSON 块
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析
                json_str = response_text
            
            return json.loads(json_str)
        except Exception as e:
            print(f"⚠️ JSON 解析失败: {e}")
            return None
    
    def _generate_default_quiz(
        self, 
        fragments: List[Dict[str, Any]], 
        topic: str
    ) -> Dict[str, Any]:
        """生成默认试题结构"""
        questions = []
        
        for i, frag in enumerate(fragments[:5], 1):
            questions.append({
                "id": i,
                "type": "single",
                "question": f"关于「{frag['title']}」，以下说法正确的是？",
                "options": {
                    "A": "需要立即处理",
                    "B": "可以延后处理",
                    "C": "需要请示上级",
                    "D": "按标准流程处理"
                },
                "correct_answer": "D",
                "explanation": f"应按照标准流程处理。参考：{frag['content'][:100]}...",
                "knowledge_point": frag["category"]
            })
        
        return {
            "quiz_title": f"「{topic}」培训测试",
            "total_questions": len(questions),
            "questions": questions
        }
    
    def _generate_grade_report(self, grade: Dict[str, Any]) -> str:
        """生成批改报告"""
        report_parts = [
            f"# 📊 作业批改报告",
            "",
            f"## 成绩概览",
            f"- **得分**: {grade['score']:.1f} 分",
            f"- **正确数**: {grade['correct_count']} / {grade['total_count']}",
            "",
            "## 题目详情",
            ""
        ]
        
        for r in grade["results"]:
            status = "✅" if r["is_correct"] else "❌"
            report_parts.append(f"### {status} 第 {r['question_id']} 题")
            report_parts.append(f"**题目**: {r['question']}")
            report_parts.append(f"- 您的答案: {r['user_answer'] or '未作答'}")
            report_parts.append(f"- 正确答案: {r['correct_answer']}")
            
            if not r["is_correct"]:
                report_parts.append(f"- **解析**: {r['explanation']}")
                report_parts.append(f"- **知识点**: {r['knowledge_point']}")
            
            report_parts.append("")
        
        report_parts.extend([
            "---",
            "",
            "💡 **学习建议**: 如需查看针对性的培训课件，请输入「生成课件」或点击下方按钮。"
        ])
        
        return "\n".join(report_parts)


# ===================== 测试入口 =====================
if __name__ == "__main__":
    async def test():
        agent = TrainingAgent()
        
        async def print_callback(msg_type: str, action: str, data: dict):
            print(f"[{msg_type}] {action}: {json.dumps(data, ensure_ascii=False, indent=2)[:300]}")
        
        # 测试生成试题
        print("=" * 50)
        print("测试1: 生成试题")
        print("=" * 50)
        
        quiz = await agent.generate_quiz("轴承故障处置", None, print_callback)
        print(f"\n生成的试题: {quiz.get('quiz_title')}")
        print(f"题目数量: {len(quiz.get('questions', []))}")
        
        # 测试批改
        print("\n" + "=" * 50)
        print("测试2: 批改作业")
        print("=" * 50)
        
        # 模拟用户答案
        answers = {
            "1": "A",
            "2": "B",
            "3": "D",
            "4": "C",
            "5": "D"
        }
        
        grade = await agent.grade_answers(answers, None, print_callback)
        print(f"\n得分: {grade['score']:.1f}")
        
        # 测试生成课件
        print("\n" + "=" * 50)
        print("测试3: 生成课件")
        print("=" * 50)
        
        courseware = await agent.generate_courseware(None, print_callback)
        print(f"\n课件生成完成，长度: {len(courseware)} 字符")
    
    asyncio.run(test())
