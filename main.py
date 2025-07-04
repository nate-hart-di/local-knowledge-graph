from fastapi import FastAPI, HTTPException, Body
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
import traceback

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
    extension: Optional[str] = None
    size: Optional[int] = None
    modified: Optional[str] = None

class RepositoryInfo(BaseModel):
    name: str
    source: str
    is_url: bool
    processed_at: str
    files_processed: int

class HealthResponse(BaseModel):
    status: str
    ollama_status: str
    qdrant_status: str
    message: Optional[str] = None

# --- FastAPI Application ---
app = FastAPI(
    title="Agent: Semantic Code",
    description="A headless microservice for semantic search and analysis of code repositories.",
    version="1.0.0"
)

# Rationale: A single instance of the KG class manages state for the app's lifetime.
kg = LocalKnowledgeGraph()

@app.get("/health", response_model=HealthResponse, summary="Check service health")
def health_check():
    # Rationale: Essential for any microservice to confirm it's running.
    # We will expand this to check DB/Ollama connections as per the PRD.
    try:
        # Test Qdrant connection
        qdrant_status = "ok"
        try:
            kg.vector_store.client.get_collections()
        except Exception as e:
            qdrant_status = f"error: {str(e)}"
        
        # Test Ollama connection
        ollama_status = "ok"
        try:
            # Test embedding to verify Ollama connection
            kg.vector_store.embed_query("test")
        except Exception as e:
            ollama_status = f"error: {str(e)}"
        
        return HealthResponse(
            status="ok",
            ollama_status=ollama_status,
            qdrant_status=qdrant_status
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.post("/repos", summary="Add a new repository")
def add_repo(payload: AddRepoPayload):
    # Rationale: Using Pydantic models provides automatic validation and clear API docs.
    try:
        result = kg.add_repository(payload.source, payload.name, payload.is_url)
        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        # Re-raise HTTPExceptions to preserve status codes
        raise
    except Exception as e:
        print(f"Error adding repository: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search", response_model=List[SearchResult], summary="Perform semantic search")
def search(q: str, repo_filter: Optional[str] = None, limit: int = 10):
    # Rationale: Defines a clear response model for API consumers.
    try:
        results = kg.search(query=q, limit=limit, repo_filter=repo_filter)
        return [SearchResult(**result) for result in results]
    except Exception as e:
        print(f"Error searching: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/repos", response_model=List[RepositoryInfo], summary="List all repositories")
def list_repos():
    try:
        repos = kg.list_repositories()
        return [RepositoryInfo(**repo) for repo in repos]
    except Exception as e:
        print(f"Error listing repositories: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/repos/{repo_name}", summary="Remove a repository")
def remove_repo(repo_name: str):
    try:
        success = kg.remove_repository(repo_name)
        if not success:
            raise HTTPException(status_code=404, detail=f"Repository '{repo_name}' not found")
        return {"message": f"Repository '{repo_name}' removed successfully"}
    except HTTPException:
        # Re-raise HTTPExceptions to preserve status codes
        raise
    except Exception as e:
        print(f"Error removing repository: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/repos/{name}/update", summary="Update a repository")
def update_repository(name: str):
    try:
        result = kg.update_repository(name)
        return {"message": f"Repository '{name}' updated successfully.", "details": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"Error updating repo: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats", summary="Get statistics about the knowledge graph")
def get_stats():
    """
    Provides statistics about the indexed repositories and the vector database.
    """
    try:
        return kg.get_stats()
    except Exception as e:
        print(f"Error getting stats: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
