#!/usr/bin/env python3
import os
import json
import pickle
import streamlit as st
from pyvis.network import Network
import networkx as nx
from typing import Annotated, List, Dict, Any, Optional
from typing_extensions import TypedDict
from dotenv import load_dotenv
from datetime import datetime, timedelta
from json.decoder import JSONDecodeError
import re

# LangChain/LangGraph 相关
try:
    from langchain_core.pydantic_v1 import BaseModel, Field
except ImportError:
    from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from langchain_neo4j import Neo4jGraph
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_community.vectorstores import Neo4jVector
from langchain_neo4j.vectorstores.neo4j_vector import remove_lucene_chars
import logging
logging.getLogger("neo4j").setLevel(logging.ERROR)


# 配置信息
load_dotenv()
# Neo4j 连接配置
neo4j_uri_raw = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
neo4j_password = os.getenv("NEO4J_PASSWORD", "12345678")

# 处理URI协议：neo4j:// 用于集群路由，单机版应使用 bolt://
# 如果用户提供的是 neo4j://，尝试转换为 bolt://
if neo4j_uri_raw.startswith("neo4j://"):
    # 提取主机和端口
    host_port = neo4j_uri_raw.replace("neo4j://", "")
    neo4j_uri = f"bolt://{host_port}"
    print(f"⚠️  检测到 neo4j:// 协议，已自动转换为 bolt:// ({neo4j_uri})")
    print(f"   提示：单机版Neo4j应使用 bolt:// 协议")
else:
    neo4j_uri = neo4j_uri_raw

print(f"🔌 正在连接 Neo4j...")
print(f"   URI: {neo4j_uri}")
print(f"   用户名: {neo4j_username}")

try:
    graph = Neo4jGraph(
        url=neo4j_uri,
        username=neo4j_username,
        password=neo4j_password
    )
    print(f"✅ Neo4j 连接成功！")
    
    # 检查并创建全文索引（如果不存在）
    print(f"🔍 检查全文索引...")
    try:
        # 检查索引是否存在
        check_index_query = """
        SHOW INDEXES
        YIELD name, type, state, populationPercent
        WHERE name = 'entity' AND type = 'FULLTEXT'
        RETURN count(*) as exists
        """
        result = graph.query(check_index_query)
        index_exists = result[0]['exists'] > 0 if result else False
        
        if not index_exists:
            print(f"📝 创建全文索引 'entity'...")
            # 先检查实体节点的标签和属性
            try:
                check_nodes_query = """
                MATCH (n)
                WHERE n:__Entity__ OR n:Entity OR 'Entity' IN labels(n)
                WITH n LIMIT 1
                RETURN labels(n) as labels, keys(n) as keys
                """
                node_info = graph.query(check_nodes_query)
                
                if node_info:
                    labels = node_info[0].get('labels', [])
                    keys = node_info[0].get('keys', [])
                    print(f"   发现实体节点标签：{labels}")
                    print(f"   发现实体节点属性：{keys}")
                    
                    # 确定用于索引的属性（优先使用id，其次使用name）
                    index_property = 'id' if 'id' in keys else ('name' if 'name' in keys else keys[0] if keys else 'id')
                    entity_label = labels[0] if labels else '__Entity__'
                    
                    # 创建全文索引
                    create_index_query = f"""
                    CREATE FULLTEXT INDEX entity IF NOT EXISTS
                    FOR (n:`{entity_label}`)
                    ON EACH [n.{index_property}]
                    """
                    graph.query(create_index_query)
                    print(f"✅ 全文索引 'entity' 创建成功！")
                    print(f"   索引标签：{entity_label}")
                    print(f"   索引属性：{index_property}")
                else:
                    print(f"⚠️  未找到实体节点，索引将在首次导入数据后创建")
            except Exception as idx_e:
                print(f"⚠️  索引创建失败：{idx_e}")
                print(f"   提示：将在首次查询时使用降级方案，或手动创建索引")
                print(f"   手动创建索引命令：")
                print(f"   CREATE FULLTEXT INDEX entity FOR (n:__Entity__) ON EACH [n.id]")
        else:
            print(f"✅ 全文索引 'entity' 已存在")
    except Exception as idx_check_e:
        print(f"⚠️  索引检查失败：{idx_check_e}")
        print(f"   提示：将在首次查询时使用降级方案")
        
except Exception as e:
    print(f"❌ Neo4j 连接失败：{str(e)}")
    print(f"\n📋 故障排查建议：")
    print(f"   1. 确认Neo4j服务已启动")
    print(f"   2. 检查连接URI是否正确（单机版使用 bolt://127.0.0.1:7687）")
    print(f"   3. 验证用户名和密码是否正确")
    print(f"   4. 检查防火墙是否阻止了7687端口")
    print(f"   5. 查看Neo4j日志文件获取详细错误信息")
    raise
GRAPH_HTML_PATH = "D:\git\patrol_\inspection_analysis_demo\zhongche_kg_visualization.html"
GRAPH_DATA_PATH = "D:\git\patrol_\inspection_analysis_demo\zhongche_graph_documents.pkl"

