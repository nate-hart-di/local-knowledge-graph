import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # --- Local Paths ---
    BASE_DIR = Path(__file__).parent
    DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
    REPOS_DIR = Path(os.getenv("REPOS_DIR", BASE_DIR / "repos"))
    VECTOR_DB_DIR = Path(os.getenv("VECTOR_DB_DIR", BASE_DIR / "vector_db"))

    # --- Ollama Configuration ---
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

    # --- Vector DB ---
    VECTOR_DB_TYPE = os.getenv("VECTOR_DB_TYPE", "qdrant").lower()
    QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

    # --- GitHub ---
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

    # --- Processing ---
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 2))
    EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "auto").lower()

    # --- Supported file types ---
    SUPPORTED_EXTENSIONS = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.php', '.java', '.cpp', '.c',
        '.h', '.hpp', '.cs', '.rb', '.go', '.rs', '.swift', '.kt', '.scala',
        '.md', '.txt', '.json', '.yaml', '.yml', '.xml', '.html', '.css',
        '.scss', '.sass', '.less', '.sql', '.sh', '.bash', '.zsh'
    }
    
    # --- Directories to ignore ---
    IGNORE_DIRS = {
        '.git', 'node_modules', 'vendor', '__pycache__', '.pytest_cache',
        'venv', 'env', '.env', 'dist', 'build', 'target', '.idea', '.vscode'
    }

    def __post_init__(self):
        """Create directories after initialization"""
        self.DATA_DIR.mkdir(exist_ok=True)
        self.REPOS_DIR.mkdir(exist_ok=True)
        self.VECTOR_DB_DIR.mkdir(exist_ok=True)

# Initialize directories
_config = Config()
_config.__post_init__() 
