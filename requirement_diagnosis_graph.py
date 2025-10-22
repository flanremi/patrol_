#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
import os
from typing import Annotated
from typing_extensions import TypedDict
from dotenv import load_dotenv

from langgraph_helper import common_llm

load_dotenv()


# 定义状态类型
class State(TypedDict):
    """对话状态，使用add_messages自动处理消息列表更新"""
    messages: Annotated[list, add_messages]


task_available_model = ["component_segmentation", "bolt_looseness_detection", "defect_classification"]


def create_requirement_diagnosis_graph():
    """
    创建需求诊断子图，包含5个节点：意图解析、任务划分、区域定位、历史查询、总结节点
    
    Returns:
        编译后的langgraph子图
    """
    base_url = os.getenv('OPENAI_BASE_URL')
    api_key = "123"

    if not api_key:
        raise ValueError("请设置OPENAI_API_KEY环境变量: requirement_diagnosis_graph.py")

    # 创建LLM实例
    llm = ChatOpenAI(
        base_url=base_url,
        api_key=api_key,
        temperature=0.7,
        max_tokens=1000
    )

    # 创建状态图
    graph = StateGraph(State)

    # 创建5个agent节点（不绑定tool node）
    intent_analysis_agent = common_llm(
        prompt="""
            你是一个轨道交通巡检系统的意图分析专家。请分析用户输入的巡检需求，提取以下信息：
            1. 主要意图分类：从[设备状态检查, 故障诊断, 预防性维护, 安全评估, 性能检测]中选择
            2. 次要意图：识别具体的检测目标
            3. 实体提取：
               - 位置信息：线路编号、里程标、具体区域
               - 目标组件：轨道、螺栓、道岔、接触网等
               - 操作类型：检查、诊断、监测、评估
            4. 隐含需求：用户未明确表达但合理的扩展需求
            输出格式参考：意图分析模块： <json>
            {
                "primary_intent": "主要意图分类：从[设备状态检查, 故障诊断, 预防性维护, 安全评估, 性能检测]中选择",
                "secondary_intents": ["识别的具体目标"],
                "extracted_entities": [{
                    "location": "实体位置",
                    "target_components": "目标组件",
                    "operation_type": "操作类型",
                    "urgency_level": "急迫等级，从normal，high，urgent中选择"
                }],
                "implicit_requirements": ["例如,需要量化评估,需要历史对比等等"]
            }
            </json>
        """
    )

    task_decomposition_agent = common_llm(
        prompt=f"""
            基于意图分析结果，将用户需求转化为具体的可执行任务。请完成：
            1. 任务分类：确定主任务类别[螺栓专项检测, 综合巡检, 故障排查, 预防性检查]
            2. 子任务分解：将主任务拆分为具体的检测子任务
            3. 模型映射：为每个子任务分配合适的算法模型，参考算法[{",".join(task_available_model)}]
            4. 质量要求：根据任务设定检测置信度、实时性要求、数据源需求
            5. 约束条件：识别任务执行的特殊要求
            输出格式参考：意图解析模块： <json>
                 {{
                  "task_category": "确定主任务类别",
                  "sub_tasks": [
                    {{"name": "任务1", "model": "component_segmentation", "priority": 1}},
                    {{"name": "任务2", "model": "bolt_looseness_detection", "priority": 2}},
                    {{"name": "任务n...", "model": "defect_classification", "priority": 3}}
                  ],
                  "quality_requirements": {{
                    "detection_confidence": 0.85,
                    "processing_time": "realtime",
                    "data_sources": ["visual", "audio"]
                  }},
                  "constraints": [""]
                  }}
            </json>
        """
    )

    location_standardization_agent = common_llm(
        prompt="""
            你负责将用户描述的位置信息转换为系统标准格式，并提供空间上下文信息。
            处理步骤：
            1. 位置标准化：提取线路编号、里程标，转换为标准格式
            2. 坐标转换：转换为GPS坐标和系统内部坐标
            3. 空间上下文：识别上下游区段、邻近设施、地形特征
            4. 可达性分析：评估巡检难度、推荐巡检方式、安全区域
            请输出完整的位置分析结果。
            输出格式参考：区域定位模块： 
            <json>
             {
                  "standardized_location": {
                    "line_number": "3",
                    "mileage": "K25+300",
                    "coordinate_system": "线路相对坐标系",
                    "gps_coordinates": {"lat": 31.2304, "lng": 121.4737},
                    "facility_id": "TRACK_SEGMENT_3_25300"
                  },
                  "spatial_context": {
                    "upstream_section": "K25+200-K25+300",
                    "downstream_section": "K25+300-K25+400", 
                    "nearby_facilities": ["道岔组25B", "信号机S325"],
                    "terrain_type": "直线段"
                  },
                  "accessibility": {
                    "inspection_difficulty": "中等",
                    "recommended_approach": "轨道巡检车",
                    "safety_zones": ["检修通道A"]
                  }
              }
            
            </json>
        """
    )

    historical_query_agent = common_llm(
        prompt="""
        查询并分析指定位置的历史巡检数据，为当前任务提供决策支持。
        需要获取的信息：
        1. 历史巡检概况：最近检查时间、检查频率、总记录数
        2. 缺陷历史：相关缺陷发生次数、模式、趋势
        3. 维护记录：最近维护时间、类型、更换部件
        4. 风险指标：当前风险等级、趋势方向、关注点
        输出格式参考：历史查询模块：       
        <json>
         {
          "historical_summary": {
            "last_inspection_date": "2024-01-15",
            "inspection_frequency": "每月一次",
            "total_historical_records": 24
          },
          "defect_history": {
            "bolt_related_issues": {
              "total_occurrences": 8,
              "last_occurrence": "2024-01-15",
              "common_patterns": ["螺栓松动", "垫片磨损"],
              "seasonal_trend": "冬季高发"
            }
          },
          "maintenance_records": {
            "last_maintenance": "2024-01-20",
            "maintenance_type": "预防性维护",
            "replaced_components": ["螺栓组25-28"]
          },
          "risk_indicators": {
            "current_risk_level": "中等",
            "trend_direction": "稳定",
            "attention_points": ["螺栓腐蚀倾向", "振动异常历史"]
          }}
        </json>
        """
    )

    summary_agent = common_llm(
        prompt="""
            你是需求诊断总结专家，请根据意图分析，任务划分，区域定位和历史查询4个模块的输出内容，整合成一个总结内容。
            最终输出要求：
                - 结构化JSON数据：包含所有分析维度的完整信息
                - 详细需求描述文本：用自然语言总结诊断结果
            参考输出格式：需求诊断总结：<json>
                            {
              "structured_data": {
                "task_understanding": {
                  "primary_intent": "设备状态检查",
                  "target_components": ["轨道螺栓"],
                  "location": "3号线路K25+300"
                },
                "task_planning": {
                  "main_task": "螺栓专项检测",
                  "sub_tasks": ["螺栓定位", "松动检测", "缺陷分类"],
                  "priority": "high"
                },
                "location_info": {
                  "standardized": "LINE_3_K25+300",
                  "coordinates": {"lat": 31.2304, "lng": 121.4737},
                  "terrain": "直线段"
                },
                "historical_context": {
                  "last_inspection": "2024-01-15",
                  "defect_history": "8次螺栓相关问题",
                  "risk_level": "中等"
                }
              },
              "detailed_description": "具体描述"}
            </json>
        """
    )

    # 添加节点
    graph.add_node("意图解析节点", intent_analysis_agent,
                   metadata={"description": "深度理解用户需求，提取实体和隐含需求，为后续处理提供准确的需求理解基础"})
    graph.add_node("任务划分节点", task_decomposition_agent,
                   metadata={"description": "将需求转化为具体的可执行任务链，确保任务链的逻辑性和完整性"})
    graph.add_node("区域定位节点", location_standardization_agent,
                   metadata={"description": "标准化位置信息，提供空间上下文，为后续分析提供空间维度支持"})
    graph.add_node("历史查询节点", historical_query_agent,
                   metadata={"description": "获取历史数据，评估风险趋势，为决策提供数据支撑"})
    graph.add_node("需求诊断总结节点", summary_agent,
                   metadata={"description": "整合意图解析、任务划分、区域定位和历史查询结果，生成完整的需求诊断报告"})

    # 添加线性拓扑关系：1->2->3->4->5
    graph.add_edge(START, "意图解析节点")
    graph.add_edge("意图解析节点", "任务划分节点")
    graph.add_edge("任务划分节点", "区域定位节点")
    graph.add_edge("区域定位节点", "历史查询节点")
    graph.add_edge("历史查询节点", "需求诊断总结节点")
    graph.add_edge("需求诊断总结节点", END)

    return graph.compile()


# 创建全局图实例
requirement_diagnosis_subgraph = create_requirement_diagnosis_graph()
