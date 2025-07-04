import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
sys.path.append('..')

# Save original environment
original_env = dict(os.environ)


class TestConfig:
    """Test configuration loading and validation"""
    
    @patch.dict(os.environ, {}, clear=True)
    @patch('config.load_dotenv')
    def test_default_configuration(self, mock_load_dotenv):
        """Test that default configuration loads correctly"""
        # Import after mocking environment
        from config import Config
        config = Config()
        
        # Test default values
        assert config.OLLAMA_BASE_URL == "http://localhost:11434"
        assert config.OLLAMA_EMBEDDING_MODEL == "nomic-embed-text"
        assert config.VECTOR_DB_TYPE == "qdrant"
        assert config.QDRANT_URL == "http://localhost:6333"
        assert config.MAX_FILE_SIZE_MB == 2
        assert config.EMBEDDING_DEVICE == "auto"
        
        # Test paths exist
        assert config.BASE_DIR.exists()
        assert config.DATA_DIR.exists()
        assert config.REPOS_DIR.exists()
        assert config.VECTOR_DB_DIR.exists()
    
    @patch.dict(os.environ, {
        'OLLAMA_BASE_URL': 'http://test-ollama:11434',
        'OLLAMA_EMBEDDING_MODEL': 'test-model',
        'VECTOR_DB_TYPE': 'qdrant',
        'QDRANT_URL': 'http://test-qdrant:6333',
        'MAX_FILE_SIZE_MB': '5',
        'EMBEDDING_DEVICE': 'cpu'
    }, clear=True)
    @patch('config.load_dotenv')
    def test_environment_override(self, mock_load_dotenv):
        """Test that environment variables override defaults"""
        # Clear module cache and reimport
        import sys
        if 'config' in sys.modules:
            del sys.modules['config']
        from config import Config
        config = Config()
        
        assert config.OLLAMA_BASE_URL == "http://test-ollama:11434"
        assert config.OLLAMA_EMBEDDING_MODEL == "test-model"
        assert config.QDRANT_URL == "http://test-qdrant:6333"
        assert config.MAX_FILE_SIZE_MB == 5
        assert config.EMBEDDING_DEVICE == "cpu"
    
    @patch('config.load_dotenv')
    def test_supported_file_extensions(self, mock_load_dotenv):
        """Test that supported file extensions are properly defined"""
        from config import Config
        config = Config()
        
        # Test common programming languages
        assert '.py' in config.SUPPORTED_EXTENSIONS
        assert '.js' in config.SUPPORTED_EXTENSIONS
        assert '.ts' in config.SUPPORTED_EXTENSIONS
        assert '.java' in config.SUPPORTED_EXTENSIONS
        assert '.cpp' in config.SUPPORTED_EXTENSIONS
        
        # Test documentation formats
        assert '.md' in config.SUPPORTED_EXTENSIONS
        assert '.txt' in config.SUPPORTED_EXTENSIONS
        assert '.json' in config.SUPPORTED_EXTENSIONS
        
        # Test that it's a set (no duplicates)
        assert isinstance(config.SUPPORTED_EXTENSIONS, set)
    
    @patch('config.load_dotenv')
    def test_ignore_directories(self, mock_load_dotenv):
        """Test that ignore directories are properly defined"""
        from config import Config
        config = Config()
        
        # Test common ignore patterns
        assert '.git' in config.IGNORE_DIRS
        assert 'node_modules' in config.IGNORE_DIRS
        assert '__pycache__' in config.IGNORE_DIRS
        assert 'venv' in config.IGNORE_DIRS
        
        # Test that it's a set
        assert isinstance(config.IGNORE_DIRS, set)
    
    @patch('config.load_dotenv')
    def test_directory_creation(self, mock_load_dotenv):
        """Test that directories are created on initialization"""
        from config import Config
        config = Config()
        
        # All directories should exist after initialization
        assert config.DATA_DIR.exists()
        assert config.REPOS_DIR.exists()
        assert config.VECTOR_DB_DIR.exists()
        
        # They should be directories
        assert config.DATA_DIR.is_dir()
        assert config.REPOS_DIR.is_dir()
        assert config.VECTOR_DB_DIR.is_dir()
    
    @patch.dict(os.environ, {'GITHUB_TOKEN': 'test-token-123'}, clear=True)
    @patch('config.load_dotenv')
    def test_github_token_loading(self, mock_load_dotenv):
        """Test that GitHub token is loaded from environment"""
        # Clear module cache and reimport
        import sys
        if 'config' in sys.modules:
            del sys.modules['config']
        from config import Config
        config = Config()
        assert config.GITHUB_TOKEN == 'test-token-123'
    
    @patch.dict(os.environ, {}, clear=True)
    @patch('config.load_dotenv')
    def test_github_token_none_when_not_set(self, mock_load_dotenv):
        """Test that GitHub token is None when not set"""
        # Clear module cache and reimport
        import sys
        if 'config' in sys.modules:
            del sys.modules['config']
        from config import Config
        config = Config()
        assert config.GITHUB_TOKEN is None 