# LLM模型初始化
base_url = os.getenv("OPENAI_BASE_URL")
api_key = os.getenv("OPENAI_API_KEY")
model_name = os.getenv("OPENAI_MODEL")
llm = ChatOpenAI(
    base_url=base_url,  # Ollama API 地址
    api_key=api_key,  # 任意字符串，Ollama 不需要真实密钥
    model=model_name,  # Ollama 中的模型名称
    temperature=0
)

embeddings = OllamaEmbeddings(
    model="mxbai-embed-large:latest",
    base_url="http://localhost:11434",
)

try:
    vector_index = Neo4jVector.from_existing_graph(
        embeddings,
        url=neo4j_uri,
        username=neo4j_username,
        password=neo4j_password,
        search_type="hybrid",
        node_label="Document",
        text_node_properties=["text"],
        embedding_node_property="embedding"
    )
    print(f"✅ Neo4jVector 初始化成功！")
    vector_retriever = vector_index.as_retriever()
except Exception as e:
    print(f"⚠️  Neo4jVector 初始化失败：{str(e)}")
    print(f"   提示：如果数据库为空，这是正常的。首次运行时会自动创建向量索引。")
    # 创建一个空的retriever，避免后续调用出错
    vector_index = None
    vector_retriever = None

# 知识图谱写入Neo4j
with open(GRAPH_DATA_PATH, "rb") as f:
    graph_documents = pickle.load(f)
    graph.add_graph_documents(
        graph_documents,
        baseEntityLabel=True,
        include_source=True
    )

# -------------------------- 核心函数 --------------------------
def common_llm(prompt: str, node_name: str):
    """生成绑定prompt的LLM调用函数（记录思考过程）"""
    def llm_node(state: dict):
        messages = state["messages"]
        system_prompt = SystemMessage(content=prompt)
        new_messages = [system_prompt] + messages
        
        # 记录思考过程
        thinking_process = f"【{node_name}】正在执行任务...\n"
        thinking_process += f"系统提示：{prompt[:100]}...\n"
        thinking_process += f"输入消息数：{len(messages)}\n"
        
        response = llm.invoke([system_prompt])
        
        thinking_process += f"任务执行完成，生成响应结果"
        state["thinking_processes"].append(thinking_process)
        
        return {"messages": [response]}
    return llm_node

def clean_json_output(raw_output: str) -> str:
    """
    清理大模型输出的JSON字符串，移除非JSON标记、修复格式问题，确保可被json.loads解析
    """
    if not isinstance(raw_output, str):
        raise TypeError("输入必须为字符串类型")
    
    cleaned = raw_output.strip()
    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'```\s*$', '', cleaned)
    cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
    cleaned = re.sub(r'(?<!\\)\'', '"', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).replace(' }', '}').replace(' ]', ']')
    
    try:
        json.loads(cleaned)
        return cleaned
    except json.JSONDecodeError as e:
        try:
            cleaned_encoded = cleaned.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
            json.loads(cleaned_encoded)
            return cleaned_encoded
        except json.JSONDecodeError as e2:
            raise ValueError(
                f"清理后仍无法解析为JSON，原始错误：{str(e)}，编码修复后错误：{str(e2)}\n"
                f"清理后内容：{cleaned}"
            )
   
def generate_full_text_query(input: str) -> str:
    """生成Neo4j全文检索查询"""
    words = [el for el in remove_lucene_chars(input).split() if el]
    if not words:
        return ""
    full_text_query = " AND ".join([f"{word}~2" for word in words])
    return full_text_query.strip()

class Entities(BaseModel):
    names: list[str] = Field(
        ...,
        description="从文本中提取的所有人物、组织或工业部件实体名称列表"
    )

entity_prompt = ChatPromptTemplate.from_messages([
    ("system", "你需要从文本中提取组织和人物、工业部件实体，严格按照指定格式返回结果。"),
    ("human", "使用给定的格式从以下输入中提取信息：{question}"),
])
entity_chain = entity_prompt | llm.with_structured_output(Entities)

