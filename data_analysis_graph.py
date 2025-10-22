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


# ==================== 数据预处理工具定义 ====================

@tool
def image_enhancement(content: str) -> str:
    """
    图像增强工具，对原始图像进行对比度、亮度调整和降噪处理
    
    Args:
        content: 输入的原始图像数据描述
        
    Returns:
        str: 图像增强结果的JSON字符串
    """
    print("image_enhancement工具被调用")
    result = {
        "enhanced_image": "增强后的图像数据(模拟)",
        "quality_metrics": {
            "contrast_score": 0.85,
            "brightness_score": 0.78,
            "noise_ratio": 0.02
        },
        "status": "success"
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def roi_extraction(content: str) -> str:
    """
    ROI区域提取工具，从增强后的图像中提取感兴趣区域
    
    Args:
        content: 输入的增强图像数据描述
        
    Returns:
        str: ROI提取结果的JSON字符串
    """
    print("roi_extraction工具被调用")
    result = {
        "roi_regions": [
            {
                "region_id": "roi_1",
                "coordinates": [100, 100, 600, 400],
                "image_data": "ROI图像数据(模拟)",
                "component_type": "轨道段"
            },
            {
                "region_id": "roi_2",
                "coordinates": [650, 100, 1150, 400],
                "image_data": "ROI图像数据(模拟)",
                "component_type": "螺栓区域"
            }
        ],
        "coverage_ratio": 0.95,
        "status": "success"
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


# ==================== 检测分析工具定义 ====================

@tool
def component_segmentation(content: str) -> str:
    """
    组件分割工具，识别和分割轨道部件
    
    Args:
        content: 输入的ROI区域数据描述
        
    Returns:
        str: 组件分割结果的JSON字符串
    """
    print("component_segmentation工具被调用")
    result = {
        "segmented_components": [
            {
                "component_id": "comp_1",
                "class": "轨道",
                "mask": "分割掩码(模拟)",
                "confidence": 0.92,
                "bounding_box": [100, 100, 500, 300]
            },
            {
                "component_id": "comp_2",
                "class": "螺栓",
                "mask": "分割掩码(模拟)",
                "confidence": 0.89,
                "bounding_box": [200, 150, 250, 200]
            }
        ],
        "segmentation_accuracy": 0.91,
        "status": "success"
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def bolt_detection(content: str) -> str:
    """
    螺栓检测工具，定位螺栓等关键部件
    
    Args:
        content: 输入的分割组件数据描述
        
    Returns:
        str: 螺栓检测结果的JSON字符串
    """
    print("bolt_detection工具被调用")
    result = {
        "detected_bolts": [
            {
                "bolt_id": "bolt_1",
                "position": [220, 175],
                "size": 25,
                "orientation": 15.2,
                "confidence": 0.94
            },
            {
                "bolt_id": "bolt_2",
                "position": [280, 180],
                "size": 28,
                "orientation": -3.5,
                "confidence": 0.91
            },
            {
                "bolt_id": "bolt_15",
                "position": [520, 220],
                "size": 26,
                "orientation": 12.5,
                "confidence": 0.92
            },
            {
                "bolt_id": "bolt_22",
                "position": [680, 250],
                "size": 27,
                "orientation": 18.3,
                "confidence": 0.88
            }
        ],
        "detection_confidence": 0.93,
        "total_bolts_detected": 24,
        "status": "success"
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def looseness_analysis(content: str) -> str:
    """
    松动分析工具，评估螺栓健康状态和松动程度
    
    Args:
        content: 输入的螺栓检测数据描述
        
    Returns:
        str: 松动分析结果的JSON字符串
    """
    print("looseness_analysis工具被调用")
    result = {
        "bolt_analysis": [
            {
                "bolt_id": "bolt_1",
                "orientation_angle": 2.1,
                "vibration_level": 0.08,
                "looseness_status": "正常",
                "confidence": 0.96
            },
            {
                "bolt_id": "bolt_2",
                "orientation_angle": 1.5,
                "vibration_level": 0.06,
                "looseness_status": "正常",
                "confidence": 0.95
            },
            {
                "bolt_id": "bolt_15",
                "orientation_angle": 12.5,
                "vibration_level": 0.23,
                "looseness_status": "松动",
                "confidence": 0.92
            },
            {
                "bolt_id": "bolt_22",
                "orientation_angle": 18.3,
                "vibration_level": 0.31,
                "looseness_status": "松动",
                "confidence": 0.88
            }
        ],
        "summary": {
            "normal_bolts": 22,
            "loose_bolts": 2,
            "overall_risk": "中等"
        },
        "status": "success"
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


# ==================== 结果验证工具定义 ====================

@tool
def confidence_calculation(content: str) -> str:
    """
    置信度计算工具，计算整体分析结果的置信度
    
    Args:
        content: 输入的分析结果数据描述
        
    Returns:
        str: 置信度计算结果的JSON字符串
    """
    print("confidence_calculation工具被调用")
    result = {
        "confidence_scores": {
            "overall_confidence": 0.91,
            "component_confidence": {
                "segmentation": 0.92,
                "detection": 0.93,
                "analysis": 0.89
            },
            "risk_assessment": "中等风险"
        },
        "validation_passed": True,
        "status": "success"
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def cross_validation(content: str) -> str:
    """
    交叉验证工具，验证分析结果的可靠性
    
    Args:
        content: 输入的主要分析结果描述
        
    Returns:
        str: 交叉验证结果的JSON字符串
    """
    print("cross_validation工具被调用")
    result = {
        "validation_results": {
            "agreement_score": 0.87,
            "inconsistent_findings": [
                {
                    "component": "bolt_22",
                    "primary_result": "松动",
                    "secondary_result": "正常",
                    "resolution": "采用主要结果"
                }
            ],
            "final_validation": "passed"
        },
        "status": "success"
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


def create_data_analysis_graph():
    """
    创建数据分析与洞察子图，包含3个Agent节点和对应的工具节点
    
    Returns:
        编译后的langgraph子图
    """
    base_url = os.getenv('OPENAI_BASE_URL')
    api_key = "123"

    if not api_key:
        raise ValueError("请设置OPENAI_API_KEY环境变量: data_analysis_graph.py")

    # 创建LLM实例
    llm = ChatOpenAI(
        base_url=base_url,
        api_key=api_key,
        temperature=0.7,
        max_tokens=2000
    )

    # 创建状态图
    graph = StateGraph(State)
    
    # 创建3个Agent节点
    data_preprocessing_agent = create_react_agent(
        llm,
        [image_enhancement, roi_extraction],
        prompt="""你是数据预处理专家，负责准备高质量的分析数据。
        
        任务：
        1. 从指定位置获取原始数据
        2. 应用数据增强和预处理技术（调用image_enhancement工具）
        3. 提取感兴趣区域ROI（调用roi_extraction工具）
        4. 确保数据质量符合后续分析要求
        
        每次分析都需要依次调用image_enhancement和roi_extraction工具，不能仅凭经验回答。
        你的回答应以"数据预处理："开头。"""
    )
    
    detection_analysis_agent = create_react_agent(
        llm,
        [component_segmentation, bolt_detection, looseness_analysis],
        prompt="""你是检测分析专家，负责执行具体的缺陷检测和分析算法。
        
        任务：
        1. 组件分割：识别和分割轨道部件（调用component_segmentation工具）
        2. 目标检测：定位螺栓等关键部件（调用bolt_detection工具）
        3. 状态分析：评估部件健康状态（调用looseness_analysis工具）
        
        每次分析都需要依次调用这3个工具，不能仅凭经验回答。
        你的回答应以"检测分析："开头。"""
    )
    
    result_validation_agent = create_react_agent(
        llm,
        [confidence_calculation, cross_validation],
        prompt="""你是结果验证专家，负责整合分析结果并进行质量验证。
        
        任务：
        1. 计算整体置信度（调用confidence_calculation工具）
        2. 交叉验证结果可靠性（调用cross_validation工具）
        3. 生成结构化报告
        4. 质量最终检查
        
        每次分析都需要依次调用confidence_calculation和cross_validation工具，不能仅凭经验回答。
        你的回答应以"结果验证："开头，并生成完整的巡检报告JSON。"""
    )
    
    # 创建工具节点
    data_preprocessing_tools = ToolNode([image_enhancement, roi_extraction])
    detection_analysis_tools = ToolNode([component_segmentation, bolt_detection, looseness_analysis])
    result_validation_tools = ToolNode([confidence_calculation, cross_validation])
    
    # 创建最终总结节点
    final_summary_agent = common_llm(
        prompt="""你是数据分析总结专家，负责整合数据预处理、检测分析和结果验证的所有结果。
        
        你需要：
        1. 综合3个模块的分析结果
        2. 生成完整的巡检报告，包含检测ID、位置、时间、结果详情和质量指标
        3. 确保不遗漏任何关键信息
        
        最终输出格式应为：
        {
          "inspection_id": "...",
          "location": "3号线路K25+300",
          "inspection_time": "...",
          "results": {
            "total_bolts_inspected": 24,
            "loose_bolts": [...],
            "overall_risk_assessment": "...",
            "recommendations": [...]
          },
          "quality_metrics": {
            "processing_time": "...",
            "overall_confidence": ...,
            "coverage": "..."
          }
        }
        
        你的回答应以"数据分析总结："开头。"""
    )
    
    # 添加Agent节点和工具节点
    graph.add_node("数据预处理Agent", data_preprocessing_agent,
                   metadata={"description": "数据预处理专家，负责图像增强和ROI提取"})
    graph.add_node("数据预处理工具", data_preprocessing_tools,
                   metadata={"description": "执行图像增强和ROI提取工具"})
    
    graph.add_node("检测分析Agent", detection_analysis_agent,
                   metadata={"description": "检测分析专家，负责组件分割、螺栓检测和松动分析"})
    graph.add_node("检测分析工具", detection_analysis_tools,
                   metadata={"description": "执行组件分割、螺栓检测和松动分析工具"})
    
    graph.add_node("结果验证Agent", result_validation_agent,
                   metadata={"description": "结果验证专家，负责置信度计算和交叉验证"})
    graph.add_node("结果验证工具", result_validation_tools,
                   metadata={"description": "执行置信度计算和交叉验证工具"})
    
    graph.add_node("数据分析总结节点", final_summary_agent,
                   metadata={"description": "整合所有分析结果，生成完整的巡检报告"})
    
    # 添加边：线性流程
    graph.add_edge(START, "数据预处理Agent")
    graph.add_edge("数据预处理Agent", "数据预处理工具")
    graph.add_edge("数据预处理工具", "检测分析Agent")
    graph.add_edge("检测分析Agent", "检测分析工具")
    graph.add_edge("检测分析工具", "结果验证Agent")
    graph.add_edge("结果验证Agent", "结果验证工具")
    graph.add_edge("结果验证工具", "数据分析总结节点")
    graph.add_edge("数据分析总结节点", END)
    
    return graph.compile()


# 创建全局图实例
data_analysis_subgraph = create_data_analysis_graph()

