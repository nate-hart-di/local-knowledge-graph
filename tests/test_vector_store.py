import pytest
import os
from unittest.mock import patch, MagicMock, Mock
import sys
sys.path.append('..')

from vector_store import LocalVectorStore
from config import Config


class TestVectorStore:
    """Test vector store operations with mocked Ollama embeddings"""
    
    @patch('vector_store.OllamaEmbeddings')
    @patch('vector_store.QdrantClient')
    def test_initialization(self, mock_qdrant_client, mock_ollama_embeddings):
        """Test that vector store initializes correctly"""
        # Mock the embeddings
        mock_embedding_instance = MagicMock()
        mock_ollama_embeddings.return_value = mock_embedding_instance
        
        # Mock the Qdrant client
        mock_client_instance = MagicMock()
        mock_qdrant_client.return_value = mock_client_instance
        
        # Create vector store
        vs = LocalVectorStore("test_collection")
        
        # Verify initialization
        assert vs.collection_name == "test_collection"
        assert vs.embedding_model == mock_embedding_instance
        assert vs.client == mock_client_instance
        
        # Verify Ollama embeddings were configured correctly
        mock_ollama_embeddings.assert_called_once()
        call_args = mock_ollama_embeddings.call_args
        assert 'base_url' in call_args.kwargs
        assert 'model' in call_args.kwargs
    
    @patch('vector_store.OllamaEmbeddings')
    @patch('vector_store.QdrantClient')
    def test_device_detection(self, mock_qdrant_client, mock_ollama_embeddings):
        """Test device detection logic"""
        mock_ollama_embeddings.return_value = MagicMock()
        mock_qdrant_client.return_value = MagicMock()
        
        vs = LocalVectorStore()
        
        # Test with auto device
        device = vs._get_embedding_device()
        assert device in ['cpu', 'mps']
        
        # Test with manual device override
        vs.config.EMBEDDING_DEVICE = 'cpu'
        device = vs._get_embedding_device()
        assert device == 'cpu'
    
    @patch('vector_store.OllamaEmbeddings')
    @patch('vector_store.QdrantClient')
    def test_embed_batch(self, mock_qdrant_client, mock_ollama_embeddings):
        """Test batch embedding functionality"""
        # Mock embeddings response
        mock_embedding_instance = MagicMock()
        mock_embedding_instance.embed_documents.return_value = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6]
        ]
        mock_ollama_embeddings.return_value = mock_embedding_instance
        mock_qdrant_client.return_value = MagicMock()
        
        vs = LocalVectorStore()
        texts = ["test text 1", "test text 2"]
        
        # Test embedding
        embeddings = vs.embed_batch(texts)
        
        # Verify results
        assert len(embeddings) == 2
        assert embeddings[0] == [0.1, 0.2, 0.3]
        assert embeddings[1] == [0.4, 0.5, 0.6]
        
        # Verify Ollama was called correctly
        mock_embedding_instance.embed_documents.assert_called_once_with(texts)
    
    @patch('vector_store.OllamaEmbeddings')
    @patch('vector_store.QdrantClient')
    def test_embed_query(self, mock_qdrant_client, mock_ollama_embeddings):
        """Test single query embedding"""
        # Mock embeddings response
        mock_embedding_instance = MagicMock()
        mock_embedding_instance.embed_query.return_value = [0.1, 0.2, 0.3]
        mock_ollama_embeddings.return_value = mock_embedding_instance
        mock_qdrant_client.return_value = MagicMock()
        
        vs = LocalVectorStore()
        query = "test query"
        
        # Test embedding
        embedding = vs.embed_query(query)
        
        # Verify results
        assert embedding == [0.1, 0.2, 0.3]
        mock_embedding_instance.embed_query.assert_called_once_with(query)
    
    @patch('vector_store.OllamaEmbeddings')
    @patch('vector_store.QdrantClient')
    def test_add_documents(self, mock_qdrant_client, mock_ollama_embeddings):
        """Test adding documents to vector store"""
        # Mock embeddings
        mock_embedding_instance = MagicMock()
        mock_embedding_instance.embed_documents.return_value = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6]
        ]
        mock_ollama_embeddings.return_value = mock_embedding_instance
        
        # Mock Qdrant client
        mock_client_instance = MagicMock()
        mock_qdrant_client.return_value = mock_client_instance
        
        vs = LocalVectorStore()
        documents = [
            {
                "path": "test1.py",
                "content": "print('hello')",
                "repo_name": "test_repo",
                "extension": ".py",
                "size": 100
            },
            {
                "path": "test2.py", 
                "content": "print('world')",
                "repo_name": "test_repo",
                "extension": ".py",
                "size": 200
            }
        ]
        
        # Test adding documents
        result = vs.add_documents(documents)
        
        # Verify embeddings were generated
        mock_embedding_instance.embed_documents.assert_called_once()
        call_args = mock_embedding_instance.embed_documents.call_args[0][0]
        assert len(call_args) == 2
        assert "test1.py" in call_args[0]
        assert "test2.py" in call_args[1]
        
        # Verify documents were added to Qdrant
        mock_client_instance.upsert.assert_called_once()
        assert result == 2
    
    @patch('vector_store.OllamaEmbeddings')
    @patch('vector_store.QdrantClient')
    def test_search(self, mock_qdrant_client, mock_ollama_embeddings):
        """Test search functionality"""
        # Mock embeddings
        mock_embedding_instance = MagicMock()
        mock_embedding_instance.embed_query.return_value = [0.1, 0.2, 0.3]
        mock_ollama_embeddings.return_value = mock_embedding_instance
        
        # Mock Qdrant client with search results
        mock_client_instance = MagicMock()
        mock_search_result = MagicMock()
        mock_search_result.id = "test_id"
        mock_search_result.score = 0.9
        mock_search_result.payload = {
            "path": "test.py",
            "content": "test content",
            "repo_name": "test_repo",
            "extension": ".py"
        }
        mock_client_instance.search.return_value = [mock_search_result]
        mock_qdrant_client.return_value = mock_client_instance
        
        vs = LocalVectorStore()
        
        # Test search
        results = vs.search("test query", limit=5)
        
        # Verify query was embedded
        mock_embedding_instance.embed_query.assert_called_once_with("test query")
        
        # Verify search was called
        mock_client_instance.search.assert_called_once()
        
        # Verify results
        assert len(results) == 1
        assert results[0]["path"] == "test.py"
        assert results[0]["content"] == "test content"
        assert results[0]["repo_name"] == "test_repo"
        assert results[0]["score"] == 0.9
    
    @patch('vector_store.OllamaEmbeddings')
    @patch('vector_store.QdrantClient')
    def test_search_with_repo_filter(self, mock_qdrant_client, mock_ollama_embeddings):
        """Test search with repository filter"""
        mock_embedding_instance = MagicMock()
        mock_embedding_instance.embed_query.return_value = [0.1, 0.2, 0.3]
        mock_ollama_embeddings.return_value = mock_embedding_instance
        
        mock_client_instance = MagicMock()
        mock_client_instance.search.return_value = []
        mock_qdrant_client.return_value = mock_client_instance
        
        vs = LocalVectorStore()
        
        # Test search with filter
        vs.search("test query", repo_filter="specific_repo")
        
        # Verify search was called with filter
        mock_client_instance.search.assert_called_once()
        call_args = mock_client_instance.search.call_args
        assert call_args.kwargs is not None
    
    @patch('vector_store.OllamaEmbeddings')
    @patch('vector_store.QdrantClient')
    def test_get_stats(self, mock_qdrant_client, mock_ollama_embeddings):
        """Test getting vector store statistics"""
        mock_ollama_embeddings.return_value = MagicMock()
        
        # Mock Qdrant client with collection info
        mock_client_instance = MagicMock()
        mock_collection_info = MagicMock()
        mock_collection_info.points_count = 100
        mock_collection_info.vectors_config.params.size = 768
        mock_client_instance.get_collection.return_value = mock_collection_info
        mock_qdrant_client.return_value = mock_client_instance
        
        vs = LocalVectorStore()
        
        # Test getting stats
        stats = vs.get_stats()
        
        # Verify results
        assert stats["db_type"].lower() == "qdrant"
        assert stats["total_documents"] == 100
        assert stats["vector_size"] == 768
        
        # Verify Qdrant was called with our collection name
        assert mock_client_instance.get_collection.called
        # Verify the last call was for stats
        last_call = mock_client_instance.get_collection.call_args_list[-1]
        assert last_call[0][0] == vs.collection_name
    
    @patch('vector_store.OllamaEmbeddings')
    @patch('vector_store.QdrantClient')
    def test_delete_repo(self, mock_qdrant_client, mock_ollama_embeddings):
        """Test deleting repository from vector store"""
        mock_ollama_embeddings.return_value = MagicMock()
        
        mock_client_instance = MagicMock()
        mock_qdrant_client.return_value = mock_client_instance
        
        vs = LocalVectorStore()
        
        # Test deleting repository
        vs.delete_repo("test_repo")
        
        # Verify delete was called
        mock_client_instance.delete.assert_called_once()
        call_args = mock_client_instance.delete.call_args
        assert call_args.kwargs is not None
    
    @patch('vector_store.OllamaEmbeddings')
    @patch('vector_store.QdrantClient')
    def test_empty_documents_handling(self, mock_qdrant_client, mock_ollama_embeddings):
        """Test handling of empty document list"""
        mock_ollama_embeddings.return_value = MagicMock()
        mock_qdrant_client.return_value = MagicMock()
        
        vs = LocalVectorStore()
        
        # Test with empty documents
        result = vs.add_documents([])
        
        # Should return 0 without processing
        assert result == 0
    
    @patch('vector_store.OllamaEmbeddings')
    @patch('vector_store.QdrantClient')
    def test_qdrant_connection_failure(self, mock_qdrant_client, mock_ollama_embeddings):
        """Test handling of Qdrant connection failure"""
        mock_ollama_embeddings.return_value = MagicMock()
        
        # Mock connection failure, then fallback to memory
        mock_qdrant_client.side_effect = [Exception("Connection failed"), MagicMock()]
        
        vs = LocalVectorStore()
        
        # Should have fallen back to memory storage
        assert mock_qdrant_client.call_count == 2
        assert mock_qdrant_client.call_args_list[1][0][0] == ":memory:" 