def graph_retriever(question: str) -> str:
    """基于问题中的实体，检索Neo4j图谱中的关系。这里涉及RAG（图谱检索）。"""
    result = ""
    try:
        entities = entity_chain.invoke({"question": question})
        for entity in entities.names:
            try:
                # 首先尝试使用全文索引查询
                cypher_query = """
                CALL db.index.fulltext.queryNodes('entity', $query, {limit:2})
                YIELD node,score
                CALL (node) { 
                  WITH node
                  MATCH (node)-[r:!MENTIONS]->(neighbor)
                  RETURN node.id + ' - ' + type(r) + ' -> ' + neighbor.id AS output
                  UNION ALL
                  WITH node
                  MATCH (node)<-[r:!MENTIONS]-(neighbor)
                  RETURN neighbor.id + ' - ' + type(r) + ' -> ' +  node.id AS output
                }
                RETURN output LIMIT 50
                """
                response = graph.query(cypher_query, {"query": generate_full_text_query(entity)})
                result += "\n".join([el['output'] for el in response])
            except Exception as idx_error:
                # 如果全文索引不存在，使用普通查询作为降级方案
                if "no such fulltext schema index" in str(idx_error).lower():
                    print(f"⚠️  全文索引不存在，使用降级查询方案（实体：{entity}）")
                    # 降级查询：直接通过节点属性匹配
                    fallback_query = """
                    MATCH (node)
                    WHERE node.id CONTAINS $entity OR toLower(node.id) CONTAINS toLower($entity)
                    WITH node LIMIT 5
                    OPTIONAL MATCH (node)-[r:!MENTIONS]->(neighbor)
                    WITH node, r, neighbor
                    WHERE r IS NOT NULL
                    RETURN node.id + ' - ' + type(r) + ' -> ' + neighbor.id AS output
                    UNION ALL
                    MATCH (node)
                    WHERE node.id CONTAINS $entity OR toLower(node.id) CONTAINS toLower($entity)
                    WITH node LIMIT 5
                    OPTIONAL MATCH (node)<-[r:!MENTIONS]-(neighbor)
                    WITH node, r, neighbor
                    WHERE r IS NOT NULL
                    RETURN neighbor.id + ' - ' + type(r) + ' -> ' + node.id AS output
                    LIMIT 50
                    """
                    try:
                        response = graph.query(fallback_query, {"entity": entity})
                        result += "\n".join([el['output'] for el in response])
                    except Exception as fallback_error:
                        print(f"⚠️  降级查询也失败（实体：{entity}）：{fallback_error}")
                else:
                    print(f"⚠️  图谱检索异常（实体：{entity}）：{idx_error}")
    except Exception as e:
        print(f"⚠️  实体提取或图谱检索异常：{e}")
    # RAG：将图谱检索结果输出到控制台
    if result:
        print("\n" + "=" * 60 + "\n[RAG] 图谱检索")
        print(f"[RAG] 检索 query: {question}")
        print(f"[RAG] 图谱检索结果长度: {len(result)} 字符")
        print("[RAG] 图谱检索结果内容:\n" + result + "\n" + "=" * 60)
    return result

def full_retriever(question: str):
    """混合检索（图谱+向量）。这里涉及RAG（混合检索）。"""
    # 这里涉及RAG：图谱检索
    graph_data = graph_retriever(question)
    # 这里涉及RAG：向量检索
    if vector_retriever is not None:
        try:
            vector_data = [el.page_content for el in vector_retriever.invoke(question)]
        except Exception as e:
            print(f"⚠️  向量检索失败：{e}")
            vector_data = []
    else:
        vector_data = []
    
    final_data = f"""Graph data:
{graph_data}
vector data:
{"#Document ". join(vector_data)}
    """
    # RAG：将混合检索结果输出到控制台
    print("\n" + "=" * 60 + "\n[RAG] 混合检索（图谱 + 向量）")
    print(f"[RAG] 检索 query: {question}")
    print(f"[RAG] 图谱部分长度: {len(graph_data)} 字符, 向量文档数: {len(vector_data)}")
    print("[RAG] 混合检索结果全文:\n" + final_data + "=" * 60 + "\n")
    return final_data

# -------------------------- 状态类型定义--------------------------
class State(TypedDict):
    messages: Annotated[list, add_messages]
    defect_input: Dict[str, Any] = {}
    retrieval_result: Dict[str, Any] = {}
    extraction_result: Dict[str, Any] = {}
    fault_analysis_result: Dict[str, Any] = {}
    maintenance_plan_result: Dict[str, Any] = {}
    thinking_processes: List[str] = []  # 记录各节点思考过程
    query_entities: List[str] = []  # 记录检索的实体
    is_info_sufficient: bool = False  # 信息是否足够生成维护方案
    supplementary_queries: List[str] = []  # 补充检索的查询列表
    retry_count: int = 0  # 补充检索重试次数
    max_retry: int = 3  # 最大重试次数

