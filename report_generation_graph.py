#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
import os
from typing import Annotated
from typing_extensions import TypedDict
from dotenv import load_dotenv
import json

from langgraph_helper import common_llm

load_dotenv()


# 定义状态类型
class State(TypedDict):
    """对话状态，使用add_messages自动处理消息列表更新"""
    messages: Annotated[list, add_messages]


# ==================== 模块1：模板选择工具 ====================

@tool
def template_selection(content: str) -> str:
    """
    模板选择工具，根据分析结果选择最合适的报告模板
    
    Args:
        content: 输入的分析结果和报告要求描述
        
    Returns:
        str: 模板选择结果的JSON字符串
    """
    print("template_selection工具被调用")
    result = {
        "selected_template": "defect_analysis_report",
        "template_sections": [
            "执行摘要",
            "检测概况",
            "缺陷详情",
            "风险分析",
            "可视化结果",
            "维护建议",
            "附录"
        ],
        "style_config": {
            "emphasis_level": "medium",
            "visualization_density": "high",
            "technical_depth": "detailed"
        },
        "rationale": "选择缺陷分析报告模板，因为检测到多个缺陷且风险等级为中等，需要详细的技术分析和维护建议"
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


# ==================== 模块2：文本生成工具 ====================

@tool
def text_generation(content: str) -> str:
    """
    文本生成工具，将结构化分析数据转化为专业的自然语言描述
    
    Args:
        content: 输入的模板结构和分析数据描述
        
    Returns:
        str: 文本生成结果的JSON字符串
    """
    print("text_generation工具被调用")
    result = {
        "report_text": {
            "executive_summary": "本次对3号线路K25+300区段的螺栓专项检测发现2处螺栓松动缺陷，其中1处为高风险缺陷。建议立即对高风险螺栓进行检查维护，并在1周内完成所有缺陷处理。",
            "inspection_overview": "检测于2024年1月20日进行，覆盖轨道、螺栓、垫片等关键部件。采用高精度视觉分析算法，检测置信度91%，区域覆盖率95%。",
            "defect_details": "1. 螺栓Bolt_15：位置(1250,880)，松动程度中等，检测置信度92%。\n2. 螺栓Bolt_22：位置(1340,920)，松动程度高，检测置信度88%。",
            "technical_analysis": "螺栓松动主要基于角度偏移和振动特征分析。Bolt_22显示12.5度偏移，超出安全阈值5度，振动水平0.23，表明急需维护。"
        },
        "text_quality": {
            "readability_score": 0.87,
            "technical_accuracy": 0.95,
            "completeness": 0.92
        }
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


# ==================== 模块3：可视化工具 ====================

@tool
def defect_annotation(content: str) -> str:
    """
    缺陷标注工具，在原图上标注缺陷位置和类型
    
    Args:
        content: 输入的原始图像和缺陷位置信息
        
    Returns:
        str: 缺陷标注结果的JSON字符串
    """
    print("defect_annotation工具被调用")
    result = {
        "annotated_image": "标注后的图像数据(模拟)",
        "legend": {
            "high_risk_color": "红色",
            "medium_risk_color": "橙色",
            "normal_color": "绿色"
        },
        "image_metadata": {
            "resolution": "1920x1080",
            "format": "PNG",
            "file_size": "2.3MB"
        }
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def statistical_charts(content: str) -> str:
    """
    统计图表生成工具，创建缺陷分布和趋势图表
    
    Args:
        content: 输入的统计数据和图表配置
        
    Returns:
        str: 统计图表结果的JSON字符串
    """
    print("statistical_charts工具被调用")
    result = {
        "charts": {
            "defect_pie_chart": "缺陷分布饼图(模拟)",
            "severity_bar_chart": "风险等级柱状图(模拟)",
            "trend_line_chart": "历史趋势折线图(模拟)"
        },
        "chart_descriptions": {
            "defect_pie_chart": "显示所有检测到的缺陷类型分布",
            "severity_bar_chart": "按风险等级分类的缺陷数量",
            "trend_line_chart": "近三个月缺陷数量变化趋势"
        }
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def risk_heatmap(content: str) -> str:
    """
    风险热力图生成工具，显示区域风险等级分布
    
    Args:
        content: 输入的风险数据和区域信息
        
    Returns:
        str: 风险热力图结果的JSON字符串
    """
    print("risk_heatmap工具被调用")
    result = {
        "heatmap_image": "风险热力图(模拟)",
        "risk_zones": {
            "high_risk_areas": ["K25+300-K25+320"],
            "medium_risk_areas": ["K25+280-K25+300"],
            "low_risk_areas": ["K25+320-K25+350"]
        },
        "color_scale": {
            "high": "#FF0000",
            "medium": "#FFA500",
            "low": "#00FF00"
        }
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


# ==================== 模块4：预警和建议工具 ====================

@tool
def alert_generation(content: str) -> str:
    """
    预警生成工具，基于风险等级生成预警信息
    
    Args:
        content: 输入的风险数据和缺陷详情
        
    Returns:
        str: 预警信息的JSON字符串
    """
    print("alert_generation工具被调用")
    result = {
        "alerts": {
            "high_priority_alert": {
                "title": "高风险螺栓松动预警",
                "content": "螺栓Bolt_22出现严重松动，需立即处理",
                "recipients": ["维护主管", "技术负责人"],
                "urgency": "immediate"
            },
            "medium_priority_alert": {
                "title": "中等风险缺陷通知",
                "content": "发现1处中等风险螺栓松动",
                "recipients": ["维护团队"],
                "urgency": "within_week"
            }
        },
        "alert_metadata": {
            "total_alerts": 2,
            "highest_priority": "immediate",
            "notification_channels": ["email", "sms", "system_notification"]
        }
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def maintenance_recommendation(content: str) -> str:
    """
    维护建议工具，生成具体的维护计划和资源预估
    
    Args:
        content: 输入的风险评估和历史数据
        
    Returns:
        str: 维护建议的JSON字符串
    """
    print("maintenance_recommendation工具被调用")
    result = {
        "maintenance_recommendations": {
            "immediate_actions": [
                {
                    "action": "检查并紧固螺栓Bolt_22",
                    "timeframe": "24小时内",
                    "team": "紧急维修组",
                    "estimated_duration": "2小时"
                }
            ],
            "scheduled_actions": [
                {
                    "action": "全面检查K25+300区段所有螺栓",
                    "timeframe": "1周内",
                    "team": "日常维护组",
                    "estimated_duration": "4小时"
                }
            ],
            "preventive_measures": [
                "增加该区段的巡检频率至每两周一次",
                "考虑使用防松螺栓替换普通螺栓"
            ]
        },
        "resource_estimation": {
            "manpower": {"紧急维修": "2人", "日常维护": "3人"},
            "materials": ["螺栓M24×100", "垫片", "防松胶"],
            "total_cost_estimate": "￥1,200"
        }
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


# ==================== 模块5：报告格式化工具 ====================

@tool
def report_formatting(content: str) -> str:
    """
    报告格式化工具，将所有内容整合为最终格式化的报告
    
    Args:
        content: 输入的所有报告内容和格式配置
        
    Returns:
        str: 格式化报告的JSON字符串
    """
    print("report_formatting工具被调用")
    result = {
        "formatted_report": {
            "pdf_document": {
                "file_path": "/reports/轨道巡检_3号线_K25+300_20240120.pdf",
                "page_count": 12,
                "file_size": "5.7MB",
                "sections": [
                    {"name": "封面", "page": 1},
                    {"name": "执行摘要", "page": 2},
                    {"name": "检测结果", "page": 3},
                    {"name": "缺陷分析", "page": 4},
                    {"name": "可视化结果", "page": 6},
                    {"name": "维护建议", "page": 9},
                    {"name": "附录", "page": 11}
                ]
            },
            "html_version": {
                "file_path": "/reports/轨道巡检_3号线_K25+300_20240120.html",
                "interactive_elements": ["可缩放图像", "筛选表格"],
                "mobile_friendly": True
            },
            "report_metadata": {
                "report_id": "TRACK_INSP_20240120_001",
                "version": "1.0",
                "generation_date": "2024-01-20 14:30:00",
                "author": "智能巡检系统"
            }
        },
        "quality_check": {
            "formatting_consistency": 0.94,
            "accessibility_score": 0.88,
            "professional_appearance": 0.91
        }
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


def create_report_generation_graph():
    """
    创建报告生成子图，包含5个模块：模板选择、文本生成、可视化制作、预警建议、报告格式化
    
    Returns:
        编译后的langgraph子图
    """
    base_url = os.getenv('OPENAI_BASE_URL')
    api_key = "123"

    if not api_key:
        raise ValueError("请设置OPENAI_API_KEY环境变量: report_generation_graph.py")

    # 创建LLM实例
    llm = ChatOpenAI(
        base_url=base_url,
        api_key=api_key,
        temperature=0.7,
        max_tokens=2000
    )

    # 创建状态图
    graph = StateGraph(State)
    
    # 创建5个Agent节点
    template_selection_agent = create_react_agent(
        llm,
        [template_selection],
        prompt="""你是报告模板选择专家，负责根据分析结果选择最合适的报告模板。
        
        任务：
        1. 分析任务类型：螺栓检测、综合巡检、紧急排查等
        2. 评估风险等级：低风险、中等风险、高风险、紧急
        3. 考虑受众需求：技术人员、管理人员、维护团队
        4. 选择合适模板并配置样式
        
        每次分析都需要调用template_selection工具，不能仅凭经验回答。
        你的回答应以"模板选择："开头。"""
    )
    
    text_generation_agent = create_react_agent(
        llm,
        [text_generation],
        prompt="""你是报告文本生成专家，负责将结构化数据转化为专业的自然语言描述。
        
        任务：
        1. 生成执行摘要：简明扼要总结关键发现
        2. 编写检测概况：描述检测范围、方法、结果
        3. 描述缺陷详情：详细说明每个缺陷的情况
        4. 提供技术分析：专业的技术说明
        
        每次分析都需要调用text_generation工具，不能仅凭经验回答。
        你的回答应以"文本生成："开头。"""
    )
    
    visualization_agent = create_react_agent(
        llm,
        [defect_annotation, statistical_charts, risk_heatmap],
        prompt="""你是可视化内容制作专家，负责创建清晰、信息丰富的可视化内容。
        
        任务：
        1. 缺陷标注：在原图上标注缺陷位置和类型（调用defect_annotation工具）
        2. 统计图表：展示缺陷分布、历史趋势等（调用statistical_charts工具）
        3. 风险热力图：显示区域风险等级分布（调用risk_heatmap工具）
        
        每次分析都需要依次调用这3个工具，不能仅凭经验回答。
        你的回答应以"可视化制作："开头。"""
    )
    
    alert_recommendation_agent = create_react_agent(
        llm,
        [alert_generation, maintenance_recommendation],
        prompt="""你是预警和建议专家，负责生成预警信息和具体的维护建议。
        
        任务：
        1. 预警生成：根据风险程度设置预警等级（调用alert_generation工具）
        2. 维护建议：提供可操作的技术建议和资源预估（调用maintenance_recommendation工具）
        
        每次分析都需要依次调用这2个工具，不能仅凭经验回答。
        你的回答应以"预警建议："开头。"""
    )
    
    report_formatting_agent = create_react_agent(
        llm,
        [report_formatting],
        prompt="""你是报告格式化专家，负责将所有内容整合为最终格式化的报告。
        
        任务：
        1. 整合所有内容：文本、可视化、预警建议
        2. 格式化排版：确保结构完整、格式统一
        3. 生成多格式输出：PDF、HTML等格式
        4. 添加元数据：报告编号、版本等信息
        
        每次分析都需要调用report_formatting工具，不能仅凭经验回答。
        你的回答应以"报告格式化："开头。"""
    )
    
    # 创建工具节点
    template_selection_tools = ToolNode([template_selection])
    text_generation_tools = ToolNode([text_generation])
    visualization_tools = ToolNode([defect_annotation, statistical_charts, risk_heatmap])
    alert_recommendation_tools = ToolNode([alert_generation, maintenance_recommendation])
    report_formatting_tools = ToolNode([report_formatting])
    
    # 创建最终总结节点
    final_summary_agent = common_llm(
        prompt="""你是报告生成总结专家，负责整合所有模块的结果并生成最终的报告摘要。
        
        你需要：
        1. 综合5个模块的输出结果
        2. 生成完整的报告生成执行摘要
        3. 确保所有关键信息完整
        
        最终输出格式应为：
        {
          "agent": "report_generation",
          "execution_summary": {
            "processing_time": "...",
            "modules_completed": 5,
            "report_pages": ...,
            "visual_elements": ...,
            "status": "success"
          },
          "final_report": {
            "main_document": {...},
            "supplementary_files": {...},
            "report_content_overview": {...}
          },
          "distribution_info": {...},
          "quality_assessment": {...}
        }
        
        你的回答应以"报告生成总结："开头。"""
    )
    
    # 添加Agent节点和工具节点
    graph.add_node("模板选择Agent", template_selection_agent,
                   metadata={"description": "模板选择专家，根据任务类型和风险等级选择合适的报告模板"})
    graph.add_node("模板选择工具", template_selection_tools,
                   metadata={"description": "执行模板选择工具"})
    
    graph.add_node("文本生成Agent", text_generation_agent,
                   metadata={"description": "文本生成专家，将结构化数据转化为自然语言描述"})
    graph.add_node("文本生成工具", text_generation_tools,
                   metadata={"description": "执行文本生成工具"})
    
    graph.add_node("可视化制作Agent", visualization_agent,
                   metadata={"description": "可视化专家，创建缺陷标注、统计图表和风险热力图"})
    graph.add_node("可视化制作工具", visualization_tools,
                   metadata={"description": "执行可视化制作工具"})
    
    graph.add_node("预警建议Agent", alert_recommendation_agent,
                   metadata={"description": "预警建议专家，生成预警信息和维护建议"})
    graph.add_node("预警建议工具", alert_recommendation_tools,
                   metadata={"description": "执行预警生成和维护建议工具"})
    
    graph.add_node("报告格式化Agent", report_formatting_agent,
                   metadata={"description": "格式化专家，整合所有内容生成最终报告"})
    graph.add_node("报告格式化工具", report_formatting_tools,
                   metadata={"description": "执行报告格式化工具"})
    
    graph.add_node("报告生成总结节点", final_summary_agent,
                   metadata={"description": "整合所有模块结果，生成完整的报告生成摘要"})
    
    # 添加边：线性流程
    graph.add_edge(START, "模板选择Agent")
    graph.add_edge("模板选择Agent", "模板选择工具")
    graph.add_edge("模板选择工具", "文本生成Agent")
    graph.add_edge("文本生成Agent", "文本生成工具")
    graph.add_edge("文本生成工具", "可视化制作Agent")
    graph.add_edge("可视化制作Agent", "可视化制作工具")
    graph.add_edge("可视化制作工具", "预警建议Agent")
    graph.add_edge("预警建议Agent", "预警建议工具")
    graph.add_edge("预警建议工具", "报告格式化Agent")
    graph.add_edge("报告格式化Agent", "报告格式化工具")
    graph.add_edge("报告格式化工具", "报告生成总结节点")
    graph.add_edge("报告生成总结节点", END)
    
    return graph.compile()


# 创建全局图实例
report_generation_subgraph = create_report_generation_graph()

