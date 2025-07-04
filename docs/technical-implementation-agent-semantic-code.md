Of course. You are absolutely right. The PRD defines the "what" and "why," but a clear technical implementation plan defines the "how." A great strategy needs an equally great execution plan.

Here is the refined, instruction-oriented blueprint for building `agent-semantic-code` v1.0. This document serves as the direct technical companion to the PRD, providing a step-by-step guide for development.

---

### **Technical Implementation Plan: `agent-semantic-code` v1.0**

This document outlines the specific technical steps, code changes, and file structures required to build the first agent in our Federated Knowledge Mesh. It is based on the data-driven analysis of the `awesome-llm-apps` repository and adheres to our "Ollama-first" principle.

#### **Overall Goal:**

To refactor our existing application into a headless, containerized, API-driven microservice that is configurable, robust, and ready for orchestration.

---

### **Phase 1: Project Structure & Configuration**

**Objective:** Establish a clean file structure and a fully environment-driven configuration system.

**1. Finalize Project Directory Structure:**
Organize the project files as follows. We will remove the Streamlit UI and add the FastAPI entry point.

```
agent-semantic-code/
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── README.md
├── requirements.txt
├── main.py           # <-- NEW: FastAPI entry point
├── cli.py            # (Optional, for debugging)
├── config.py
├── knowledge_graph.py
├── repo_processor.py
└── vector_store.py
```

**2. Update `config.py`:**
Ensure all settings are loaded from environment variables with sensible defaults. This makes the application fully configurable without code changes.

```python
# In config.py
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

    def __post_init__(self):
        # Create directories after initialization
        self.DATA_DIR.mkdir(exist_ok=True)
        self.REPOS_DIR.mkdir(exist_ok=True)
        self.VECTOR_DB_DIR.mkdir(exist_ok=True)
```

**3. Create `.env.example`:**
This file will serve as the template for all user configuration.

```
# Copy this file to .env and fill in your values.

# -- Ollama Configuration --
# If running Ollama on your host Mac and agent in Docker, use this:
OLLAMA_BASE_URL="http://host.docker.internal:11434"
# If running Ollama in the same Docker Compose network, use this:
# OLLAMA_BASE_URL="http://ollama:11434"

# The embedding model to use from Ollama (must be pulled first: `ollama pull nomic-embed-text`)
OLLAMA_EMBEDDING_MODEL="nomic-embed-text"

# -- Vector Database Configuration --
VECTOR_DB_TYPE="qdrant"
QDRANT_URL="http://qdrant:6333"

# -- GitHub Configuration --
# Required for cloning private repositories
GITHUB_TOKEN="ghp_..."

# -- Processing Configuration --
# Max file size in MB to process
MAX_FILE_SIZE_MB=2
# Device for embeddings ('auto', 'cpu', 'mps'). 'auto' will try mps on Mac.
EMBEDDING_DEVICE="auto"
```

---

### **Phase 2: Core Logic - Adapting to Ollama Embeddings**

**Objective:** Decouple the embedding logic from `SentenceTransformer` and use a clean LangChain interface for Ollama.

**1. Update `vector_store.py`:**
Refactor the class to use `langchain_community.embeddings.OllamaEmbeddings`.

```python
# In vector_store.py
from langchain_community.embeddings import OllamaEmbeddings
from config import Config
# ... other imports

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

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        # Rationale: Switch to the LangChain standard method for embedding.
        print(f"Embedding a batch of {len(texts)} documents...")
        return self.embedding_model.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        print(f"Embedding query: '{text[:50]}...'")
        return self.embedding_model.embed_query(text)

    # In your search method, change the call from .encode() to the new embed_query method:
    def search(self, query: str, limit: int = 10, repo_filter: Optional[str] = None) -> List[Dict]:
        query_embedding = self.embed_query(query)
        # ... rest of search logic
```

---

### **Phase 3: The API Layer with FastAPI**

**Objective:** Expose the core `LocalKnowledgeGraph` functionality through a RESTful API.

**1. Create `main.py`:**
This is the new entry point for our service. It will start a `uvicorn` web server.

```python
# In main.py
from fastapi import FastAPI, HTTPException, Body
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

from knowledge_graph import LocalKnowledgeGraph

# --- Pydantic Models for API Data Contracts ---
class AddRepoPayload(BaseModel):
    source: str = Field(..., description="The URL or local path of the repository.")
    name: Optional[str] = Field(None, description="An optional custom name for the repository.")
    is_url: bool = Field(True, description="Specifies if the source is a URL (True) or local path (False).")

class SearchResult(BaseModel):
    path: str
    content: str
    repo_name: str
    score: float
    # ... add other fields you want to expose

# --- FastAPI Application ---
app = FastAPI(
    title="Agent: Semantic Code",
    description="A service for semantic search and analysis of code repositories.",
    version="1.0.0"
)

# Rationale: A single instance of the KG class manages state for the app's lifetime.
kg = LocalKnowledgeGraph()

@app.get("/health", summary="Check service health")
def health_check():
    # Rationale: Essential for any microservice to confirm it's running.
    # We will expand this to check DB/Ollama connections as per the PRD.
    return {"status": "ok"}

@app.post("/repos", summary="Add a new repository")
def add_repo(payload: AddRepoPayload):
    # Rationale: Using Pydantic models provides automatic validation and clear API docs.
    try:
        result = kg.add_repository(payload.source, payload.name, payload.is_url)
        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search", response_model=List[SearchResult], summary="Perform semantic search")
def search(q: str, repo_filter: Optional[str] = None, limit: int = 10):
    # Rationale: Defines a clear response model for API consumers.
    try:
        results = kg.search(query=q, limit=limit, repo_filter=repo_filter)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ... Implement other endpoints: GET /repos, DELETE /repos/{name}, etc.
```

---

### **Phase 4: Containerization & Orchestration**

**Objective:** Package the entire application and its dependencies into a reproducible and deployable stack.

**1. Create `Dockerfile`:**
This file defines how to build our agent's container image.

```Dockerfile
# Use a slim Python image for a smaller final container size
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker's build cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Expose the port the API server will run on
EXPOSE 8000

# The command to run when the container starts
# Rationale: uvicorn is a high-performance ASGI server for FastAPI.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**2. Create `docker-compose.yml`:**
This file orchestrates our agent and its Qdrant dependency.

```yaml
version: '3.8'

services:
  # Our Semantic Code Agent service
  agent-semantic-code:
    build: .
    container_name: agent-semantic-code
    ports:
      - '8000:8000' # Map host port 8000 to container port 8000
    volumes:
      # Mount local directories for data persistence
      - ./data:/app/data
      - ./repos:/app/repos
      - ./vector_db:/app/vector_db
    # Pass environment variables from the .env file on the host
    env_file:
      - .env
    # Ensure Qdrant is started before our agent
    depends_on:
      - qdrant

  # The Qdrant Vector Database service
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    ports:
      - '6333:6333'
      - '6334:6334'
    volumes:
      - ./qdrant_storage:/qdrant/storage
    # Rationale: Critical optimization for M1/M2/M3 Macs to ensure native performance.
    platform: linux/arm64
```

**Important Note on Ollama:** For this setup, we assume Ollama is running **on the host machine** (your Mac). This is the most reliable way to provide GPU access. The `OLLAMA_BASE_URL="http://host.docker.internal:11434"` setting in your `.env` file allows the Docker container to communicate with the Ollama service on your Mac.

This technical plan provides a clear, step-by-step path to building the first agent. It is robust, modular, and directly aligned with our strategic vision and the PRD.