# -------------------------- LangGraph节点定义--------------------------
def retrieval_node(state: State) -> State:
    """数据检索节点。这里涉及RAG（本节点执行 GraphRAG 混合检索）。"""
    defect_input = state["defect_input"]
    supplementary_queries = state.get("supplementary_queries", [])
    retry_count = state.get("retry_count", 0)
    
    # 确定检索查询
    if supplementary_queries and retry_count > 0:
        query = " ".join(supplementary_queries)
        node_prefix = f"【数据检索节点（补充检索{retry_count}次）】"
    else:
        part_name = defect_input.get("part_name", "轴承")
        defect_type = defect_input.get("defect_type", "温度异常")
        query = f"{part_name}的{defect_type}相关巡检记录、故障原因、维修方案和部件规格是什么？"
        node_prefix = "【数据检索节点（初始检索）】"
        
        # 记录检索实体（用于图谱高亮）
        query_entities = [part_name, defect_type, defect_input.get("part_position", "")]
        state["query_entities"] = [ent for ent in query_entities if ent]
    
    # 记录思考过程
    thinking_process = f"{node_prefix}\n"
    thinking_process += f"检索目标：{query}\n"
    if state.get("query_entities"):
        thinking_process += f"检索实体：{', '.join(state['query_entities'])}\n"
    thinking_process += f"开始执行GraphRAG混合检索（图谱+向量）..."
    state["thinking_processes"].append(thinking_process)
    
    # 这里涉及RAG：执行混合检索（结果会输出到控制台）
    raw_data = full_retriever(query)
    
    # 记录检索完成状态
    thinking_process = f"{node_prefix}检索完成\n"
    thinking_process += f"检索结果长度：{len(raw_data)}字符\n"
    thinking_process += f"开始整理检索结果..."
    state["thinking_processes"].append(thinking_process)
    
    # 调用LLM整理检索结果
    retrieval_prompt = f"""
    你是轨道运输巡检数据专家，擅长整理电客车故障文本信息。请仔细阅读输入信息，以简洁的语言进行重述，总结出其中的关键信息。
    输入信息为：
    检索问题：{query}
    混合检索结果：{raw_data}（文本中"#Document"为分隔符，需合并所有文本片段提取信息）
    """
    retrieval_agent = common_llm(retrieval_prompt, "数据检索节点")
    response = retrieval_agent(state)
    response_content = response["messages"][0].content
    
    # 补充检索时合并原有结果，初始检索直接覆盖
    if retry_count > 0 and state.get("retrieval_result"):
        state["retrieval_result"] = f"{state['retrieval_result']}\n\n【补充检索{retry_count}次结果】：{response_content}"
    else:
        state["retrieval_result"] = response_content
    
    # 重试次数+1
    state["retry_count"] = retry_count + 1
    
    return state

def extraction_node(state: State) -> State:
    """信息提取节点。输入为上游 RAG 检索整理后的内容。这里涉及RAG（使用 RAG 检索结果）。"""
    # 这里涉及RAG：retrieval_result 来自上游 RAG 混合检索并整理后的内容
    retrieval_result = state["retrieval_result"]
    defect_input = state["defect_input"]
    
    thinking_process = f"【信息提取节点】\n"
    thinking_process += f"输入数据：{'补充检索后' if state['retry_count']>1 else '初始检索后'}的混合检索结果\n"
    thinking_process += f"开始凝练核心信息..."
    state["thinking_processes"].append(thinking_process)
    
    extraction_prompt = f"""
        你是轨道运输巡检数据专家，擅长整理电客车故障文本信息。
        当前巡检结果为：
        {defect_input}
        往年巡检记录中，与该结果相关的故障文本内容为：
        {retrieval_result}
        请凝练以下检索结果为结构化JSON，仅返回JSON：
        输出结构：
        {{
            "core_fault_phenomenon": [],
            "key_part_info": [],
            "time_series": [],
            "critical_env_params": [],
            "maintenance_key_points": []
        }}
        其中，core_fault_phenomenon中填入当前核心故障现象。
        key_part_info中填入与该现象相关的部件名称和信息，包括尺寸、型号等。
        time_series中填入当前核心故障现象相关的时间序列数据，包括故障时间、持续时长等。
        critical_env_params中填入当前核心故障现象相关的环境参数，包括温度、转速、压力等。
        maintenance_key_points中填入当前核心故障现象相关的过往维修思路及维修建议。 

        举例：
        {{
            "core_fault_phenomenon": ["辅助逆变器显黄"],
            "key_part_info": [
                {{"部件名称": "辅助逆变器", "关联部件": "紧急制动接触器EBK、制动缓解继电器ABRR"}},
                {{"部件名称": "紧急制动接触器EBK", "特性": "存在机械卡死可能性，正线卡死无法排除故障需救援"}},
                {{"部件名称": "制动缓解继电器ABRR", "关联电路": "SKS_E113_114（所有制动缓解）电路"}}
            ],
            "time_series": [
                {{"故障时间": "2023-11-20 12:30", "故障现象": "0116车辅助逆变器显黄"}},
                {{"处理时间": "未知", "处理现象": "EBK接触器库内卡死、ABRR继电器未正常得电"}}
            ],
            "critical_env_params": [
                {{"参数名称": "故障列车最高运行速度", "数值": "14公里/小时"}},
                {{"参数名称": "ABRR继电器得电状态", "数值": "未正常得电（远程缓解后可正常得电）"}},
                {{"参数名称": "制动缓解状态", "数值": "常用制动实际已缓解"}}
            ],
            "maintenance_key_points": [
                "重新安装EBK辅助触点，多次测试验证设备正常工作",
                "唤醒电客车通过远程缓解方式，恢复ABRR继电器正常得电状态",
                "检查ABRR继电器相关电路，确认SKS_E113_114电路正常得电",
                "EBK接触器存在机械卡死共性风险，需加强日常巡检频次",
                "EBK正线卡死无现场处理方案，需提前储备应急救援预案"
            ]
        }}
    """

    extraction_agent = common_llm(extraction_prompt, "信息提取节点")
    response = extraction_agent(state)
    
    try:
        json_data = clean_json_output(response["messages"][0].content)
        extraction_result = json.loads(json_data)
        state["thinking_processes"].append(f"【信息提取节点】信息提取完成，成功凝练核心数据")
    except:
        error_msg = "信息提取失败，使用默认结构"
        state["thinking_processes"].append(f"【信息提取节点】{error_msg}")
        extraction_result = {
            "core_fault_phenomenon": ["无"],
            "key_part_info": ["无"],
            "time_series": ["无"],
            "critical_env_params": ["无"],
            "maintenance_key_points": ["无"]
        }
    
    state["extraction_result"] = extraction_result
    state["messages"].extend(response["messages"])
    return state

