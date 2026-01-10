"""
NullForge AI Memory System - Vector Store
State of the Art semantic memory with ChromaDB

Features:
- Semantic search over code, conversations, and knowledge
- Long-term memory persistence
- Context-aware retrieval
- Automatic embedding generation
- Memory consolidation and compression
"""

import os
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
import uuid

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str
    content: str
    memory_type: str  # code, conversation, knowledge, error, success
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    embedding: Optional[List[float]] = None
    importance: float = 0.5  # 0-1 scale
    access_count: int = 0
    last_accessed: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        return cls(**data)


@dataclass 
class MemorySearchResult:
    """Search result with relevance score."""
    entry: MemoryEntry
    score: float
    distance: float


class EmbeddingEngine:
    """Handles text embedding generation."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        
    @property
    def model(self):
        if self._model is None:
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                self._model = SentenceTransformer(self.model_name)
            else:
                # Fallback to simple hash-based embedding
                self._model = "fallback"
        return self._model
    
    def embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        if self.model == "fallback":
            # Simple hash-based pseudo-embedding (384 dimensions to match all-MiniLM-L6-v2)
            return self._hash_embed(text)
        return self.model.encode(text).tolist()
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if self.model == "fallback":
            return [self._hash_embed(t) for t in texts]
        return self.model.encode(texts).tolist()
    
    def _hash_embed(self, text: str, dim: int = 384) -> List[float]:
        """Fallback hash-based embedding."""
        import hashlib
        # Create deterministic embedding from text hash
        hash_bytes = hashlib.sha384(text.encode()).digest()
        return [float(b) / 255.0 for b in hash_bytes[:dim]]


class VectorMemoryStore:
    """
    State of the Art vector-based memory store.
    
    Uses ChromaDB for semantic search and retrieval.
    Supports multiple memory types and importance-weighted recall.
    """
    
    COLLECTIONS = {
        "code": "nullforge_code_memory",
        "conversation": "nullforge_conversation_memory", 
        "knowledge": "nullforge_knowledge_memory",
        "error": "nullforge_error_memory",
        "success": "nullforge_success_memory",
        "general": "nullforge_general_memory"
    }
    
    def __init__(
        self,
        persist_directory: str = ".nullforge/memory",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.embedding_engine = EmbeddingEngine(embedding_model)
        
        # Initialize ChromaDB
        if CHROMADB_AVAILABLE:
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        else:
            self.client = None
            self._fallback_store: Dict[str, List[MemoryEntry]] = {}
            self._load_fallback_store()
        
        # Initialize collections
        self.collections = {}
        self._init_collections()
        
        # Memory stats
        self.stats = {
            "total_entries": 0,
            "queries_served": 0,
            "last_consolidation": None
        }
    
    def _init_collections(self):
        """Initialize memory collections."""
        for memory_type, collection_name in self.COLLECTIONS.items():
            if self.client:
                self.collections[memory_type] = self.client.get_or_create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
            else:
                if memory_type not in self._fallback_store:
                    self._fallback_store[memory_type] = []
    
    def _load_fallback_store(self):
        """Load fallback JSON store."""
        fallback_file = self.persist_directory / "memory_fallback.json"
        if fallback_file.exists():
            with open(fallback_file) as f:
                data = json.load(f)
                self._fallback_store = {
                    k: [MemoryEntry.from_dict(e) for e in v]
                    for k, v in data.items()
                }
    
    def _save_fallback_store(self):
        """Save fallback JSON store."""
        fallback_file = self.persist_directory / "memory_fallback.json"
        data = {
            k: [e.to_dict() for e in v]
            for k, v in self._fallback_store.items()
        }
        with open(fallback_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def add(
        self,
        content: str,
        memory_type: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5
    ) -> MemoryEntry:
        """
        Add a memory entry.
        
        Args:
            content: The content to remember
            memory_type: Type of memory (code, conversation, knowledge, etc.)
            metadata: Additional metadata
            importance: Importance score 0-1
            
        Returns:
            The created MemoryEntry
        """
        entry_id = str(uuid.uuid4())
        embedding = self.embedding_engine.embed(content)
        
        entry = MemoryEntry(
            id=entry_id,
            content=content,
            memory_type=memory_type,
            metadata=metadata or {},
            importance=importance,
            embedding=embedding
        )
        
        if self.client:
            collection = self.collections.get(memory_type, self.collections["general"])
            collection.add(
                ids=[entry_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[{
                    "memory_type": memory_type,
                    "importance": importance,
                    "timestamp": entry.timestamp,
                    **(metadata or {})
                }]
            )
        else:
            if memory_type not in self._fallback_store:
                self._fallback_store[memory_type] = []
            self._fallback_store[memory_type].append(entry)
            self._save_fallback_store()
        
        self.stats["total_entries"] += 1
        return entry
    
    def search(
        self,
        query: str,
        memory_type: Optional[str] = None,
        n_results: int = 10,
        min_score: float = 0.0,
        include_metadata: bool = True
    ) -> List[MemorySearchResult]:
        """
        Search memories semantically.
        
        Args:
            query: Search query
            memory_type: Filter by memory type (None for all)
            n_results: Maximum results to return
            min_score: Minimum relevance score (0-1)
            include_metadata: Include metadata in results
            
        Returns:
            List of MemorySearchResult sorted by relevance
        """
        query_embedding = self.embedding_engine.embed(query)
        results = []
        
        if self.client:
            collections_to_search = (
                [self.collections[memory_type]] if memory_type and memory_type in self.collections
                else list(self.collections.values())
            )
            
            for collection in collections_to_search:
                try:
                    search_results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=n_results,
                        include=["documents", "metadatas", "distances", "embeddings"] if include_metadata else ["documents", "distances"]
                    )
                    
                    if search_results and search_results['ids'] and search_results['ids'][0]:
                        for i, doc_id in enumerate(search_results['ids'][0]):
                            distance = search_results['distances'][0][i] if search_results['distances'] else 0
                            # Convert distance to similarity score (cosine distance -> similarity)
                            score = 1 - distance
                            
                            if score >= min_score:
                                entry = MemoryEntry(
                                    id=doc_id,
                                    content=search_results['documents'][0][i],
                                    memory_type=search_results['metadatas'][0][i].get('memory_type', 'general') if search_results['metadatas'] else 'general',
                                    metadata=search_results['metadatas'][0][i] if search_results['metadatas'] else {},
                                    embedding=search_results['embeddings'][0][i] if 'embeddings' in search_results and search_results['embeddings'] else None
                                )
                                results.append(MemorySearchResult(entry=entry, score=score, distance=distance))
                except Exception as e:
                    print(f"Search error in collection: {e}")
        else:
            # Fallback search using cosine similarity
            memories_to_search = (
                self._fallback_store.get(memory_type, []) if memory_type
                else [m for memories in self._fallback_store.values() for m in memories]
            )
            
            for entry in memories_to_search:
                if entry.embedding:
                    score = self._cosine_similarity(query_embedding, entry.embedding)
                    if score >= min_score:
                        results.append(MemorySearchResult(entry=entry, score=score, distance=1-score))
        
        # Sort by score and limit results
        results.sort(key=lambda r: r.score, reverse=True)
        results = results[:n_results]
        
        self.stats["queries_served"] += 1
        return results
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        dot_product = sum(x * y for x, y in zip(a, b))
        magnitude_a = math.sqrt(sum(x * x for x in a))
        magnitude_b = math.sqrt(sum(x * x for x in b))
        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0
        return dot_product / (magnitude_a * magnitude_b)
    
    def get(self, entry_id: str, memory_type: Optional[str] = None) -> Optional[MemoryEntry]:
        """Get a specific memory entry by ID."""
        if self.client:
            collections_to_search = (
                [self.collections[memory_type]] if memory_type and memory_type in self.collections
                else list(self.collections.values())
            )
            
            for collection in collections_to_search:
                try:
                    result = collection.get(ids=[entry_id], include=["documents", "metadatas", "embeddings"])
                    if result and result['ids']:
                        return MemoryEntry(
                            id=entry_id,
                            content=result['documents'][0],
                            memory_type=result['metadatas'][0].get('memory_type', 'general'),
                            metadata=result['metadatas'][0],
                            embedding=result['embeddings'][0] if result.get('embeddings') else None
                        )
                except Exception:
                    continue
        else:
            for mem_type, memories in self._fallback_store.items():
                for entry in memories:
                    if entry.id == entry_id:
                        return entry
        return None
    
    def delete(self, entry_id: str, memory_type: Optional[str] = None) -> bool:
        """Delete a memory entry."""
        if self.client:
            collections_to_search = (
                [self.collections[memory_type]] if memory_type and memory_type in self.collections
                else list(self.collections.values())
            )
            
            for collection in collections_to_search:
                try:
                    collection.delete(ids=[entry_id])
                    self.stats["total_entries"] -= 1
                    return True
                except Exception:
                    continue
        else:
            for mem_type, memories in self._fallback_store.items():
                for i, entry in enumerate(memories):
                    if entry.id == entry_id:
                        del memories[i]
                        self._save_fallback_store()
                        self.stats["total_entries"] -= 1
                        return True
        return False
    
    def consolidate(self, min_importance: float = 0.3) -> int:
        """
        Consolidate memory by removing low-importance entries.
        
        Args:
            min_importance: Minimum importance threshold
            
        Returns:
            Number of entries removed
        """
        removed = 0
        
        if self.client:
            for memory_type, collection in self.collections.items():
                try:
                    all_entries = collection.get(include=["metadatas"])
                    if all_entries and all_entries['ids']:
                        ids_to_remove = []
                        for i, entry_id in enumerate(all_entries['ids']):
                            importance = all_entries['metadatas'][i].get('importance', 0.5)
                            if importance < min_importance:
                                ids_to_remove.append(entry_id)
                        
                        if ids_to_remove:
                            collection.delete(ids=ids_to_remove)
                            removed += len(ids_to_remove)
                except Exception as e:
                    print(f"Consolidation error: {e}")
        else:
            for mem_type, memories in self._fallback_store.items():
                original_count = len(memories)
                self._fallback_store[mem_type] = [
                    m for m in memories if m.importance >= min_importance
                ]
                removed += original_count - len(self._fallback_store[mem_type])
            self._save_fallback_store()
        
        self.stats["total_entries"] -= removed
        self.stats["last_consolidation"] = datetime.now().isoformat()
        return removed
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory store statistics."""
        return {
            **self.stats,
            "chromadb_available": CHROMADB_AVAILABLE,
            "sentence_transformers_available": SENTENCE_TRANSFORMERS_AVAILABLE,
            "persist_directory": str(self.persist_directory),
            "collections": list(self.COLLECTIONS.keys())
        }
    
    def export(self, output_path: str) -> str:
        """Export all memories to JSON."""
        all_memories = {}
        
        if self.client:
            for memory_type, collection in self.collections.items():
                try:
                    data = collection.get(include=["documents", "metadatas", "embeddings"])
                    if data and data['ids']:
                        all_memories[memory_type] = [
                            {
                                "id": data['ids'][i],
                                "content": data['documents'][i],
                                "metadata": data['metadatas'][i],
                                "embedding": data['embeddings'][i] if data.get('embeddings') else None
                            }
                            for i in range(len(data['ids']))
                        ]
                except Exception:
                    continue
        else:
            all_memories = {
                k: [e.to_dict() for e in v]
                for k, v in self._fallback_store.items()
            }
        
        with open(output_path, "w") as f:
            json.dump(all_memories, f, indent=2)
        
        return output_path
    
    def import_memories(self, input_path: str) -> int:
        """Import memories from JSON."""
        with open(input_path) as f:
            data = json.load(f)
        
        imported = 0
        for memory_type, entries in data.items():
            for entry_data in entries:
                self.add(
                    content=entry_data.get('content', ''),
                    memory_type=memory_type,
                    metadata=entry_data.get('metadata', {}),
                    importance=entry_data.get('metadata', {}).get('importance', 0.5)
                )
                imported += 1
        
        return imported


