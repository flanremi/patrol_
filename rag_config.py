# -*- coding: utf-8 -*-
"""
RAG 与向量数据库配置
- 后端通过 RAG_MODE 切换 graph（知识图谱+向量）与 vector（纯向量文档）方案
- 向量库路径、文档目录、分块参数等在此统一配置
"""
import os


# ---------- HuggingFace 镜像配置（中国用户） ----------
# 设置镜像源加速模型下载，如 https://hf-mirror.com
HF_ENDPOINT = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")
if HF_ENDPOINT:
    os.environ["HF_ENDPOINT"] = HF_ENDPOINT

# 项目根目录（以本文件所在目录为基准）
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# ---------- RAG 接入方案 ----------
# 可选: "graph" = Neo4j 知识图谱 + 向量混合检索；"vector" = 仅向量数据库文档检索
RAG_MODE = os.getenv("RAG_MODE", "vector").strip().lower()
if RAG_MODE not in ("graph", "vector"):
    RAG_MODE = "vector"

# ---------- 向量数据库（Chroma） ----------
# 持久化目录；不存在时由激活脚本创建并写入 doc 下的文档
VECTOR_DB_DIR = os.getenv("VECTOR_DB_DIR", os.path.join(PROJECT_ROOT, "data", "chroma"))
VECTOR_COLLECTION_NAME = os.getenv("VECTOR_COLLECTION_NAME", "patrol_docs")

# ---------- 文档目录（用于初始化向量库） ----------
DOC_DIR = os.getenv("DOC_DIR", os.path.join(PROJECT_ROOT, "doc"))

# ---------- 分块配置（适合 RAG 检索） ----------
CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "150"))

# ---------- 本地嵌入模型（无需代理、不连远端） ----------
# 使用 sentence-transformers 在本地加载模型；可为 HuggingFace 模型 id 或本地目录路径
# 默认 BAAI/bge-small-zh-v1.5（中文友好，首次运行会下载到本地缓存，之后完全离线）
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-small-zh-v1.5")

# ---------- 向量库激活脚本 ----------
INIT_VECTOR_DB_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "init_vector_db.py")


def vector_db_exists() -> bool:
    """判断向量数据库是否已存在（目录存在且非空）。"""
    if not os.path.isdir(VECTOR_DB_DIR):
        return False
    # Chroma 持久化后会生成 chroma.sqlite3 等文件
    for name in os.listdir(VECTOR_DB_DIR):
        if name.endswith(".sqlite3") or name == "chroma.sqlite3":
            return True
    return False
