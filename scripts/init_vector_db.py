#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向量数据库激活脚本
- 若向量数据库不存在则创建
- 将项目 doc 目录下的文件按 RAG 推荐配置分块并写入向量数据库
- 过程输出详细日志
"""
import logging
import os
import sys

# ---------- HuggingFace 镜像配置（中国用户） ----------
# 设置镜像源加速模型下载，如 https://hf-mirror.com
HF_ENDPOINT = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")
if HF_ENDPOINT:
    os.environ["HF_ENDPOINT"] = HF_ENDPOINT

# 将项目根目录加入 path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from rag_config import (
    VECTOR_DB_DIR,
    DOC_DIR,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    VECTOR_COLLECTION_NAME,
    EMBEDDING_MODEL_NAME,
)

# 配置日志：控制台 + 详细格式
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def _ensure_doc_dir():
    """确保 doc 目录存在。"""
    if not os.path.isdir(DOC_DIR):
        logger.warning("文档目录不存在，已创建空目录: %s", DOC_DIR)
        os.makedirs(DOC_DIR, exist_ok=True)
    return DOC_DIR


def _collect_files():
    """收集 doc 下支持的文档路径（.txt, .pdf, .docx）。"""
    supported = (".txt", ".pdf", ".docx")
    paths = []
    for root, _, files in os.walk(DOC_DIR):
        for f in files:
            if f.lower().endswith(supported):
                paths.append(os.path.join(root, f))
    return sorted(paths)


def _load_documents(file_paths):
    """按类型加载文档为 LangChain Document 列表。"""
    from langchain_core.documents import Document

    docs = []
    for path in file_paths:
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == ".txt":
                from langchain_community.document_loaders import TextLoader
                loader = TextLoader(path, encoding="utf-8", autodetect_encoding=True)
                part = loader.load()
            elif ext == ".pdf":
                from langchain_community.document_loaders import PyPDFLoader
                loader = PyPDFLoader(path)
                part = loader.load()
            elif ext == ".docx":
                from langchain_community.document_loaders import Docx2txtLoader
                loader = Docx2txtLoader(path)
                part = loader.load()
            else:
                continue
            for d in part:
                d.metadata.setdefault("source", path)
                d.metadata.setdefault("filename", os.path.basename(path))
            docs.extend(part)
            logger.info("  已加载: %s (片段数 %d)", path, len(part))
        except Exception as e:
            logger.exception("  加载失败 %s: %s", path, e)
    return docs


def _split_documents(docs):
    """对文档做分块（RAG 推荐配置）。"""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", "。", "；", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    logger.info("分块完成: 总片段数 %d (chunk_size=%d, overlap=%d)", len(chunks), CHUNK_SIZE, CHUNK_OVERLAP)
    return chunks


def _create_vector_store(chunks):
    """创建 Chroma 向量库并写入分块。使用本地 sentence-transformers 模型，无需代理、不连远端。"""
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings import HuggingFaceEmbeddings

    os.makedirs(VECTOR_DB_DIR, exist_ok=True)
    model_name = EMBEDDING_MODEL_NAME
    logger.info("使用本地嵌入模型: %s（sentence-transformers，无需代理）", model_name)
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    logger.info("正在写入 Chroma 持久化目录: %s (collection=%s)", VECTOR_DB_DIR, VECTOR_COLLECTION_NAME)
    vector_store = Chroma.from_documents(
        chunks,
        embeddings,
        persist_directory=VECTOR_DB_DIR,
        collection_name=VECTOR_COLLECTION_NAME,
    )
    vector_store.persist()
    logger.info("向量库创建并持久化完成。")
    return vector_store


def run():
    """执行：检查 -> 收集文档 -> 分块 -> 写入向量库。"""
    logger.info("========== 向量数据库激活脚本 ==========")
    logger.info("文档目录: %s", DOC_DIR)
    logger.info("向量库目录: %s", VECTOR_DB_DIR)
    logger.info("分块配置: chunk_size=%d, chunk_overlap=%d", CHUNK_SIZE, CHUNK_OVERLAP)

    _ensure_doc_dir()
    file_paths = _collect_files()
    if not file_paths:
        logger.warning("doc 目录下未找到 .txt/.pdf/.docx 文件，将创建空向量库。")

    logger.info("开始加载文档 (共 %d 个文件)...", len(file_paths))
    docs = _load_documents(file_paths)
    if not docs:
        logger.warning("未加载到任何文档内容，仍将创建空向量库。")
        docs = []  # Chroma.from_documents 需要列表，可传空列表

    logger.info("开始分块...")
    chunks = _split_documents(docs) if docs else []

    if not chunks:
        logger.warning("无有效分块，创建空向量库（仅结构）。")
        # 写入一个占位 chunk 以便 collection 存在
        from langchain_core.documents import Document
        placeholder = Document(page_content="无文档内容，请向 doc 目录添加 .txt/.pdf/.docx 后重新运行本脚本。", metadata={"source": "placeholder"})
        chunks = [placeholder]

    logger.info("创建并写入向量库...")
    _create_vector_store(chunks)
    logger.info("========== 向量数据库激活完成 ==========")
    return True


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        logger.exception("激活失败: %s", e)
        sys.exit(1)
