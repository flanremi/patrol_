# -*- coding: utf-8 -*-
"""
通用 RAG 模块
支持多库切换、保存 PDF 页码和物理地址
通过库地址和库名来选择不同的向量库

使用示例:
    from rag_module import RAGModule
    
    # 创建 RAG 实例（使用默认库）
    rag = RAGModule()
    
    # 或指定特定库
    rag = RAGModule(db_dir="/path/to/db", collection_name="my_collection")
    
    # 检索文档
    results = rag.retrieve("查询内容", top_k=5)
    
    # 发送检索结果到前端（通过 WebSocket 回调）
    await rag.retrieve_and_notify(query, ws_callback, top_k=5)
"""
import os
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RAGDocument:
    """RAG 检索文档结果"""
    text: str
    source: str  # PDF 名称或文件名
    page: Optional[int]  # PDF 页码（从 1 开始）
    file_path: str  # 物理文件路径
    score: Optional[float] = None  # 相似度分数
    chunk_index: Optional[int] = None  # 分块索引
    metadata: Optional[Dict[str, Any]] = None  # 其他元数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "text": self.text,
            "source": self.source,
            "page": self.page,
            "file_path": self.file_path,
            "score": self.score,
            "chunk_index": self.chunk_index,
            "metadata": self.metadata or {}
        }
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class RAGRetrievalResult:
    """RAG 检索结果"""
    query: str
    documents: List[RAGDocument]
    total_count: int
    db_dir: str
    collection_name: str
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "query": self.query,
            "documents": [doc.to_dict() for doc in self.documents],
            "total_count": self.total_count,
            "db_dir": self.db_dir,
            "collection_name": self.collection_name,
            "timestamp": self.timestamp
        }
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class RAGModule:
    """
    通用 RAG 检索模块
    
    支持通过库地址和库名切换不同的向量库
    """
    
    _instances: Dict[str, 'RAGModule'] = {}  # 缓存已创建的实例
    
    def __init__(
        self,
        db_dir: Optional[str] = None,
        collection_name: Optional[str] = None,
        embedding_model: Optional[str] = None
    ):
        """
        初始化 RAG 模块
        
        Args:
            db_dir: 向量库目录，默认使用 rag_config 中的配置
            collection_name: 集合名称，默认使用 rag_config 中的配置
            embedding_model: 嵌入模型名称，默认使用 rag_config 中的配置
        """
        # 导入配置
        from rag_config import (
            VECTOR_DB_DIR, 
            VECTOR_COLLECTION_NAME, 
            EMBEDDING_MODEL_NAME
        )
        
        self.db_dir = db_dir or VECTOR_DB_DIR
        self.collection_name = collection_name or VECTOR_COLLECTION_NAME
        self.embedding_model = embedding_model or EMBEDDING_MODEL_NAME
        
        self._retriever = None
        self._embeddings = None
        self._chroma = None
        self._initialized = False
        
        logger.info(f"RAGModule 创建: db_dir={self.db_dir}, collection={self.collection_name}")
    
    @classmethod
    def get_instance(
        cls,
        db_dir: Optional[str] = None,
        collection_name: Optional[str] = None,
        embedding_model: Optional[str] = None
    ) -> 'RAGModule':
        """
        获取或创建 RAG 模块实例（单例模式，按 db_dir + collection_name 缓存）
        
        Args:
            db_dir: 向量库目录
            collection_name: 集合名称
            embedding_model: 嵌入模型名称
            
        Returns:
            RAGModule 实例
        """
        from rag_config import VECTOR_DB_DIR, VECTOR_COLLECTION_NAME
        
        db_dir = db_dir or VECTOR_DB_DIR
        collection_name = collection_name or VECTOR_COLLECTION_NAME
        
        key = f"{db_dir}:{collection_name}"
        
        if key not in cls._instances:
            cls._instances[key] = cls(
                db_dir=db_dir,
                collection_name=collection_name,
                embedding_model=embedding_model
            )
        
        return cls._instances[key]
    
    def initialize(self) -> bool:
        """
        初始化向量检索器
        
        Returns:
            是否初始化成功
        """
        if self._initialized:
            return True
        
        try:
            from langchain_community.vectorstores import Chroma
            from langchain_community.embeddings import HuggingFaceEmbeddings
            
            logger.info(f"正在初始化嵌入模型: {self.embedding_model}")
            self._embeddings = HuggingFaceEmbeddings(
                model_name=self.embedding_model,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
            
            logger.info(f"正在连接向量数据库: {self.db_dir} (collection: {self.collection_name})")
            self._chroma = Chroma(
                persist_directory=self.db_dir,
                embedding_function=self._embeddings,
                collection_name=self.collection_name,
            )
            
            self._retriever = self._chroma.as_retriever(search_kwargs={"k": 10})
            
            # 检查集合是否存在
            try:
                count = self._chroma._collection.count()
                logger.info(f"向量库初始化成功，文档数: {count}")
            except Exception:
                logger.warning("无法获取向量库文档数")
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"向量检索器初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5
    ) -> RAGRetrievalResult:
        """
        检索文档
        
        Args:
            query: 查询文本
            top_k: 返回的文档数量
            
        Returns:
            RAGRetrievalResult 检索结果
        """
        if not self._initialized:
            if not self.initialize():
                return RAGRetrievalResult(
                    query=query,
                    documents=[],
                    total_count=0,
                    db_dir=self.db_dir,
                    collection_name=self.collection_name,
                    timestamp=datetime.now().isoformat()
                )
        
        documents = []
        
        try:
            # 使用带分数的相似度搜索
            if self._chroma:
                results_with_scores = self._chroma.similarity_search_with_score(
                    query, k=top_k
                )
                
                for i, (doc, score) in enumerate(results_with_scores):
                    metadata = doc.metadata or {}
                    
                    # 提取页码：支持多种字段名
                    page = metadata.get("page") or metadata.get("page_number")
                    if page is not None:
                        try:
                            page = int(page) + 1  # 转换为 1-based 页码
                        except (ValueError, TypeError):
                            page = None
                    
                    # 提取文件路径
                    file_path = metadata.get("file_path") or metadata.get("source") or ""
                    
                    # 提取文件名
                    source = metadata.get("filename") or metadata.get("source", "")
                    if source and os.path.sep in source:
                        source = os.path.basename(source)
                    
                    rag_doc = RAGDocument(
                        text=doc.page_content,
                        source=source,
                        page=page,
                        file_path=file_path,
                        score=1 - score if score <= 1 else score,  # 转换为相似度分数
                        chunk_index=i,
                        metadata=metadata
                    )
                    documents.append(rag_doc)
                    
        except Exception as e:
            logger.error(f"检索失败: {e}")
            import traceback
            traceback.print_exc()
        
        result = RAGRetrievalResult(
            query=query,
            documents=documents,
            total_count=len(documents),
            db_dir=self.db_dir,
            collection_name=self.collection_name,
            timestamp=datetime.now().isoformat()
        )
        
        # 打印检索结果到控制台
        self._print_retrieval_result(result)
        
        return result
    
    def _print_retrieval_result(self, result: RAGRetrievalResult) -> None:
        """打印检索结果到控制台"""
        sep = "=" * 70
        print(f"\n{sep}")
        print(f"  [RAG 检索] 向量数据库文档检索")
        print(f"{sep}")
        print(f"  数据库: {result.db_dir}")
        print(f"  集合: {result.collection_name}")
        print(f"  查询: {result.query}")
        print(f"  命中文档数: {result.total_count}")
        print(f"-" * 70)
        
        for i, doc in enumerate(result.documents, 1):
            preview = (doc.text[:200] + "...") if len(doc.text) > 200 else doc.text
            print(f"  【文档 {i}】")
            print(f"    来源: {doc.source}")
            if doc.page:
                print(f"    页码: 第 {doc.page} 页")
            print(f"    路径: {doc.file_path}")
            if doc.score is not None:
                print(f"    相似度: {doc.score:.4f}")
            print(f"    内容: {preview}")
            print()
        
        print(f"{sep}\n")
    
    def _format_retrieval_result_for_display(self, result: RAGRetrievalResult) -> str:
        """格式化检索结果为前端显示的文本格式（类似 _print_retrieval_result）"""
        sep = "=" * 50
        lines = []
        lines.append(f"\n{sep}")
        lines.append(f"[RAG 检索] 向量数据库文档检索")
        lines.append(f"{sep}")
        lines.append(f"查询: {result.query}")
        lines.append(f"命中文档数: {result.total_count}")
        lines.append(f"{'-' * 50}")
        
        for i, doc in enumerate(result.documents, 1):
            preview = (doc.text[:150] + "...") if len(doc.text) > 150 else doc.text
            lines.append(f"【文档 {i}】")
            lines.append(f"  来源: {doc.source}")
            if doc.page:
                lines.append(f"  页码: 第 {doc.page} 页")
            if doc.score is not None:
                lines.append(f"  相似度: {doc.score:.4f}")
            lines.append(f"  内容: {preview}")
            lines.append("")
        
        lines.append(f"{sep}\n")
        return "\n".join(lines)
    
    async def retrieve_and_notify(
        self,
        query: str,
        ws_callback: Optional[Callable[[str, str, dict], Awaitable[None]]],
        top_k: int = 5,
        action: str = "rag_retrieval"
    ) -> RAGRetrievalResult:
        """
        检索文档并通过 WebSocket 回调发送结果到前端
        
        Args:
            query: 查询文本
            ws_callback: WebSocket 回调函数
            top_k: 返回的文档数量
            action: WebSocket 消息的 action 类型
            
        Returns:
            RAGRetrievalResult 检索结果
        """
        result = self.retrieve(query, top_k)
        
        # 发送检索结果到前端
        if ws_callback:
            try:
                # 生成格式化的显示文本
                formatted_text = self._format_retrieval_result_for_display(result)
                
                # 发送完整数据（包含格式化文本）
                data = result.to_dict()
                data["formatted_text"] = formatted_text
                await ws_callback("tool", action, data)
            except Exception as e:
                logger.error(f"发送 RAG 检索结果失败: {e}")
        
        return result
    
    def get_documents_text(
        self,
        result: RAGRetrievalResult,
        separator: str = "\n\n#Document\n"
    ) -> str:
        """
        将检索结果转换为纯文本（用于 LLM 输入）
        
        Args:
            result: 检索结果
            separator: 文档分隔符
            
        Returns:
            合并后的文档文本
        """
        if not result.documents:
            return "未找到相关文档"
        
        return separator.join([doc.text for doc in result.documents])
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        获取向量库信息
        
        Returns:
            包含向量库信息的字典
        """
        if not self._initialized:
            self.initialize()
        
        info = {
            "db_dir": self.db_dir,
            "collection_name": self.collection_name,
            "embedding_model": self.embedding_model,
            "initialized": self._initialized,
            "document_count": None
        }
        
        if self._chroma:
            try:
                info["document_count"] = self._chroma._collection.count()
            except Exception:
                pass
        
        return info


# ===================== 便捷函数 =====================

def get_default_rag() -> RAGModule:
    """获取默认的 RAG 模块实例"""
    return RAGModule.get_instance()


def retrieve(
    query: str,
    top_k: int = 5,
    db_dir: Optional[str] = None,
    collection_name: Optional[str] = None
) -> RAGRetrievalResult:
    """
    便捷函数：检索文档
    
    Args:
        query: 查询文本
        top_k: 返回的文档数量
        db_dir: 向量库目录（可选）
        collection_name: 集合名称（可选）
        
    Returns:
        RAGRetrievalResult 检索结果
    """
    rag = RAGModule.get_instance(db_dir=db_dir, collection_name=collection_name)
    return rag.retrieve(query, top_k)


async def retrieve_and_notify(
    query: str,
    ws_callback: Optional[Callable[[str, str, dict], Awaitable[None]]],
    top_k: int = 5,
    db_dir: Optional[str] = None,
    collection_name: Optional[str] = None,
    action: str = "rag_retrieval"
) -> RAGRetrievalResult:
    """
    便捷函数：检索文档并发送到前端
    
    Args:
        query: 查询文本
        ws_callback: WebSocket 回调函数
        top_k: 返回的文档数量
        db_dir: 向量库目录（可选）
        collection_name: 集合名称（可选）
        action: WebSocket 消息的 action 类型
        
    Returns:
        RAGRetrievalResult 检索结果
    """
    rag = RAGModule.get_instance(db_dir=db_dir, collection_name=collection_name)
    return await rag.retrieve_and_notify(query, ws_callback, top_k, action)


# ===================== 测试入口 =====================
if __name__ == "__main__":
    # 测试 RAG 模块
    print("测试 RAG 模块...")
    
    rag = RAGModule()
    if rag.initialize():
        result = rag.retrieve("轴承温度异常", top_k=3)
        print(f"\n检索结果 JSON:\n{result.to_json()}")
    else:
        print("RAG 模块初始化失败")
