import chromadb
from chromadb.config import Settings
import logging
from server.config import CHROMA_DB_PATH, EMBEDDING_MODEL
import os

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self):
        # 确保数据库目录存在
        os.makedirs(CHROMA_DB_PATH, exist_ok=True)
        
        # 初始化Chroma客户端
        self.client = chromadb.PersistentClient(
            path=CHROMA_DB_PATH,
            settings=Settings(
                anonymized_telemetry=False
            )
        )
        
        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name="subtitles",
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.info("Vector store initialized")

    def add_subtitle(self, video_id, subtitle_text, metadata=None):
        """添加字幕到向量数据库"""
        try:
            # 将字幕文本分段（这里简单地按句号分割）
            segments = [s.strip() for s in subtitle_text.split('.') if s.strip()]
            
            # 为每个段落生成ID
            ids = [f"{video_id}_{i}" for i in range(len(segments))]
            
            # 添加元数据
            if metadata is None:
                metadata = {}
            metadatas = [{**metadata, "segment_index": i} for i in range(len(segments))]
            
            # 添加到集合
            self.collection.add(
                documents=segments,
                ids=ids,
                metadatas=metadatas
            )
            
            logger.info(f"Added {len(segments)} subtitle segments for video {video_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding subtitle to vector store: {str(e)}")
            return False

    def search(self, query, n_results=5):
        """搜索相似的字幕片段"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            # 格式化结果
            formatted_results = []
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error searching vector store: {str(e)}")
            return []

# 创建全局向量存储实例
vector_store = VectorStore() 