class ConversationMemory:
    """
    Specialized memory for conversation history.
    
    Maintains a sliding window of recent messages plus
    semantic search over older conversations.
    """
    
    def __init__(
        self,
        vector_store: VectorMemoryStore,
        window_size: int = 20,
        summary_threshold: int = 50
    ):
        self.vector_store = vector_store
        self.window_size = window_size
        self.summary_threshold = summary_threshold
        self.recent_messages: List[Dict[str, str]] = []
        self.message_count = 0
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a message to conversation memory."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **(metadata or {})
        }
        
        self.recent_messages.append(message)
        self.message_count += 1
        
        # Store in vector memory
        self.vector_store.add(
            content=f"{role}: {content}",
            memory_type="conversation",
            metadata={"role": role, **(metadata or {})},
            importance=0.6 if role == "user" else 0.4
        )
        
        # Trim window
        if len(self.recent_messages) > self.window_size:
            self.recent_messages = self.recent_messages[-self.window_size:]
        
        # Check if summarization needed
        if self.message_count % self.summary_threshold == 0:
            self._create_summary()
    
    def _create_summary(self):
        """Create a summary of recent conversation."""
        if len(self.recent_messages) < 5:
            return
        
        # Simple summary: first and last few messages
        summary_content = "Conversation summary:\n"
        for msg in self.recent_messages[:3] + self.recent_messages[-3:]:
            summary_content += f"- {msg['role']}: {msg['content'][:100]}...\n"
        
        self.vector_store.add(
            content=summary_content,
            memory_type="knowledge",
            metadata={"type": "conversation_summary"},
            importance=0.8
        )
    
    def get_context(self, query: Optional[str] = None, n_relevant: int = 5) -> str:
        """
        Get conversation context.
        
        Args:
            query: Optional query to retrieve relevant past messages
            n_relevant: Number of relevant past messages to include
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        # Add recent messages
        context_parts.append("Recent conversation:")
        for msg in self.recent_messages[-10:]:
            context_parts.append(f"  {msg['role']}: {msg['content'][:200]}")
        
        # Add semantically relevant past messages
        if query:
            relevant = self.vector_store.search(
                query=query,
                memory_type="conversation",
                n_results=n_relevant,
                min_score=0.5
            )
            
            if relevant:
                context_parts.append("\nRelevant past context:")
                for result in relevant:
                    context_parts.append(f"  [{result.score:.2f}] {result.entry.content[:200]}")
        
        return "\n".join(context_parts)
    
    def clear(self):
        """Clear recent messages (keeps vector store)."""
        self.recent_messages = []


class CodeMemory:
    """
    Specialized memory for code patterns and solutions.
    
    Remembers successful code generations, common patterns,
    and error solutions.
    """
    
    def __init__(self, vector_store: VectorMemoryStore):
        self.vector_store = vector_store
    
    def remember_code(
        self,
        code: str,
        description: str,
        language: str = "python",
        tags: Optional[List[str]] = None,
        success: bool = True
    ) -> MemoryEntry:
        """Remember a code snippet."""
        content = f"[{language}] {description}\n\n```{language}\n{code}\n```"
        
        return self.vector_store.add(
            content=content,
            memory_type="code",
            metadata={
                "language": language,
                "tags": tags or [],
                "success": success,
                "lines": len(code.split('\n'))
            },
            importance=0.7 if success else 0.5
        )
    
    def remember_error(
        self,
        error: str,
        solution: str,
        context: Optional[str] = None
    ) -> MemoryEntry:
        """Remember an error and its solution."""
        content = f"Error: {error}\n\nSolution: {solution}"
        if context:
            content += f"\n\nContext: {context}"
        
        return self.vector_store.add(
            content=content,
            memory_type="error",
            metadata={"has_solution": bool(solution)},
            importance=0.8  # Errors are important to remember
        )
    
    def find_similar_code(
        self,
        query: str,
        language: Optional[str] = None,
        n_results: int = 5
    ) -> List[MemorySearchResult]:
        """Find similar code patterns."""
        results = self.vector_store.search(
            query=query,
            memory_type="code",
            n_results=n_results * 2  # Get more, then filter
        )
        
        if language:
            results = [
                r for r in results 
                if r.entry.metadata.get('language') == language
            ]
        
        return results[:n_results]
    
    def find_error_solution(self, error: str, n_results: int = 3) -> List[MemorySearchResult]:
        """Find solutions for similar errors."""
        return self.vector_store.search(
            query=error,
            memory_type="error",
            n_results=n_results,
            min_score=0.4
        )


# Global memory instance
_memory_store: Optional[VectorMemoryStore] = None


def get_memory_store(persist_directory: str = ".nullforge/memory") -> VectorMemoryStore:
    """Get or create the global memory store."""
    global _memory_store
    if _memory_store is None:
        _memory_store = VectorMemoryStore(persist_directory=persist_directory)
    return _memory_store


def remember(content: str, memory_type: str = "general", **kwargs) -> MemoryEntry:
    """Convenience function to add a memory."""
    store = get_memory_store()
    return store.add(content, memory_type, **kwargs)


def recall(query: str, memory_type: Optional[str] = None, n_results: int = 5) -> List[MemorySearchResult]:
    """Convenience function to search memories."""
    store = get_memory_store()
    return store.search(query, memory_type, n_results)
