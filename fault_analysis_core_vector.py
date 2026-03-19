#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
故障分析核心模块（纯向量库版）
与 fault_analysis_core 相同的 LangGraph 流程，但 RAG 仅使用向量数据库文档检索（无知识图谱）。
- 通过 WebSocket 实时推送分析进度和结果
- 支持同步和异步执行
- 每次 RAG 检索结果会格式化输出到控制台并明确标记
"""
import os
import json
import re
import asyncio
from datetime import datetime
from typing import Annotated, List, Dict, Any, Optional, Callable, Awaitable
from typing_extensions import TypedDict
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
import logging

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages

load_dotenv()

# 使用与 fault_analysis_core 一致的消息类型与数据结构（便于 backend 复用）
from fault_analysis_core import (
    WSMessageTypes,
    NodeProgressData,
    ThinkingStepData,
    FinalReportData,
    AnalysisResult,
)

# 本模块状态与 fault_analysis_core.State 结构一致
class State(TypedDict):
    messages: Annotated[list, add_messages]
    defect_input: Dict[str, Any]
    retrieval_result: str
    extraction_result: Dict[str, Any]
    fault_analysis_result: Dict[str, Any]
    maintenance_plan_result: Dict[str, Any]
    thinking_processes: List[str]
    query_entities: List[str]
    is_info_sufficient: bool
    supplementary_queries: List[str]
    retry_count: int
    max_retry: int


# ===================== 全局变量 =====================
_vector_retriever = None
_llm = None
_is_initialized = False
_ws_callback: Optional[Callable[[str, str, dict], Awaitable[None]]] = None
_thinking_step_counter = 0


def set_ws_callback(callback: Optional[Callable[[str, str, dict], Awaitable[None]]]):
    global _ws_callback
    _ws_callback = callback


def get_ws_callback():
    return _ws_callback


async def _send_ws_message(action: str, data: dict):
    if _ws_callback:
        try:
            await _ws_callback("analysis", action, data)
        except Exception as e:
            print(f"⚠️ WebSocket 消息发送失败: {e}")


async def _send_thinking_step(node_name: str, title: str, content: str):
    global _thinking_step_counter
    _thinking_step_counter += 1
    step_data = ThinkingStepData(step_index=_thinking_step_counter, node_name=node_name, title=title, content=content)
    await _send_ws_message(WSMessageTypes.THINKING_STEP, step_data.to_dict())


async def _send_node_progress(node_name: str, node_index: int, status: str, message: str, input_summary: str = "", output_summary: str = "", duration: float = 0):
    progress_data = NodeProgressData(node_name=node_name, node_index=node_index, status=status, message=message, input_summary=input_summary, output_summary=output_summary, duration=duration)
    action = WSMessageTypes.NODE_START if status == "running" else WSMessageTypes.NODE_COMPLETE
    await _send_ws_message(action, progress_data.to_dict())


# ===================== RAG 检索结果美化输出（这里涉及 RAG） =====================
def _print_rag_retrieval(query: str, documents: List[Any], source: str = "向量文档检索") -> None:
    """将 RAG 检索到的文档格式化打印到控制台。"""
    sep = "=" * 60
    print("\n" + sep)
    print(f"  [RAG] {source}")
    print(sep)
    print(f"  检索 query: {query}")
    print(f"  命中文档数: {len(documents)}")
    print("-" * 60)
    for i, doc in enumerate(documents, 1):
        content = doc.page_content if hasattr(doc, "page_content") else str(doc)
        meta = doc.metadata if hasattr(doc, "metadata") else {}
        source_path = meta.get("source", meta.get("filename", "未知"))
        preview = (content[:300] + "…") if len(content) > 300 else content
        print(f"  【文档 {i}】")
        print(f"    来源: {source_path}")
        print(f"    内容预览: {preview}")
        print()
    print(sep + "\n")


# ===================== 初始化（向量库） =====================
def initialize(
    openai_base_url: str = None,
    openai_api_key: str = None,
    openai_model: str = None,
    vector_db_dir: str = None,
) -> bool:
    """初始化故障分析模块（纯向量库）。这里涉及 RAG：初始化向量检索器。"""
    global _vector_retriever, _llm, _is_initialized

    from rag_config import VECTOR_DB_DIR, VECTOR_COLLECTION_NAME

    openai_base_url = openai_base_url or os.getenv("OPENAI_BASE_URL")
    openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
    openai_model = openai_model or os.getenv("OPENAI_MODEL", "gpt-4")
    persist_dir = vector_db_dir or VECTOR_DB_DIR

    print("🔌 正在初始化 LLM...")
    try:
        _llm = ChatOpenAI(base_url=openai_base_url, api_key=openai_api_key, temperature=0, model=openai_model)
        print("✅ LLM 初始化成功！")
    except Exception as e:
        print(f"❌ LLM 初始化失败: {e}")
        return False

    print("🔌 正在连接向量数据库（Chroma）...")
    try:
        from langchain_community.vectorstores import Chroma
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from rag_config import EMBEDDING_MODEL_NAME

        print("使用本地嵌入模型（sentence-transformers，无需代理）: %s" % EMBEDDING_MODEL_NAME)
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        _vector_retriever = Chroma(
            persist_directory=persist_dir,
            embedding_function=embeddings,
            collection_name=VECTOR_COLLECTION_NAME,
        ).as_retriever(search_kwargs={"k": 8})
        print("✅ 向量检索器初始化成功！")
    except Exception as e:
        print(f"⚠️ 向量检索器初始化失败: {e}")
        _vector_retriever = None

    _is_initialized = True
    return True


def clean_json_output(raw_output: str) -> str:
    """清理 LLM 返回的 JSON 字符串，去除 markdown 代码块等格式"""
    if not isinstance(raw_output, str):
        raise TypeError("输入必须为字符串类型")
    cleaned = raw_output.strip()
    
    # 去除 markdown 代码块标记
    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'```\s*$', '', cleaned)
    
    # 尝试提取 JSON 对象（处理 LLM 可能返回的额外文字）
    json_match = re.search(r'\{[\s\S]*\}', cleaned)
    if json_match:
        cleaned = json_match.group()
    
    # 清理常见 JSON 格式问题
    cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)  # 移除尾随逗号
    cleaned = re.sub(r'(?<!\\)\'', '"', cleaned)  # 单引号转双引号
    
    try:
        json.loads(cleaned)
        return cleaned
    except json.JSONDecodeError as e:
        print(f"⚠️ [clean_json_output] JSON 解析失败: {e}")
        print(f"⚠️ [clean_json_output] 原始内容: {raw_output[:300]}...")
        # 返回原始清理后的内容，让上层处理
        raise ValueError(f"无法解析 JSON: {e}")


def format_confidence(confidence: Any) -> str:
    try:
        conf_value = float(confidence)
        if conf_value <= 1.0:
            conf_value = conf_value * 100
        return f"{conf_value:.1f}%"
    except (ValueError, TypeError):
        return "0%"


# ===================== RAG：纯文档检索（这里涉及 RAG） =====================
def document_retriever(question: str) -> str:
    """基于问题的向量文档检索。这里涉及 RAG（文档检索）。"""
    if _vector_retriever is None:
        return "【模拟数据】未连接向量数据库，返回模拟检索结果。"

    try:
        docs = _vector_retriever.invoke(question)
        # RAG：检索到的文档输出到控制台（美化）
        _print_rag_retrieval(question, docs, source="向量数据库文档检索（RAG）")
        return "\n\n#Document\n".join([d.page_content for d in docs]) if docs else "未找到相关文档"
    except Exception as e:
        print(f"⚠️ 向量检索失败: {e}")
        return "向量检索异常，请检查向量库与嵌入服务。"


# ===================== LangGraph 节点定义 =====================
def retrieval_node(state: State) -> State:
    """数据检索节点。这里涉及 RAG：仅执行向量文档检索（结果会输出到控制台）。"""
    defect_input = state["defect_input"]
    supplementary_queries = state.get("supplementary_queries", [])
    retry_count = state.get("retry_count", 0)

    if supplementary_queries and retry_count > 0:
        query = " ".join(supplementary_queries)
        node_prefix = f"数据检索节点（补充检索{retry_count}次）"
    else:
        part_name = defect_input.get("part_name", "轴承")
        defect_type = defect_input.get("defect_type", "温度异常")
        query = f"{part_name}的{defect_type}相关巡检记录、故障原因、维修方案和部件规格是什么？"
        node_prefix = "数据检索节点（初始检索）"
        state["query_entities"] = [part_name, defect_type, defect_input.get("part_position", "")]

    state["thinking_processes"].append({
        "node": node_prefix,
        "title": "开始执行 RAG 文档检索（向量库）",
        "content": f"检索目标：{query}\n检索范围：向量数据库文档"
    })

    # 这里涉及 RAG：执行文档检索（结果在 document_retriever 内已输出到控制台）
    raw_data = document_retriever(query)

    state["thinking_processes"].append({
        "node": node_prefix,
        "title": "文档检索完成",
        "content": f"检索结果长度：{len(raw_data)} 字符\n开始 LLM 整理检索结果..."
    })

    retrieval_prompt = f"""
    你是轨道运输巡检数据专家，擅长整理电客车故障文本信息。请仔细阅读输入信息，以简洁的语言进行重述，总结出其中的关键信息。
    输入信息为：
    检索问题：{query}
    文档检索结果：{raw_data}（文本中"#Document"为分隔符，需合并所有文本片段提取信息）
    """
    system_prompt = SystemMessage(content=retrieval_prompt)
    try:
        response = _llm.invoke([system_prompt])
        response_content = response.content
    except Exception as e:
        print(f"⚠️ [数据检索节点] LLM 调用失败: {e}")
        response_content = raw_data[:2000] if len(raw_data) > 2000 else raw_data

    if retry_count > 0 and state.get("retrieval_result"):
        state["retrieval_result"] = f"{state['retrieval_result']}\n\n【补充检索{retry_count}次结果】：{response_content}"
    else:
        state["retrieval_result"] = response_content

    state["retry_count"] = retry_count + 1
    state["thinking_processes"].append({
        "node": node_prefix,
        "title": "检索结果整理完成",
        "content": f"整理后结果长度：{len(state['retrieval_result'])} 字符"
    })
    return state


def extraction_node(state: State) -> State:
    """信息提取节点。这里涉及 RAG：使用的 retrieval_result 为上游 RAG 文档检索并整理后的内容。"""
    retrieval_result = state["retrieval_result"]
    defect_input = state["defect_input"]

    state["thinking_processes"].append({
        "node": "信息提取节点",
        "title": "开始凝练核心信息",
        "content": f"输入：检索结果 ({len(retrieval_result)} 字符)\n目标：提取核心故障现象、关键部件信息、时间序列、环境参数、维护要点"
    })

    extraction_prompt = f"""
        你是轨道运输巡检数据专家，擅长整理电客车故障文本信息。
        当前巡检结果为：{defect_input}
        往年巡检记录中，与该结果相关的故障文本内容为：{retrieval_result}
        请凝练以下检索结果为结构化JSON，仅返回JSON：
        输出结构：
        {{
            "core_fault_phenomenon": [],
            "key_part_info": [],
            "time_series": [],
            "critical_env_params": [],
            "maintenance_key_points": []
        }}
    """
    system_prompt = SystemMessage(content=extraction_prompt)
    response = None
    try:
        response = _llm.invoke([system_prompt])
        print(f"📊 [信息提取节点] LLM 返回: {response.content[:500]}...")
        json_data = clean_json_output(response.content)
        print(f"📊 [信息提取节点] 清理后 JSON: {json_data[:500]}...")
        extraction_result = json.loads(json_data)
        print(f"✅ [信息提取节点] 解析成功: {list(extraction_result.keys())}")
        
        # 验证必要字段存在
        if not extraction_result.get('core_fault_phenomenon'):
            extraction_result['core_fault_phenomenon'] = ['无具体故障现象']
        if not extraction_result.get('maintenance_key_points'):
            extraction_result['maintenance_key_points'] = ['无历史维护记录']
            
    except Exception as e:
        print(f"❌ [信息提取节点] 处理失败: {e}")
        if response:
            print(f"❌ [信息提取节点] 原始返回: {response.content[:500]}...")
        extraction_result = {
            "core_fault_phenomenon": ["基于检索内容无法提取具体故障现象"],
            "key_part_info": ["无"],
            "time_series": ["无"],
            "critical_env_params": ["无"],
            "maintenance_key_points": ["基于检索内容无法提取历史维护要点"]
        }
    state["extraction_result"] = extraction_result
    if response is not None:
        state["messages"].append(response)
    return state


def fault_analysis_node(state: State) -> State:
    """故障分析节点"""
    defect_input = state["defect_input"]
    extraction_result = state["extraction_result"]
    fault_prompt = f"""
        请分析{defect_input.get('part_name')}{defect_input.get('defect_type')}的故障原因和风险，返回JSON：
        提取结果：{json.dumps(extraction_result, ensure_ascii=False)}
        输出结构：
        {{
            "potential_causes": [{{"原因": "", "置信度": 0, "关联依据": ""}}],
            "risk_assessment": [{{"risk_level": "", "expected_fault_time": "", "impact_scope": ""}}]
        }}
        注意：置信度应为 0-100 之间的整数。
    """
    response = None
    try:
        response = _llm.invoke([SystemMessage(content=fault_prompt)])
        print(f"📊 [故障分析节点] LLM 返回: {response.content[:500]}...")
        json_data = clean_json_output(response.content)
        print(f"📊 [故障分析节点] 清理后 JSON: {json_data[:500]}...")
        fault_analysis_result = json.loads(json_data)
        print(f"✅ [故障分析节点] 解析成功: {list(fault_analysis_result.keys())}")
        
        # 验证必要字段存在
        if not fault_analysis_result.get('potential_causes'):
            fault_analysis_result['potential_causes'] = [
                {"原因": f"{defect_input.get('defect_type')}可能原因待分析", "置信度": 50, "关联依据": "需要更多数据"}
            ]
        if not fault_analysis_result.get('risk_assessment'):
            fault_analysis_result['risk_assessment'] = [
                {"risk_level": "中", "expected_fault_time": "待评估", "impact_scope": "待评估"}
            ]
            
    except Exception as e:
        print(f"❌ [故障分析节点] 处理失败: {e}")
        if response:
            print(f"❌ [故障分析节点] 原始返回: {response.content[:500]}...")
        fault_analysis_result = {
            "potential_causes": [
                {"原因": f"{defect_input.get('defect_type')}（自动生成）", "置信度": 50, "关联依据": "基于通用部件特性分析，详细原因需人工判断"}
            ],
            "risk_assessment": [
                {"risk_level": "中", "expected_fault_time": "未来7天内", "impact_scope": "局部设备可能受影响"}
            ]
        }
    state["fault_analysis_result"] = fault_analysis_result
    return state


def reflection_node(state: State) -> State:
    """信息充足性反思节点"""
    defect_input = state["defect_input"]
    extraction_result = state["extraction_result"]
    fault_analysis_result = state["fault_analysis_result"]
    retry_count = state["retry_count"]
    max_retry = state["max_retry"]

    reflection_prompt = f"""
    你是轨道运输巡检领域的资深专家，请严格评估当前信息是否足够生成详细、可执行的{defect_input.get('part_name')}{defect_input.get('defect_type')}维护方案。
    当前已有信息：
    - 核心提取结果：{json.dumps(extraction_result, ensure_ascii=False)}
    - 故障分析结果：{json.dumps(fault_analysis_result, ensure_ascii=False)}
    - 检索结果摘要：{state.get('retrieval_result', '无')[:500]}...

    请严格按照以下JSON格式返回评估结果：
    {{
        "is_info_sufficient": true/false,
        "insufficient_reasons": ["原因1", "原因2"],
        "supplementary_queries": ["补充查询1", "补充查询2"]
    }}
    补充查询数量控制在1-2个；若已达最大重试次数，即使信息不足也返回true。
    """
    try:
        response = _llm.invoke([SystemMessage(content=reflection_prompt)])
        reflection_result = json.loads(clean_json_output(response.content))
        state["is_info_sufficient"] = reflection_result.get("is_info_sufficient", False)
        state["supplementary_queries"] = reflection_result.get("supplementary_queries", [])
    except Exception:
        if retry_count < max_retry:
            state["is_info_sufficient"] = False
            state["supplementary_queries"] = [f"{defect_input.get('part_name')}{defect_input.get('defect_type')} 详细维护案例"]
        else:
            state["is_info_sufficient"] = True
    return state


def maintenance_node(state: State) -> State:
    """维护方案生成节点"""
    defect_input = state["defect_input"]
    extraction_result = state["extraction_result"]
    fault_analysis_result = state["fault_analysis_result"]
    maintenance_prompt = f"""
        请为{defect_input.get('part_name')}{defect_input.get('defect_type')}生成维护方案，返回JSON：
        提取结果：{json.dumps(extraction_result, ensure_ascii=False)}
        故障分析：{json.dumps(fault_analysis_result, ensure_ascii=False)}
        输出结构：
        {{
            "suggested_maintenance_time": "",
            "spare_parts_list": [{{"备件名称": "", "型号": "", "quantity": 0, "specs": ""}}],
            "maintenance_steps": [],
            "fault_summary": "",
            "risk_reminder": ""
        }}
    """
    try:
        response = _llm.invoke([SystemMessage(content=maintenance_prompt)])
        maintenance_plan_result = json.loads(clean_json_output(response.content))
    except Exception:
        part_name = defect_input.get("part_name", "未知部件")
        maintenance_plan_result = {
            "suggested_maintenance_time": "立即检查",
            "spare_parts_list": [{"备件名称": part_name, "型号": "通用型号", "quantity": 1, "specs": "通用规格"}],
            "maintenance_steps": [f"1. 停机检查{part_name}状态", "2. 更换损坏部件", "3. 测试设备运行"],
            "fault_summary": f"{part_name}{defect_input.get('defect_type', '异常')}",
            "risk_reminder": "建议优先现场人工检测"
        }
    state["maintenance_plan_result"] = maintenance_plan_result
    return state


def generate_final_report(state: State) -> str:
    """生成最终分析报告（与 fault_analysis_core 格式一致，数据来源改为向量库）。"""
    defect_input = state["defect_input"]
    extraction_result = state.get("extraction_result", {})
    fault_analysis_result = state.get("fault_analysis_result", {})
    maintenance_plan_result = state.get("maintenance_plan_result", {})
    retry_count = state.get("retry_count", 1) - 1
    
    # 调试日志
    print(f"\n{'='*60}")
    print(f"📝 [报告生成] 开始生成最终报告")
    print(f"📝 [报告生成] extraction_result keys: {list(extraction_result.keys())}")
    print(f"📝 [报告生成] core_fault_phenomenon: {extraction_result.get('core_fault_phenomenon', [])}")
    print(f"📝 [报告生成] maintenance_key_points: {extraction_result.get('maintenance_key_points', [])}")
    print(f"📝 [报告生成] fault_analysis_result keys: {list(fault_analysis_result.keys())}")
    print(f"📝 [报告生成] potential_causes: {fault_analysis_result.get('potential_causes', [])}")
    print(f"📝 [报告生成] risk_assessment: {fault_analysis_result.get('risk_assessment', [])}")
    print(f"{'='*60}\n")

    report = f"""# 轨道巡检故障分析报告

