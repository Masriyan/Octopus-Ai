"""
Octopus AI — Vector Memory 🧠
Wraps Qdrant and Sentence-Transformers for semantic search and long-term memory.
"""
import os
import time
import uuid
import logging
from typing import List, Dict, Any

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    HAS_VECTOR_DB = True
except ImportError:
    HAS_VECTOR_DB = False
    
try:
    from sentence_transformers import SentenceTransformer
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

logger = logging.getLogger("octopus.vector_memory")

class VectorMemory:
    """Manages long-term vector embeddings using local Qdrant."""
    
    def __init__(self, persist_directory: str = "data/vector_db"):
        self.persist_directory = persist_directory
        self.enabled = HAS_VECTOR_DB and HAS_TRANSFORMERS
        
        if not self.enabled:
            logger.warning("Vector memory disabled: qdrant-client or sentence-transformers missing.")
            return
            
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize local Qdrant
        self.client = QdrantClient(path=persist_directory)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.vector_size = self.embedding_model.get_sentence_embedding_dimension()
        
        # Ensure collections exist
        self._ensure_collection("conversations")
        self._ensure_collection("preferences")

    def _ensure_collection(self, name: str):
        if not self.client.collection_exists(collection_name=name):
            self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            )

    def _embed(self, text: str) -> List[float]:
        return self.embedding_model.encode(text).tolist()
        
    def add_conversation_message(self, conv_id: str, message_id: str, role: str, content: str):
        """Store a conversation message in vector memory."""
        if not self.enabled or not content.strip():
            return
            
        try:
            vector = self._embed(content)
            # Use deterministic UUID based on conv_id and msg_id
            import hashlib
            point_id = str(uuid.UUID(hashlib.md5(f"{conv_id}_{message_id}".encode()).hexdigest()))
            
            self.client.upsert(
                collection_name="conversations",
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={
                            "content": content,
                            "conv_id": conv_id,
                            "role": role,
                            "timestamp": time.time()
                        }
                    )
                ]
            )
        except Exception as e:
            logger.error(f"Failed to vectorize message: {e}")

    def search_conversations(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search past conversations for semantic matches."""
        if not self.enabled:
            return []
            
        try:
            vector = self._embed(query)
            results = self.client.query_points(
                collection_name="conversations",
                query=vector,
                limit=limit
            ).points
            
            output = []
            for hit in results:
                output.append({
                    "content": hit.payload.get("content", ""),
                    "metadata": hit.payload,
                    "score": hit.score
                })
            return output
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
            
    def store_preference(self, key: str, value: str):
        """Store a long-term user preference."""
        if not self.enabled:
            return
            
        try:
            vector = self._embed(value)
            # Hash key for UUID
            import hashlib
            point_id = str(uuid.UUID(hashlib.md5(key.encode()).hexdigest()))
            
            self.client.upsert(
                collection_name="preferences",
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={
                            "key": key,
                            "value": value,
                            "timestamp": time.time()
                        }
                    )
                ]
            )
        except Exception as e:
            logger.error(f"Failed to store preference: {e}")
            
    def get_relevant_preferences(self, query: str, limit: int = 3) -> List[str]:
        if not self.enabled:
            return []
            
        try:
            vector = self._embed(query)
            results = self.client.query_points(
                collection_name="preferences",
                query=vector,
                limit=limit
            ).points
            return [hit.payload.get("value", "") for hit in results if hit.payload]
        except Exception as e:
            logger.error(f"Preference search failed: {e}")
            return []
