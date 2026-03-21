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


def create_planning_strategy_graph():
    """
    创建规划与策略子图，包含4个节点：策略规划、工具选择、工作流编排、质量控制
    
    Returns:
        编译后的langgraph子图
    """
    base_url = os.getenv("OPENAI_BASE_URL")
    api_key = os.getenv("OPENAI_API_KEY")
    model_name = os.getenv("OPENAI_MODEL")

    if not api_key:
        raise ValueError("请设置OPENAI_API_KEY环境变量: planning_strategy_graph.py")

    # 创建LLM实例
    llm = ChatOpenAI(
        base_url=base_url,  # Ollama API 地址
        api_key=api_key,  # 任意字符串，Ollama 不需要真实密钥
        model=model_name,  # Ollama 中的模型名称
        temperature=0.7,
        max_tokens=1000
    )

    # 创建状态图
    graph = StateGraph(State)

    # 创建4个agent节点
    strategy_planning_agent = common_llm(
        prompt="""
            作为轨道交通巡检的策略规划专家，请基于任务需求制定最优执行策略。
            
            分析维度：
            1. 检测策略选择：[全面检测, 重点检测, 抽样检测, 快速筛查]
               - 考虑因素：风险等级、历史问题、任务紧急度
            2. 资源分配：
               - 计算优先级：[low, medium, high, critical]
               - 数据源需求：[实时视频, 历史图像, 音频数据, 传感器数据]
               - 传感器配置：根据检测目标选择合适传感器
            3. 风险评估：
               - 总体风险等级
               - 重点关注的区域/部件
               - 备用方案
            4. 执行约束：
               - 时间限制、精度要求、覆盖范围
            
            输出格式参考：策略规划模块：<json>
            {
                "detection_strategy": "comprehensive_inspection",
                "resource_allocation": {
                    "computing_priority": "high",
                    "data_sources": ["real_time_video", "historical_images", "audio_data"],
                    "sensor_configuration": ["high_resolution_camera", "acoustic_sensor"]
                },
                "risk_assessment": {
                    "overall_risk": "medium",
                    "critical_areas": ["bolt_15", "bolt_22"],
                    "fallback_plan": "manual_verification"
                },
                "constraints": {
                    "time_limit": "30_minutes",
                    "accuracy_requirement": ">95%",
                    "coverage_requirement": "100%_area"
                }
            }
            </json>
        """
    )

    tool_selection_agent = common_llm(
        prompt="""
            基于策略规划和任务需求，为数据分析与洞察Agent选择合适的工具集。
            
            选择标准：
            1. 数据预处理工具：根据数据质量选择增强和提取工具
            2. 检测分析工具：根据检测目标选择专用算法
            3. 结果验证工具：确保结果可靠性的验证方法
            
            工具选择考虑：
            - 任务匹配度：工具功能与检测需求的匹配程度
            - 性能要求：处理速度与精度的平衡
            - 版本兼容性：工具版本间的兼容性
            - 参数配置：根据具体场景调整工具参数
            
            输出格式参考：工具选择模块：<json>
            {
                "selected_tools": {
                    "data_preprocessing": [
                        {
                            "tool_name": "image_enhancement",
                            "version": "v2.1",
                            "parameters": {"contrast_ratio": 1.5, "brightness_adjust": 0.8}
                        },
                        {
                            "tool_name": "roi_extraction", 
                            "version": "v1.3",
                            "parameters": {"roi_size": [1024, 768], "overlap_ratio": 0.1}
                        }
                    ],
                    "detection_analysis": [
                        {
                            "tool_name": "component_segmentation",
                            "version": "v3.2", 
                            "parameters": {"model_type": "high_precision", "confidence_threshold": 0.8}
                        },
                        {
                            "tool_name": "bolt_detection",
                            "version": "v2.5",
                            "parameters": {"detection_mode": "precise", "min_bolt_size": 20}
                        },
                        {
                            "tool_name": "looseness_analysis",
                            "version": "v1.8",
                            "parameters": {"angle_threshold": 5, "vibration_threshold": 0.15}
                        }
                    ],
                    "result_validation": [
                        {
                            "tool_name": "confidence_calculation",
                            "version": "v1.2",
                            "parameters": {"weight_visual": 0.7, "weight_audio": 0.3}
                        },
                        {
                            "tool_name": "cross_validation",
                            "version": "v1.0",
                            "parameters": {"validation_method": "multi_modal"}
                        }
                    ]
                },
                "tool_dependencies": {
                    "bolt_detection": ["component_segmentation"],
                    "looseness_analysis": ["bolt_detection"],
                    "cross_validation": ["bolt_detection", "looseness_analysis"]
                }
            }
            </json>
        """
    )

    workflow_orchestration_agent = common_llm(
        prompt="""
            作为工作流编排专家，请设计最优的任务执行流程。
            
            编排要求：
            1. 阶段划分：将任务合理划分为数据准备、检测分析、结果验证等阶段
            2. 执行模式：确定每个阶段的串行/并行执行方式
            3. 依赖关系：明确阶段间和工具间的依赖关系
            4. 数据流设计：定义输入源、中间结果和最终输出
            
            特殊考虑：
            - 错误处理：配置重试机制和备用工具
            - 超时设置：为每个阶段设定合理的时间限制
            - 资源优化：平衡计算资源和使用效率
            
            输出格式参考：工作流编排模块：<json>
            {
                "workflow_stages": [
                    {
                        "stage_name": "data_preparation",
                        "sequence": 1,
                        "tools": ["image_enhancement", "roi_extraction"],
                        "execution_mode": "sequential",
                        "output_to": ["detection_analysis"]
                    },
                    {
                        "stage_name": "detection_analysis", 
                        "sequence": 2,
                        "tools": ["component_segmentation", "bolt_detection", "looseness_analysis"],
                        "execution_mode": "parallel",
                        "dependencies": ["data_preparation"],
                        "output_to": ["result_validation"]
                    },
                    {
                        "stage_name": "result_validation",
                        "sequence": 3,
                        "tools": ["confidence_calculation", "cross_validation"],
                        "execution_mode": "sequential", 
                        "dependencies": ["detection_analysis"],
                        "output_to": ["final_output"]
                    }
                ],
                "data_flow": {
                    "input_sources": ["real_time_camera", "historical_database"],
                    "intermediate_results": [
                        "enhanced_images",
                        "roi_regions", 
                        "segmented_components",
                        "detected_bolts",
                        "looseness_metrics"
                    ],
                    "final_outputs": ["validated_results", "quality_report"]
                },
                "error_handling": {
                    "retry_attempts": 3,
                    "fallback_tools": {
                        "bolt_detection": "manual_annotation",
                        "looseness_analysis": "basic_vibration_analysis"
                    },
                    "timeout_settings": {
                        "data_preparation": "5_minutes",
                        "detection_analysis": "15_minutes", 
                        "result_validation": "5_minutes"
                    }
                }
            }
            </json>
        """
    )

    quality_control_agent = common_llm(
        prompt="""
            基于行业标准和任务要求，制定严格的质量控制方案。
            
            质量控制维度：
            1. 质量标准设定：
               - 检测精度目标值和最低可接受值
               - 处理时间要求
               - 覆盖范围要求
            2. 质量检查点设计：
               - 每个阶段的关键质量指标
               - 质量阈值设定
               - 不合格处理措施
            3. 质量监控机制：
               - 实时报警触发条件
               - 质量报告格式和内容
               - 自动化程度设置
            
            参考标准：
            - 轨道交通检测行业标准
            - 安全检测规范
            - 历史最佳实践
            
            输出格式参考：质量控制模块：<json>
            {
                "quality_standards": {
                    "detection_accuracy": {
                        "target": 0.95,
                        "minimum_acceptable": 0.85,
                        "measurement_method": "precision_recall"
                    },
                    "processing_time": {
                        "target": "20_minutes",
                        "maximum_allowed": "30_minutes", 
                        "measurement_method": "end_to_end_timing"
                    },
                    "coverage_requirement": {
                        "target": "100%",
                        "minimum_acceptable": "95%",
                        "measurement_method": "area_coverage_calculation"
                    }
                },
                "quality_checkpoints": [
                    {
                        "checkpoint_name": "image_quality_check",
                        "stage": "data_preparation",
                        "metrics": ["contrast_ratio", "brightness_level", "noise_ratio"],
                        "thresholds": {"contrast_ratio": ">1.2", "noise_ratio": "<0.05"},
                        "action_if_failed": "reprocess_image"
                    },
                    {
                        "checkpoint_name": "detection_confidence_check", 
                        "stage": "detection_analysis",
                        "metrics": ["detection_confidence", "segmentation_accuracy"],
                        "thresholds": {"detection_confidence": ">0.8", "segmentation_accuracy": ">0.9"},
                        "action_if_failed": "manual_verification"
                    },
                    {
                        "checkpoint_name": "final_validation_check",
                        "stage": "result_validation", 
                        "metrics": ["overall_confidence", "cross_validation_score"],
                        "thresholds": {"overall_confidence": ">0.85", "cross_validation_score": ">0.8"},
                        "action_if_failed": "extended_analysis"
                    }
                ],
                "quality_monitoring": {
                    "real_time_alerts": ["low_confidence", "timeout_warning", "coverage_below_target"],
                    "quality_report_format": {
                        "sections": ["executive_summary", "detailed_metrics", "anomaly_log", "recommendations"],
                        "format": "pdf",
                        "automation_level": "full"
                    }
                }
            }
            </json>
        """
    )

    # 添加节点
    graph.add_node("策略规划节点", strategy_planning_agent,
                   metadata={"description": "分析任务复杂度和紧急程度，确定检测策略，制定资源分配方案，评估任务风险和执行约束"})
    graph.add_node("工具选择节点", tool_selection_agent,
                   metadata={"description": "根据任务类型选择合适算法工具，配置工具参数和版本，建立工具间的依赖关系"})
    graph.add_node("工作流编排节点", workflow_orchestration_agent,
                   metadata={"description": "定义任务执行顺序和依赖关系，设定并行和串行执行节点，配置数据流和错误处理机制"})
    graph.add_node("质量控制节点", quality_control_agent,
                   metadata={"description": "根据行业标准设定质量阈值，配置质量检查点和验收标准，设计质量监控和报警机制"})

    # 添加线性拓扑关系：1->2->3->4
    graph.add_edge(START, "策略规划节点")
    graph.add_edge("策略规划节点", "工具选择节点")
    graph.add_edge("工具选择节点", "工作流编排节点")
    graph.add_edge("工作流编排节点", "质量控制节点")
    graph.add_edge("质量控制节点", END)

    return graph.compile()


# 创建全局图实例
planning_strategy_subgraph = create_planning_strategy_graph()