## 一、故障基本信息

| 项目 | 内容 |
|------|------|
| 检测时间 | {defect_input.get('detect_time', '未知')} |
| 部件名称 | {defect_input.get('part_name', '未知')} |
| 部件位置 | {defect_input.get('part_position', '未知')} |
| 缺陷类型 | {defect_input.get('defect_type', '未知')} |
| 检测置信度 | {defect_input.get('detect_confidence', 0.0):.0%} |
| 检索次数 | 初始检索 + 补充检索{retry_count}次 |

## 二、核心信息提取

### 2.1 核心故障现象
"""
    core_phenomena = extraction_result.get('core_fault_phenomenon', [])
    if not core_phenomena or core_phenomena == ['无']:
        report += "暂无数据\n"
    else:
        for i, phen in enumerate(core_phenomena, 1):
            if phen and phen != '无':
                report += f"{i}. {phen}\n"
    
    report += "\n### 2.2 历史维护要点\n"
    maintenance_points = extraction_result.get('maintenance_key_points', [])
    if not maintenance_points or maintenance_points == ['无']:
        report += "暂无数据\n"
    else:
        for i, point in enumerate(maintenance_points, 1):
            if point and point != '无':
                report += f"{i}. {point}\n"
    
    report += "\n## 三、故障分析与风险评估\n\n### 3.1 潜在故障原因\n"
    potential_causes = fault_analysis_result.get('potential_causes', [])
    if not potential_causes:
        report += "暂无数据\n"
    else:
        for i, cause in enumerate(potential_causes, 1):
            report += f"\n#### 原因{i}\n- 具体原因：{cause.get('原因', '未知')}\n- 置信度：{format_confidence(cause.get('置信度', 0))}\n- 关联依据：{cause.get('关联依据', '无')}\n"
    
    report += "\n### 3.2 风险评估\n"
    risk_assessment = fault_analysis_result.get('risk_assessment', [])
    if not risk_assessment:
        report += "暂无数据\n"
    else:
        report += "\n| 风险等级 | 预计故障时间 | 影响范围 |\n|----------|--------------|----------|\n"
        for risk in risk_assessment:
            report += f"| {risk.get('risk_level', '未知')} | {risk.get('expected_fault_time', '未知')} | {risk.get('impact_scope', '未知')} |\n"
    report += f"""