def fault_analysis_node(state: State) -> State:
    """故障分析节点"""
    defect_input = state["defect_input"]
    extraction_result = state["extraction_result"]
    
    thinking_process = f"【故障分析与风险评估节点】\n"
    thinking_process += f"分析对象：{defect_input.get('part_name')}{defect_input.get('defect_type')}\n"
    thinking_process += f"输入信息：核心故障现象{extraction_result.get('core_fault_phenomenon')}，关键参数{extraction_result.get('critical_env_params')}\n"
    thinking_process += f"开始分析潜在原因和风险等级..."
    state["thinking_processes"].append(thinking_process)
    
    fault_prompt = f"""
        请分析{defect_input.get('part_name')}{defect_input.get('defect_type')}的故障原因和风险，返回JSON：
        提取结果：{json.dumps(extraction_result, ensure_ascii=False)}
        输出结构：
        {{
            "potential_causes": [{{"原因": "", "置信度": 0, "关联依据": ""}}],
            "risk_assessment": [{{"risk_level": "", "expected_fault_time": "", "impact_scope": ""}}]
        }}
    """
    fault_agent = common_llm(fault_prompt, "故障分析与风险评估节点")
    response = fault_agent(state)
    
    try:
        json_data = clean_json_output(response["messages"][0].content)
        fault_analysis_result = json.loads(json_data)
        state["thinking_processes"].append(f"【故障分析与风险评估节点】分析完成，生成{len(fault_analysis_result.get('potential_causes', []))}个潜在原因")
    except:
        error_msg = "故障分析失败，使用默认评估"
        state["thinking_processes"].append(f"【故障分析与风险评估节点】{error_msg}")
        fault_analysis_result = {
            "potential_causes": [{"原因": f"{defect_input.get('defect_type')}", "置信度": 50, "关联依据": "基于通用部件特性分析"}],
            "risk_assessment": [{"risk_level": "中", "expected_fault_time": "未来7天内", "impact_scope": "局部设备异常"}]
        }
    
    state["fault_analysis_result"] = fault_analysis_result
    state["messages"].extend(response["messages"])
    return state

def reflection_node(state: State) -> State:
    """信息充足性反思：判断是否足够生成维护方案，不足则生成补充查询"""
    defect_input = state["defect_input"]
    extraction_result = state["extraction_result"]
    fault_analysis_result = state["fault_analysis_result"]
    retry_count = state["retry_count"]
    max_retry = state["max_retry"]
    
    # 记录思考过程
    thinking_process = f"【信息充足性反思】\n"
    thinking_process += f"评估维度：核心故障现象完整性、关键参数覆盖度、故障原因充分性、历史维护案例充足性\n"
    thinking_process += f"开始评估信息是否足够生成维护方案..."
    state["thinking_processes"].append(thinking_process)
    
    # 构造反思Prompt
    reflection_prompt = f"""
    你是轨道运输巡检领域的资深专家，请严格评估当前信息是否足够生成详细、可执行的{defect_input.get('part_name')}{defect_input.get('defect_type')}维护方案。
    评估标准（需全部满足才判定为充足）：
    1. 核心故障现象明确且具体（非泛泛而谈）；
    2. 关键运行参数（温度、转速、压力等）覆盖故障相关维度；
    3. 潜在故障原因至少2个，且每个原因有明确关联依据；
    4. 包含至少1条历史维护案例或同类故障处理经验；
    5. 包含部件规格、备件信息等可执行维护的基础数据。

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

    注意：
    1. 补充查询需精准、可执行，能直接补充缺失信息（例如："辅助逆变器显黄的历史维护案例及备件型号"）；
    2. 补充查询数量控制在1-2个；
    3. 若已达最大重试次数，即使信息不足也返回true。
    """
    
    # 调用LLM进行反思评估
    reflection_agent = common_llm(reflection_prompt, "信息充足性反思")
    response = reflection_agent(state)
    
    try:
        json_data = clean_json_output(response["messages"][0].content)
        reflection_result = json.loads(json_data)
        
        # 更新状态
        state["is_info_sufficient"] = reflection_result.get("is_info_sufficient", False)
        state["supplementary_queries"] = reflection_result.get("supplementary_queries", [])
        
        # 记录评估结果
        if state["is_info_sufficient"]:
            thinking_process = f"【信息充足性反思】评估完成：信息足够生成维护方案\n"
            thinking_process += f"评估结论：满足维护方案生成的核心信息要求"
        else:
            thinking_process = f"【信息充足性反思】评估完成：信息不足\n"
            thinking_process += f"不足原因：{', '.join(reflection_result.get('insufficient_reasons', []))}\n"
            thinking_process += f"补充查询：{', '.join(state['supplementary_queries'])}"
        state["thinking_processes"].append(thinking_process)
        
    except Exception as e:
        # 容错逻辑：未达重试上限则判定为不足，否则判定为充足
        error_msg = f"反思评估解析失败（{str(e)}），触发容错逻辑"
        state["thinking_processes"].append(f"【信息充足性反思】{error_msg}")
        if retry_count < max_retry:
            state["is_info_sufficient"] = False
            state["supplementary_queries"] = [f"{defect_input.get('part_name')}{defect_input.get('defect_type')} 详细维护案例及备件规格"]
        else:
            state["is_info_sufficient"] = True
            state["supplementary_queries"] = []
    
    state["messages"].extend(response["messages"])
    return state

