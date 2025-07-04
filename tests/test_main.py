import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys
sys.path.append('..')

from main import app


class TestFastAPIEndpoints:
    """Test FastAPI application endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @patch('main.kg')
    def test_health_check_success(self, mock_kg, client):
        """Test successful health check"""
        # Mock successful vector store connections
        mock_kg.vector_store.client.get_collections.return_value = []
        mock_kg.vector_store.embed_query.return_value = [0.1, 0.2, 0.3]
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["qdrant_status"] == "ok"
        assert data["ollama_status"] == "ok"
    
    @patch('main.kg')
    def test_health_check_qdrant_failure(self, mock_kg, client):
        """Test health check with Qdrant failure"""
        # Mock Qdrant failure
        mock_kg.vector_store.client.get_collections.side_effect = Exception("Qdrant connection failed")
        mock_kg.vector_store.embed_query.return_value = [0.1, 0.2, 0.3]
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "error" in data["qdrant_status"]
        assert data["ollama_status"] == "ok"
    
    @patch('main.kg')
    def test_health_check_ollama_failure(self, mock_kg, client):
        """Test health check with Ollama failure"""
        # Mock Ollama failure
        mock_kg.vector_store.client.get_collections.return_value = []
        mock_kg.vector_store.embed_query.side_effect = Exception("Ollama connection failed")
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["qdrant_status"] == "ok"
        assert "error" in data["ollama_status"]
    
    @patch('main.kg')
    def test_add_repository_success(self, mock_kg, client):
        """Test successful repository addition"""
        # Mock successful repository addition
        mock_kg.add_repository.return_value = {
            "repo_name": "test_repo",
            "files_processed": 10,
            "documents_added": 10
        }
        
        payload = {
            "source": "https://github.com/test/repo",
            "name": "test_repo",
            "is_url": True
        }
        
        response = client.post("/repos", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["repo_name"] == "test_repo"
        assert data["files_processed"] == 10
        assert data["documents_added"] == 10
        
        # Verify knowledge graph was called correctly
        mock_kg.add_repository.assert_called_once_with(
            "https://github.com/test/repo", "test_repo", True
        )
    
    @patch('main.kg')
    def test_add_repository_error(self, mock_kg, client):
        """Test repository addition with error"""
        # Mock repository addition error
        mock_kg.add_repository.return_value = {
            "error": "Repository not found"
        }
        
        payload = {
            "source": "https://github.com/nonexistent/repo",
            "is_url": True
        }
        
        response = client.post("/repos", json=payload)
        
        assert response.status_code == 400
        assert "Repository not found" in response.json()["detail"]
    
    @patch('main.kg')
    def test_add_repository_exception(self, mock_kg, client):
        """Test repository addition with exception"""
        # Mock exception during repository addition
        mock_kg.add_repository.side_effect = Exception("Unexpected error")
        
        payload = {
            "source": "https://github.com/test/repo",
            "is_url": True
        }
        
        response = client.post("/repos", json=payload)
        
        assert response.status_code == 500
        assert "Unexpected error" in response.json()["detail"]
    
    @patch('main.kg')
    def test_search_success(self, mock_kg, client):
        """Test successful search"""
        # Mock search results
        mock_kg.search.return_value = [
            {
                "path": "test1.py",
                "content": "print('hello')",
                "repo_name": "test_repo",
                "score": 0.9,
                "extension": ".py",
                "size": 100,
                "modified": "2024-01-01"
            },
            {
                "path": "test2.py",
                "content": "print('world')",
                "repo_name": "test_repo",
                "score": 0.8,
                "extension": ".py",
                "size": 200,
                "modified": "2024-01-02"
            }
        ]
        
        response = client.get("/search?q=test%20query&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["path"] == "test1.py"
        assert data[0]["score"] == 0.9
        assert data[1]["path"] == "test2.py"
        assert data[1]["score"] == 0.8
        
        # Verify knowledge graph was called correctly
        mock_kg.search.assert_called_once_with(
            query="test query", limit=5, repo_filter=None
        )
    
    @patch('main.kg')
    def test_search_with_filters(self, mock_kg, client):
        """Test search with repository filter"""
        mock_kg.search.return_value = []
        
        response = client.get("/search?q=test&repo_filter=specific_repo&limit=3")
        
        assert response.status_code == 200
        
        # Verify filters were passed correctly
        mock_kg.search.assert_called_once_with(
            query="test", limit=3, repo_filter="specific_repo"
        )
    
    @patch('main.kg')
    def test_search_exception(self, mock_kg, client):
        """Test search with exception"""
        mock_kg.search.side_effect = Exception("Search failed")
        
        response = client.get("/search?q=test")
        
        assert response.status_code == 500
        assert "Search failed" in response.json()["detail"]
    
    @patch('main.kg')
    def test_list_repos_success(self, mock_kg, client):
        """Test successful repository listing"""
        # Mock repository list
        mock_kg.list_repositories.return_value = [
            {
                "name": "repo1",
                "source": "https://github.com/test/repo1",
                "is_url": True,
                "processed_at": "2024-01-01T00:00:00",
                "files_processed": 10
            },
            {
                "name": "repo2",
                "source": "/local/path/repo2",
                "is_url": False,
                "processed_at": "2024-01-02T00:00:00",
                "files_processed": 20
            }
        ]
        
        response = client.get("/repos")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "repo1"
        assert data[0]["files_processed"] == 10
        assert data[1]["name"] == "repo2"
        assert data[1]["files_processed"] == 20
    
    @patch('main.kg')
    def test_list_repos_exception(self, mock_kg, client):
        """Test repository listing with exception"""
        mock_kg.list_repositories.side_effect = Exception("List failed")
        
        response = client.get("/repos")
        
        assert response.status_code == 500
        assert "List failed" in response.json()["detail"]
    
    @patch('main.kg')
    def test_remove_repo_success(self, mock_kg, client):
        """Test successful repository removal"""
        mock_kg.remove_repository.return_value = True
        
        response = client.delete("/repos/test_repo")
        
        assert response.status_code == 200
        data = response.json()
        assert "removed successfully" in data["message"]
        
        # Verify knowledge graph was called correctly
        mock_kg.remove_repository.assert_called_once_with("test_repo")
    
    @patch('main.kg')
    def test_remove_repo_not_found(self, mock_kg, client):
        """Test repository removal when repo not found"""
        mock_kg.remove_repository.return_value = False
        
        response = client.delete("/repos/nonexistent_repo")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    @patch('main.kg')
    def test_remove_repo_exception(self, mock_kg, client):
        """Test repository removal with exception"""
        mock_kg.remove_repository.side_effect = Exception("Remove failed")
        
        response = client.delete("/repos/test_repo")
        
        assert response.status_code == 500
        assert "Remove failed" in response.json()["detail"]
    
    @patch('main.kg')
    def test_update_repo_success(self, mock_kg, client):
        """Test successful repository update"""
        mock_kg.update_repository.return_value = {
            "repo_name": "test_repo",
            "files_processed": 15,
            "documents_added": 15
        }
        
        response = client.post("/repos/test_repo/update")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Repository 'test_repo' updated successfully."
        assert data["details"]["repo_name"] == "test_repo"
        assert data["details"]["files_processed"] == 15
        
        # Verify knowledge graph was called correctly
        mock_kg.update_repository.assert_called_once_with("test_repo")
    
    @patch('main.kg')
    def test_update_repo_not_found(self, mock_kg, client):
        """Test repository update when repo not found"""
        mock_kg.update_repository.side_effect = ValueError("Repository not found")
        
        response = client.post("/repos/nonexistent_repo/update")
        
        assert response.status_code == 404
        assert "Repository not found" in response.json()["detail"]
    
    @patch('main.kg')
    def test_update_repo_exception(self, mock_kg, client):
        """Test repository update with exception"""
        mock_kg.update_repository.side_effect = Exception("Update failed")
        
        response = client.post("/repos/test_repo/update")
        
        assert response.status_code == 500
        assert "Update failed" in response.json()["detail"]
    
    @patch('main.kg')
    def test_get_stats_success(self, mock_kg, client):
        """Test successful stats retrieval"""
        mock_kg.get_stats.return_value = {
            "total_repositories": 2,
            "total_files": 30,
            "languages": {"Python": 15, "JavaScript": 10, "Markdown": 5},
            "vector_db": {
                "db_type": "qdrant",
                "total_documents": 30,
                "vector_size": 768
            }
        }
        
        response = client.get("/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_repositories"] == 2
        assert data["total_files"] == 30
        assert data["languages"]["Python"] == 15
        assert data["vector_db"]["db_type"] == "qdrant"
    
    @patch('main.kg')
    def test_get_stats_exception(self, mock_kg, client):
        """Test stats retrieval with exception"""
        mock_kg.get_stats.side_effect = Exception("Stats failed")
        
        response = client.get("/stats")
        
        assert response.status_code == 500
        assert "Stats failed" in response.json()["detail"]
    
    def test_invalid_request_body(self, client):
        """Test invalid request body validation"""
        # Missing required 'source' field
        payload = {
            "name": "test_repo",
            "is_url": True
        }
        
        response = client.post("/repos", json=payload)
        
        assert response.status_code == 422  # Validation error
        assert "source" in response.json()["detail"][0]["loc"]
    
    def test_search_missing_query(self, client):
        """Test search without query parameter"""
        response = client.get("/search")
        
        assert response.status_code == 422  # Validation error 