## 四、维护方案建议

### 4.1 建议维护时间
{maintenance_plan_result.get('suggested_maintenance_time', '立即维护')}

### 4.2 所需备件清单
"""
    for part in maintenance_plan_result.get('spare_parts_list', []):
        report += f"| {part.get('备件名称', '未知')} | {part.get('型号', '未知')} | {part.get('quantity', 0)} | {part.get('specs', '未知')} |\n"
    report += "\n### 4.3 维护执行步骤\n"
    for step in maintenance_plan_result.get('maintenance_steps', []):
        report += f"{step}\n"
    report += f"""
### 4.4 故障总结与风险提示

#### 故障总结
{maintenance_plan_result.get('fault_summary', '无')}

#### 风险提示
{maintenance_plan_result.get('risk_reminder', '无')}

---
*报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*数据来源：向量数据库文档检索（RAG）（共检索{retry_count + 1}次）*
"""
    return report


def _create_fault_analysis_graph():
    graph = StateGraph(State)
    graph.add_node("数据检索节点", retrieval_node)
    graph.add_node("信息提取节点", extraction_node)
    graph.add_node("故障分析节点", fault_analysis_node)
    graph.add_node("信息充足性反思", reflection_node)
    graph.add_node("维护方案生成节点", maintenance_node)

    def should_retrieve_more(state: State) -> str:
        if not state["is_info_sufficient"] and state["retry_count"] < state["max_retry"]:
            return "数据检索节点"
        return "维护方案生成节点"

    graph.add_edge(START, "数据检索节点")
    graph.add_edge("数据检索节点", "信息提取节点")
    graph.add_edge("信息提取节点", "故障分析节点")
    graph.add_edge("故障分析节点", "信息充足性反思")
    graph.add_conditional_edges("信息充足性反思", should_retrieve_more, {"数据检索节点": "数据检索节点", "维护方案生成节点": "维护方案生成节点"})
    graph.add_edge("维护方案生成节点", END)
    return graph.compile()


_fault_analysis_graph = None


def _get_graph():
    global _fault_analysis_graph
    if _fault_analysis_graph is None:
        _fault_analysis_graph = _create_fault_analysis_graph()
    return _fault_analysis_graph


def run_fault_analysis(
    detect_time: str = "",
    part_name: str = "",
    part_position: str = "",
    defect_type: str = "",
    detect_confidence: float = 0.95,
    max_retry: int = 3
) -> AnalysisResult:
    if not _is_initialized:
        initialize()
    defect_input = {
        "detect_time": detect_time or datetime.now().strftime("%Y-%m-%d %H:%M"),
        "part_name": part_name or "未知部件",
        "part_position": part_position or "未知位置",
        "defect_type": defect_type or "未知缺陷",
        "detect_confidence": detect_confidence
    }
    initial_state: State = {
        "messages": [HumanMessage(content="请分析轨道巡检的故障并生成维护方案")],
        "defect_input": defect_input,
        "retrieval_result": "",
        "extraction_result": {},
        "fault_analysis_result": {},
        "maintenance_plan_result": {},
        "thinking_processes": [],
        "query_entities": [],
        "is_info_sufficient": False,
        "supplementary_queries": [],
        "retry_count": 0,
        "max_retry": max_retry
    }
    result = _get_graph().invoke(initial_state)
    final_report = generate_final_report(result)
    return AnalysisResult(
        defect_input=result["defect_input"],
        retrieval_result=result["retrieval_result"],
        extraction_result=result["extraction_result"],
        fault_analysis_result=result["fault_analysis_result"],
        maintenance_plan_result=result["maintenance_plan_result"],
        thinking_processes=result["thinking_processes"],
        final_report=final_report,
        retry_count=result["retry_count"]
    )


async def run_fault_analysis_async(
    detect_time: str = "",
    part_name: str = "",
    part_position: str = "",
    defect_type: str = "",
    detect_confidence: float = 0.95,
    max_retry: int = 3,
    ws_callback: Optional[Callable[[str, str, dict], Awaitable[None]]] = None
) -> AnalysisResult:
    global _thinking_step_counter
    _thinking_step_counter = 0
    set_ws_callback(ws_callback)
    start_time = datetime.now()

    if not _is_initialized:
        initialize()

    defect_input = {
        "detect_time": detect_time or datetime.now().strftime("%Y-%m-%d %H:%M"),
        "part_name": part_name or "未知部件",
        "part_position": part_position or "未知位置",
        "defect_type": defect_type or "未知缺陷",
        "detect_confidence": detect_confidence
    }

    await _send_ws_message(WSMessageTypes.ANALYSIS_START, {
        "message": "开始故障分析（向量库 RAG）",
        "defect_input": defect_input,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_nodes": 5
    })

    initial_state: State = {
        "messages": [HumanMessage(content="请分析轨道巡检的故障并生成维护方案")],
        "defect_input": defect_input,
        "retrieval_result": "",
        "extraction_result": {},
        "fault_analysis_result": {},
        "maintenance_plan_result": {},
        "thinking_processes": [],
        "query_entities": [],
        "is_info_sufficient": False,
        "supplementary_queries": [],
        "retry_count": 0,
        "max_retry": max_retry
    }

    node_name_map = {"数据检索节点": 1, "信息提取节点": 2, "故障分析节点": 3, "信息充足性反思": 4, "维护方案生成节点": 5}
    graph = _get_graph()
    result = None
    last_thinking_count = 0

    async for chunk in graph.astream(initial_state):
        for node_name, node_output in chunk.items():
            node_index = node_name_map.get(node_name, 0)
            await _send_node_progress(node_name=node_name, node_index=node_index, status="running", message=f"正在执行 {node_name}...")
            if isinstance(node_output, dict) and "thinking_processes" in node_output:
                thinking_processes = node_output["thinking_processes"]
                for i in range(last_thinking_count, len(thinking_processes)):
                    step = thinking_processes[i]
                    if isinstance(step, dict):
                        await _send_thinking_step(step.get("node", node_name), step.get("title", "执行中"), step.get("content", ""))
                last_thinking_count = len(thinking_processes)
            await _send_node_progress(node_name=node_name, node_index=node_index, status="completed", message=f"{node_name} 执行完成")
            result = node_output if isinstance(node_output, dict) else result

    if result is None:
        result = initial_state
    final_report = generate_final_report(result)
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    await _send_ws_message(WSMessageTypes.FINAL_REPORT, FinalReportData(
        defect_input=result.get("defect_input", defect_input),
        extraction_result=result.get("extraction_result", {}),
        fault_analysis_result=result.get("fault_analysis_result", {}),
        maintenance_plan_result=result.get("maintenance_plan_result", {}),
        report_markdown=final_report,
        retry_count=result.get("retry_count", 0),
        total_duration=duration
    ).to_dict())
    await _send_ws_message(WSMessageTypes.ANALYSIS_COMPLETE, {"message": "故障分析完成", "duration": duration, "retry_count": result.get("retry_count", 0), "thinking_steps": _thinking_step_counter})

    return AnalysisResult(
        defect_input=result.get("defect_input", defect_input),
        retrieval_result=result.get("retrieval_result", ""),
        extraction_result=result.get("extraction_result", {}),
        fault_analysis_result=result.get("fault_analysis_result", {}),
        maintenance_plan_result=result.get("maintenance_plan_result", {}),
        thinking_processes=result.get("thinking_processes", []),
        final_report=final_report,
        retry_count=result.get("retry_count", 0)
    )