def maintenance_node(state: State) -> State:
    """维护方案生成：仅当信息充足或重试次数用尽时执行"""
    defect_input = state["defect_input"]
    extraction_result = state["extraction_result"]
    fault_analysis_result = state["fault_analysis_result"]
    retry_count = state["retry_count"] - 1  # 实际检索次数（检索后retry_count+1）
    
    # 记录思考过程
    thinking_process = f"【巡检总结与维护方案生成节点】\n"
    thinking_process += f"方案目标：{defect_input.get('part_name')}{defect_input.get('defect_type')}的维修维护\n"
    thinking_process += f"输入依据：{len(fault_analysis_result.get('potential_causes', []))}个潜在原因，风险等级{fault_analysis_result.get('risk_assessment', [{}])[0].get('risk_level')}\n"
    if state["is_info_sufficient"] or retry_count >= state["max_retry"]:
        thinking_process += f"信息状态：{'信息充足' if state['is_info_sufficient'] else '已达最大重试次数，使用现有信息'}\n"
    thinking_process += f"开始生成针对性维护方案..."
    state["thinking_processes"].append(thinking_process)
    
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
    maintenance_agent = common_llm(maintenance_prompt, "巡检总结与维护方案生成节点")
    response = maintenance_agent(state)
    
    try:
        json_data = clean_json_output(response["messages"][0].content)
        maintenance_plan_result = json.loads(json_data)
        state["thinking_processes"].append(f"【巡检总结与维护方案生成节点】方案生成完成，包含{len(maintenance_plan_result.get('maintenance_steps', []))}个执行步骤")
    except:
        error_msg = "维护方案生成失败，使用默认方案"
        state["thinking_processes"].append(f"【巡检总结与维护方案生成节点】{error_msg}")
        part_name = defect_input.get("part_name", "未知部件")
        maintenance_plan_result = {
            "suggested_maintenance_time": "立即检查",
            "spare_parts_list": [{"备件名称": part_name, "型号": "参考通用型号", "quantity": 1, "specs": "通用规格"}],
            "maintenance_steps": [f"1. 停机检查{part_name}状态", f"2. 更换损坏部件（若有）", f"3. 测试设备运行情况"],
            "fault_summary": f"{part_name}{defect_input.get('defect_type', '异常')}",
            "risk_reminder": "无历史数据，建议优先现场人工检测"
        }
    
    state["maintenance_plan_result"] = maintenance_plan_result
    state["messages"].extend(response["messages"])
    return state

