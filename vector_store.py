from pathlib import Path
from typing import List, Dict, Any, Optional

import uuid
from datetime import datetime
import time

from langchain_community.embeddings import OllamaEmbeddings
from qdrant_client import QdrantClient, models
import chromadb
import lancedb
from lancedb.pydantic import LanceModel, Vector

from config import Config

class LocalVectorStore:
    def __init__(self, collection_name: str = "repo_knowledge"):
        self.config = Config()
        self.collection_name = collection_name

        # Rationale: Use a helper to determine the device, keeping __init__ clean.
        device = self._get_embedding_device()

        # Rationale: Use the LangChain wrapper for clean integration and future-proofing.
        # This aligns with patterns in the reference repository.
        print(f"Initializing Ollama embeddings with model: {self.config.OLLAMA_EMBEDDING_MODEL} on device: {device}")
        self.embedding_model = OllamaEmbeddings(
            base_url=self.config.OLLAMA_BASE_URL,
            model=self.config.OLLAMA_EMBEDDING_MODEL
            # Note: The LangChain Ollama wrapper does not directly expose a 'device' param.
            # It relies on the Ollama server's configuration. The 'device' printout is for user feedback.
        )

        self.client = None
        self.collection = None
        self._initialize_vector_store()
    
    def _get_embedding_device(self) -> str:
        # Rationale: Encapsulate device selection logic. Respects user override.
        if self.config.EMBEDDING_DEVICE != "auto":
            return self.config.EMBEDDING_DEVICE

        try:
            import torch
            if torch.backends.mps.is_available():
                return "mps"
        except (ImportError, AttributeError):
            pass # Fallback to CPU
        return "cpu"

    def _initialize_vector_store(self):
        """Initialize the selected vector store"""
        db_type = self.config.VECTOR_DB_TYPE.lower()
        print(f"Initializing {db_type} vector store...")
        
        if db_type == "qdrant":
            self._init_qdrant()
        elif db_type == "chroma":
            self._init_chroma()
        elif db_type == "lancedb":
            self._init_lancedb()
        else:
            raise ValueError(f"Unsupported vector store: {db_type}")
    
    def _init_qdrant(self):
        """Initialize Qdrant vector store"""
        try:
            self.client = QdrantClient(url=self.config.QDRANT_URL)
            self.client.get_collections() # Test connection
        except Exception:
            print("Could not connect to Qdrant server, using in-memory storage.")
            self.client = QdrantClient(":memory:")
        
        try:
            collection_info = self.client.get_collection(collection_name=self.collection_name)
            print(f"Using existing Qdrant collection: {self.collection_name}")
            
            # Check if existing collection has correct dimensions
            existing_dimension = collection_info.config.params.vectors.size
            test_embedding = self.embed_query("test")
            required_dimension = len(test_embedding)
            
            if existing_dimension != required_dimension:
                print(f"⚠️  Dimension mismatch detected!")
                print(f"   Existing collection: {existing_dimension} dimensions")
                print(f"   Current model: {required_dimension} dimensions")
                print(f"   Recreating collection with correct dimensions...")
                
                # Delete and recreate collection with correct dimensions
                self.client.delete_collection(collection_name=self.collection_name)
                self._create_qdrant_collection(required_dimension)
        except Exception:
            # Collection doesn't exist, create it with dynamic dimensions
            print(f"Creating new Qdrant collection: {self.collection_name}")
            test_embedding = self.embed_query("test")
            embedding_dimension = len(test_embedding)
            print(f"Detected embedding dimension: {embedding_dimension}")
            self._create_qdrant_collection(embedding_dimension)
    
    def _create_qdrant_collection(self, dimension: int):
        """Create a new Qdrant collection with the specified dimension"""
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=dimension,
                distance=models.Distance.COSINE
            )
        )
    
    def _init_chroma(self):
        """Initialize ChromaDB vector store"""
        self.client = chromadb.PersistentClient(path=str(self.config.VECTOR_DB_DIR))
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        print(f"Using ChromaDB collection: {self.collection_name}")
    
    def _init_lancedb(self):
        """Initialize LanceDB vector store"""
        db = lancedb.connect(str(self.config.VECTOR_DB_DIR))
        
        # Get dynamic embedding dimension
        test_embedding = self.embed_query("test")
        embedding_dimension = len(test_embedding)
        print(f"Detected embedding dimension: {embedding_dimension}")
        
        class LanceSchema(LanceModel):
            vector: Vector(embedding_dimension)
            repo_name: str
            path: str
            content: str
            extension: str
            size: int
            modified: str
            hash: str
            added_at: str

        try:
            self.collection = db.open_table(self.collection_name)
            print(f"Using existing LanceDB table: {self.collection_name}")
        except FileNotFoundError:
            print(f"Creating new LanceDB table: {self.collection_name}")
            self.collection = db.create_table(
                self.collection_name,
                schema=LanceSchema,
                mode="overwrite"
            )

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        # Rationale: Switch to the LangChain standard method for embedding.
        print(f"Embedding a batch of {len(texts)} documents...")
        return self.embedding_model.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        print(f"Embedding query: '{text[:50]}...'")
        return self.embedding_model.embed_query(text)
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> int:
        """Add documents to vector store"""
        if not documents:
            return 0
        
        texts_to_embed = [f"File: {doc['path']}\n\nContent:\n{doc['content']}" for doc in documents]
        embeddings = self.embed_batch(texts_to_embed)
        
        db_type = self.config.VECTOR_DB_TYPE.lower()
        if db_type == "qdrant":
            return self._add_to_qdrant(documents, embeddings)
        elif db_type == "chroma":
            return self._add_to_chroma(documents, embeddings)
        elif db_type == "lancedb":
            return self._add_to_lancedb(documents, embeddings)
        return 0

    def _add_to_qdrant(self, documents: List[Dict], embeddings: List[List[float]]) -> int:
        points = [
            models.PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "repo_name": doc.get("repo_name", "unknown"),
                    "path": doc["path"],
                    "content": doc["content"],
                    "extension": doc.get("extension", ""),
                    "size": doc.get("size", 0),
                    "modified": doc.get("modified", ""),
                    "hash": doc.get("hash", ""),
                    "added_at": datetime.now().isoformat()
                }
            ) for doc, embedding in zip(documents, embeddings)
        ]
        self.client.upsert(collection_name=self.collection_name, points=points, wait=True)
        return len(points)

    def _add_to_chroma(self, documents: List[Dict], embeddings: List[List[float]]) -> int:
        ids = [str(uuid.uuid4()) for _ in documents]
        metadatas = [
            {
                "repo_name": doc.get("repo_name", "unknown"),
                "path": doc["path"],
                "extension": doc.get("extension", ""),
                "size": doc.get("size", 0),
                "modified": doc.get("modified", ""),
                "hash": doc.get("hash", ""),
                "added_at": datetime.now().isoformat()
            } for doc in documents
        ]
        contents = [doc["content"] for doc in documents]
        self.collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=contents)
        return len(ids)

    def _add_to_lancedb(self, documents: List[Dict], embeddings: List[List[float]]) -> int:
        data = [
            {
                "vector": embedding,
                "repo_name": doc.get("repo_name", "unknown"),
                "path": doc["path"],
                "content": doc["content"],
                "extension": doc.get("extension", ""),
                "size": doc.get("size", 0),
                "modified": doc.get("modified", ""),
                "hash": doc.get("hash", ""),
                "added_at": datetime.now().isoformat()
            } for doc, embedding in zip(documents, embeddings)
        ]
        self.collection.add(data)
        return len(data)

    def search(self, query: str, limit: int = 10, repo_filter: Optional[str] = None) -> List[Dict]:
        """Search for similar documents"""
        # In your search method, change the call from .encode() to the new embed_query method:
        query_embedding = self.embed_query(query)
        
        db_type = self.config.VECTOR_DB_TYPE.lower()
        if db_type == "qdrant":
            return self._search_qdrant(query_embedding, limit, repo_filter)
        elif db_type == "chroma":
            return self._search_chroma(query_embedding, limit, repo_filter)
        elif db_type == "lancedb":
            return self._search_lancedb(query_embedding, limit, repo_filter)
        return []

    def _search_qdrant(self, vector: List[float], limit: int, repo: Optional[str]) -> List[Dict]:
        search_filter = None
        if repo:
            search_filter = models.Filter(must=[models.FieldCondition(key="repo_name", match=models.MatchValue(value=repo))])
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            limit=limit,
            query_filter=search_filter
        )
        return [
            {**hit.payload, "score": hit.score} for hit in results
        ]

    def _search_chroma(self, vector: List[float], limit: int, repo: Optional[str]) -> List[Dict]:
        where_filter = {"repo_name": repo} if repo else None
        results = self.collection.query(query_embeddings=[vector], n_results=limit, where=where_filter)
        
        docs = []
        if results['ids'][0]:
            for i, doc_id in enumerate(results['ids'][0]):
                meta = results['metadatas'][0][i]
                doc = {
                    "score": 1 - results['distances'][0][i],
                    "content": results['documents'][0][i],
                    **meta
                }
                docs.append(doc)
        return docs

    def _search_lancedb(self, vector: List[float], limit: int, repo: Optional[str]) -> List[Dict]:
        query_builder = self.collection.search(vector).limit(limit)
        if repo:
            query_builder = query_builder.where(f"repo_name = '{repo}'")
        
        results = query_builder.to_pydantic()
        
        # LanceDB distance is L2, convert to a score where higher is better
        return [
            {**row.model_dump(), "score": 1 / (1 + row._distance)} for row in results
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store"""
        db_type = self.config.VECTOR_DB_TYPE.lower()
        try:
            if db_type == "qdrant":
                info = self.client.get_collection(self.collection_name)
                return {
                    "db_type": "Qdrant",
                    "total_documents": info.points_count,
                    "vector_size": info.vectors_config.params.size,
                    "distance_metric": info.vectors_config.params.distance.value
                }
            elif db_type == "chroma":
                return {
                    "db_type": "ChromaDB",
                    "total_documents": self.collection.count(),
                    "vector_size": self.embedding_model.get_sentence_embedding_dimension(),
                    "distance_metric": "cosine"
                }
            elif db_type == "lancedb":
                return {
                    "db_type": "LanceDB",
                    "total_documents": len(self.collection),
                    "vector_size": self.embedding_model.get_sentence_embedding_dimension(),
                    "distance_metric": "L2"
                }
        except Exception as e:
            print(f"Failed to get stats from {db_type}: {e}")
            return {"error": str(e)}
        return {}

    def delete_repo(self, repo_name: str):
        """Delete all vectors associated with a specific repository name."""
        print(f"Deleting all documents for repository: {repo_name}...")
        db_type = self.config.VECTOR_DB_TYPE.lower()

        try:
            if db_type == "qdrant":
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=models.FilterSelector(
                        filter=models.Filter(
                            must=[
                                models.FieldCondition(
                                    key="repo_name",
                                    match=models.MatchValue(value=repo_name),
                                )
                            ]
                        )
                    ),
                    wait=True,
                )
            elif db_type == "chroma":
                self.collection.delete(where={"repo_name": repo_name})
            elif db_type == "lancedb":
                self.collection.delete(f"repo_name = '{repo_name}'")
            print(f"Deletion complete for {repo_name}.")
        except Exception as e:
            print(f"Error deleting repository {repo_name}: {e}")

    def wipe_collection(self):
        """Deletes and recreates the entire collection for the configured DB type."""
        db_type = self.config.VECTOR_DB_TYPE.lower()
        print(f"🚨 Wiping entire collection '{self.collection_name}' for {db_type}...")
        try:
            if db_type == "qdrant":
                self.client.delete_collection(collection_name=self.collection_name)
                time.sleep(1) # Give a moment for the deletion to propagate
                self._init_qdrant() # Re-initialize to create it
            elif db_type == "chroma":
                self.client.delete_collection(name=self.collection_name)
                self._init_chroma() # Re-initialize
            elif db_type == "lancedb":
                db = lancedb.connect(str(self.config.VECTOR_DB_DIR))
                db.drop_table(self.collection_name)
                self._init_lancedb() # Re-initialize

            print(f"✅ Collection '{self.collection_name}' has been wiped and recreated.")
        except Exception as e:
            print(f"Error wiping collection: {e}. Attempting to re-initialize anyway...")
            # If deletion failed, it might be because it didn't exist. Re-init is a good fallback.
            self._initialize_vector_store()

    def get_all_repo_names(self) -> List[str]:
        """Get all unique repository names from the metadata."""
        try:
            # Implementation of get_all_repo_names method
            pass
        except Exception as e:
            print(f"Error getting all repository names: {e}")
            return []

    def _ensure_collection_exists(self):
        # Implementation of _ensure_collection_exists method
        pass 
