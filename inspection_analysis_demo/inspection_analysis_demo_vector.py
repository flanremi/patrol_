#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
轨道巡检故障分析 Demo（纯向量库 RAG 版）
与 inspection_analysis_demo 界面与流程一致，但 RAG 仅使用向量数据库文档检索（无知识图谱）。
- 这里涉及 RAG：检索与展示均基于向量库文档检索结果。
"""
import os
import sys
import json

# 确保项目根目录在 path 中，以便导入 fault_analysis_core_vector
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# 使用纯向量库故障分析核心（这里涉及 RAG：本 Demo 基于向量文档检索）
from fault_analysis_core_vector import (
    initialize,
    run_fault_analysis,
)

# -------------------------- Streamlit 界面 --------------------------
def main():
    st.set_page_config(
        page_title="轨道巡检故障分析系统（向量库 RAG）",
        page_icon="📄",
        layout="wide"
    )
    st.title("📄 轨道巡检故障分析系统（向量库 RAG）")
    st.caption("RAG 接入方案：纯向量数据库文档检索（无知识图谱）")

    st.subheader("🔍 缺陷信息录入")
    input_cols = st.columns(5)
    with input_cols[0]:
        detect_time = st.text_input("检测时间", value="2025-11-23 10:30")
    with input_cols[1]:
        part_name = st.text_input("部件名称", value="辅助逆变器")
    with input_cols[2]:
        part_position = st.text_input("部件位置", value="0116车")
    with input_cols[3]:
        defect_type = st.text_input("缺陷类型", value="显黄")
    with input_cols[4]:
        detect_confidence = st.number_input("检测置信度", min_value=0.0, max_value=1.0, value=0.95, step=0.01)

    run_analysis = st.button("🚀 执行故障分析", type="primary")

    defect_input = {
        "detect_time": detect_time,
        "part_name": part_name,
        "part_position": part_position,
        "defect_type": defect_type,
        "detect_confidence": detect_confidence
    }

    main_col1, main_col2 = st.columns([0.5, 0.5])

    with main_col1:
        st.subheader("📊 向量库说明")
        st.info("""
        **这里涉及 RAG**
        - 本方案使用 **向量数据库文档检索**，不使用知识图谱。
        - 文档来自项目 `doc/` 目录，经分块与向量化后写入 Chroma。
        - 每次检索会从向量库中召回相关文档片段，并在控制台输出检索到的文档。
        """)

    with main_col2:
        st.subheader("📋 智能分析过程与结果")
        if not run_analysis:
            st.info("""
            ### 等待分析执行
            1. 请填写上方缺陷信息
            2. 点击「执行故障分析」按钮
            3. 系统将自动完成：
               - **RAG 文档检索**（向量库）
               - 核心信息提取与故障分析
               - 反思信息充足性，不足则自动补充检索（最多 3 次）
               - 生成维护方案与最终报告
            """)
        else:
            if not initialize():
                st.error("故障分析模块初始化失败，请检查向量数据库与 LLM 配置。")
            else:
                with st.spinner("🤖 智能体正在执行分析（RAG 文档检索）..."):
                    result = run_fault_analysis(
                        detect_time=detect_time,
                        part_name=part_name,
                        part_position=part_position,
                        defect_type=defect_type,
                        detect_confidence=detect_confidence,
                        max_retry=3,
                    )

                # 展示思考过程（这里涉及 RAG：部分步骤为 RAG 检索与整理）
                st.markdown("### 🤔 智能体思考过程")
                thinking_container = st.container(border=True)
                with thinking_container:
                    for i, process in enumerate(result.thinking_processes, 1):
                        if isinstance(process, dict):
                            node = process.get("node", "")
                            title = process.get("title", "")
                            content = process.get("content", "")
                            st.markdown(f"**步骤 {i} [{node}] {title}**")
                            st.text(content)
                        else:
                            st.markdown(f"**步骤 {i}：{process}**")
                        st.divider()

                st.markdown("### 📝 各节点输出详情")
                with st.expander("1. 数据检索节点输出（RAG 文档检索结果）", expanded=False):
                    st.text_area("检索结果", result.retrieval_result, height=200)

                with st.expander("2. 信息提取节点输出", expanded=False):
                    st.json(result.extraction_result, expanded=False)

                with st.expander("3. 故障分析与风险评估节点输出", expanded=False):
                    st.json(result.fault_analysis_result, expanded=False)

                with st.expander("4. 信息充足性反思输出", expanded=False):
                    st.json({
                        "重试次数": result.retry_count
                    }, expanded=False)

                with st.expander("5. 维护方案生成节点输出", expanded=False):
                    st.json(result.maintenance_plan_result, expanded=False)

                st.markdown("### 📄 最终故障分析报告")
                report_container = st.container(border=True)
                with report_container:
                    st.markdown(result.final_report)

                export_col1, export_col2 = st.columns(2)
                with export_col1:
                    st.download_button(
                        label="📥 下载报告",
                        data=result.final_report,
                        file_name=f"轨道巡检故障分析报告_向量RAG_{datetime.now().strftime('%Y%m%d%H%M%S')}.md",
                        mime="text/markdown",
                    )
                with export_col2:
                    if st.button("💾 保存完整数据"):
                        full_data = {
                            "报告生成时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "缺陷输入信息": defect_input,
                            "检索次数": result.retry_count,
                            "各节点输出": {
                                "检索结果": result.retrieval_result,
                                "提取结果": result.extraction_result,
                                "故障分析": result.fault_analysis_result,
                                "维护方案": result.maintenance_plan_result
                            },
                            "智能体思考过程": result.thinking_processes,
                            "最终报告": result.final_report
                        }
                        path = f"轨道巡检完整分析数据_向量RAG_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
                        with open(path, "w", encoding="utf-8") as f:
                            json.dump(full_data, f, ensure_ascii=False, indent=2)
                        st.success(f"已保存: {path}")


if __name__ == "__main__":
    main()