def generate_final_report(state: State) -> str:
    """生成最终分析报告（整合所有结果）"""
    defect_input = state["defect_input"]
    retrieval_result = state["retrieval_result"]
    extraction_result = state["extraction_result"]
    fault_analysis_result = state["fault_analysis_result"]
    maintenance_plan_result = state["maintenance_plan_result"]
    retry_count = state["retry_count"] - 1
    
    # 构建报告
    report = f"""# 轨道巡检故障分析报告
## 一、故障基本信息
| 项目 | 内容 |
|------|------|
| 检测时间 | {defect_input.get('detect_time', '未知')} |
| 部件名称 | {defect_input.get('part_name', '未知')} |
| 部件位置 | {defect_input.get('part_position', '未知')} |
| 缺陷类型 | {defect_input.get('defect_type', '未知')} |
| 检测置信度 | {defect_input.get('detect_confidence', 0.0)} |
| 检索次数 | 初始检索 + 补充检索{retry_count}次 |

## 二、数据检索概况
基于GraphRAG混合检索，检索范围包括：
- 巡检记录：2019年1月1日至2023年12月31日
- 运行日志：2019年1月1日至2023年12月31日
- 维修报告：2019年1月1日至2023年12月31日
- 部件规格：未获得查询结果

### 关键部件信息
| 规格项 | 数值 |
|--------|------|
| 型号 | 未知 |
| 内径 | 未知 |
| 外径 | 未知 |
| 额定转速 | 未知 |
| 额定温度 | 未知 |
| 润滑脂更换周期 | 未知 |
| 使用年限 | 未知 |

## 三、核心信息提取
### 3.1 核心故障现象
"""
    
    core_phenomena = extraction_result.get('core_fault_phenomenon', ['无'])
    for i, phen in enumerate(core_phenomena, 1):
        if phen and phen != '无':
            report += f"{i}. {phen}\n"
    
    report += f"""
### 3.2 关键运行参数
"""
    critical_params = extraction_result.get('critical_env_params', [])
    for i, cparams in enumerate(critical_params, 1):
        if cparams and cparams != {'无': '无'}:
            for param_name, param_value in cparams.items():
                report += f"- {param_name}：{param_value}\n"
    else:
        report += "- 无相关关键参数记录\n"
    
    report += f"""
### 3.3 历史维护要点
"""
    maintenance_points = extraction_result.get('maintenance_key_points', ['无'])
    for i, point in enumerate(maintenance_points, 1):
        if point and point != '无':
            report += f"{i}. {point}\n"

    report += f"""
## 四、故障分析与风险评估
### 4.1 潜在故障原因
"""
    potential_causes = fault_analysis_result.get('potential_causes', [])
    for i, cause in enumerate(potential_causes, 1):
        report += f"""
#### 原因{i}
- 具体原因：{cause.get('原因', '未知')}
- 置信度：{cause.get('置信度', 0)}%
- 关联依据：{cause.get('关联依据', '无')}
"""
    
    report += f"""
### 4.2 风险评估
"""
    risk_assessments = fault_analysis_result.get('risk_assessment', [])
    for risk in risk_assessments:
        report += f"""
| 风险等级 | 预计故障时间 | 影响范围 |
|----------|--------------|----------|
| {risk.get('risk_level', '未知')} | {risk.get('expected_fault_time', '未知')} | {risk.get('impact_scope', '未知')} |
"""

    report += f"""
## 五、维护方案建议
### 5.1 建议维护时间
{maintenance_plan_result.get('suggested_maintenance_time', '立即维护')}

### 5.2 所需备件清单
"""
    spare_parts = maintenance_plan_result.get('spare_parts_list', [])
    if spare_parts:
        report += "| 备件名称 | 型号 | 数量 | 规格 |\n"
        report += "|----------|------|------|------|\n"
        for part in spare_parts:
            report += f"| {part.get('备件名称', '未知')} | {part.get('型号', '未知')} | {part.get('quantity', 0)} | {part.get('specs', '未知')} |\n"
    else:
        report += "- 无需额外备件\n"

    report += f"""
### 5.3 维护执行步骤
"""
    maintenance_steps = maintenance_plan_result.get('maintenance_steps', [])
    for i, step in enumerate(maintenance_steps, 1):
        report += f"{step}\n"

    report += f"""
### 5.4 故障总结与风险提示
#### 故障总结
{maintenance_plan_result.get('fault_summary', '无')}

#### 风险提示
{maintenance_plan_result.get('risk_reminder', '无')}

---
*报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*数据来源：Neo4j知识图谱 + 向量数据库混合检索（共检索{retry_count+1}次）*
"""
    return report

def create_railway_inspection_graph():
    graph = StateGraph(State)
    
    # 添加所有节点
    graph.add_node("数据检索节点", retrieval_node)
    graph.add_node("信息提取节点", extraction_node)
    graph.add_node("故障分析与风险评估节点", fault_analysis_node)
    graph.add_node("信息充足性反思", reflection_node)
    graph.add_node("巡检总结与维护方案生成节点", maintenance_node)
    
    # 定义条件判断函数：是否需要补充检索
    def should_retrieve_more(state: State) -> str:
        """
        判断是否需要补充检索：
        - 信息不足且未达最大重试次数 → 返回数据检索节点
        - 信息充足 或 已达最大重试次数 → 返回维护方案节点
        """
        if not state["is_info_sufficient"] and state["retry_count"] < state["max_retry"]:
            return "数据检索节点"
        else:
            return "巡检总结与维护方案生成节点"
    
    # 构建图的执行流程
    graph.add_edge(START, "数据检索节点")
    graph.add_edge("数据检索节点", "信息提取节点")
    graph.add_edge("信息提取节点", "故障分析与风险评估节点")
    graph.add_edge("故障分析与风险评估节点", "信息充足性反思")
    # 条件分支：根据反思结果选择下一个节点
    graph.add_conditional_edges(
        "信息充足性反思",
        should_retrieve_more,
        {
            "数据检索节点": "数据检索节点",
            "巡检总结与维护方案生成节点": "巡检总结与维护方案生成节点"
        }
    )
    graph.add_edge("巡检总结与维护方案生成节点", END)
    
    return graph.compile()

# 初始化图实例
railway_inspection_graph = create_railway_inspection_graph()

# -------------------------- Streamlit可视化界面 --------------------------
def main():
    st.set_page_config(
        page_title="轨道巡检故障分析系统",
        page_icon="🚄",
        layout="wide"
    )
    st.title("🚄 轨道巡检故障分析系统")

    # 顶部：缺陷信息输入
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
    
    # 执行按钮
    run_col1, run_col2, run_col3 = st.columns([1, 8, 1])
    with run_col1:
        run_analysis = st.button("🚀 执行故障分析", type="primary", use_container_width=True)
    with run_col3:
        refresh_graph = st.button("🔄 刷新图谱", use_container_width=True)

    # 构造缺陷输入数据
    defect_input = {
        "detect_time": detect_time,
        "part_name": part_name,
        "part_position": part_position,
        "defect_type": defect_type,
        "detect_confidence": detect_confidence
    }

    # 主界面布局
    main_col1, main_col2 = st.columns([0.5, 0.5])
    
    # 左侧：知识图谱可视化
    with main_col1:
        st.subheader("📊 知识库")
        if os.path.exists(GRAPH_HTML_PATH) or refresh_graph:
            with open(GRAPH_HTML_PATH, "r", encoding="utf-8") as f:
                graph_html = f.read()
            st.components.v1.html(graph_html, height=900, scrolling=True)
        else:
            st.info("可视化图谱不存在")

    # 右侧：结果展示区域
    with main_col2:
        st.subheader("📋 智能分析过程与结果")
        
        if not run_analysis:
            st.info("""
            ### 等待分析执行
            1. 请填写上方缺陷信息
            2. 点击「执行故障分析」按钮
            3. 系统将自动完成：
               - 初始GraphRAG检索
               - 核心信息提取与故障分析
               - 反思信息充足性，不足则自动补充检索（最多3次）
               - 生成维护方案与最终报告
            """)
        else:
            # 初始化状态
            initial_state = {
                "messages": [HumanMessage(content="请分析轨道巡检的故障并生成维护方案")],
                "defect_input": defect_input,
                "thinking_processes": [],
                "query_entities": [],
                "is_info_sufficient": False,
                "supplementary_queries": [],
                "retry_count": 0,
                "max_retry": 3
            }
            
            with st.spinner("🤖 智能体正在执行分析..."):
                result = railway_inspection_graph.invoke(initial_state)
            
            # 生成最终报告
            final_report = generate_final_report(result)
            
            # 展示思考过程
            st.markdown("### 🤔 智能体思考过程")
            thinking_container = st.container(border=True)
            with thinking_container:
                for i, process in enumerate(result["thinking_processes"], 1):
                    st.markdown(f"**步骤{i}：{process}**")
                    st.divider()
            
            # 展示各节点输出
            st.markdown("### 📝 各节点输出详情")
            with st.expander("1. 数据检索节点输出（含补充检索）", expanded=False):
                st.text_area("检索结果", result["retrieval_result"], height=200)
            
            with st.expander("2. 信息提取节点输出", expanded=False):
                st.json(result["extraction_result"], expanded=False)
            
            with st.expander("3. 故障分析与风险评估节点输出", expanded=False):
                st.json(result["fault_analysis_result"], expanded=False)
            
            with st.expander("4. 信息充足性反思输出", expanded=False):
                st.json({
                    "信息是否充足": result["is_info_sufficient"],
                    "补充查询": result["supplementary_queries"],
                    "重试次数": result["retry_count"]
                }, expanded=False)
            
            with st.expander("5. 维护方案生成节点输出", expanded=False):
                st.json(result["maintenance_plan_result"], expanded=False)
            
            # 展示最终报告
            st.markdown("### 📄 最终故障分析报告")
            report_container = st.container(border=True)
            with report_container:
                st.markdown(final_report)
            
            # 导出功能
            export_cols = st.columns([8, 1, 1])
            with export_cols[1]:
                if st.download_button(
                    label="📥 下载报告",
                    data=final_report,
                    file_name=f"轨道巡检故障分析报告_{datetime.now().strftime('%Y%m%d%H%M%S')}.md",
                    mime="text/markdown",
                    use_container_width=True
                ):
                    st.success("报告下载成功！")
            
            with export_cols[2]:
                if st.button("💾 保存完整数据", use_container_width=True):
                    full_data = {
                        "报告生成时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "缺陷输入信息": defect_input,
                        "检索次数": result["retry_count"],
                        "各节点输出": {
                            "检索结果": result["retrieval_result"],
                            "提取结果": result["extraction_result"],
                            "故障分析": result["fault_analysis_result"],
                            "反思结果": {
                                "信息充足": result["is_info_sufficient"],
                                "补充查询": result["supplementary_queries"]
                            },
                            "维护方案": result["maintenance_plan_result"]
                        },
                        "智能体思考过程": result["thinking_processes"],
                        "最终报告": final_report
                    }
                    with open(f"轨道巡检完整分析数据_{datetime.now().strftime('%Y%m%d%H%M%S')}.json", "w", encoding="utf-8") as f:
                        json.dump(full_data, f, ensure_ascii=False, indent=2)
                    st.success("完整数据保存成功！")

if __name__ == "__main__":
    main()