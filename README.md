# 🧠 Agent: Semantic Code

A headless, containerized microservice for semantic search and analysis of code repositories. This agent understands the semantic meaning of code and provides fast, accurate search capabilities through a REST API.

## 🎯 Purpose

`agent-semantic-code` is designed to:

- Index and understand code repositories semantically
- Provide fast semantic search across your codebase
- Operate completely locally and privately (no external API calls)
- Serve as a building block for larger AI-powered development workflows

## 🏗️ Architecture

- **Headless REST API**: FastAPI-based service with no UI
- **Local & Private**: Uses Ollama for embeddings (no external dependencies)
- **Vector Search**: Qdrant for high-performance semantic search
- **Containerized**: Docker-based deployment for consistency and isolation

## 🚀 Quick Start

### Prerequisites

1. **Docker & Docker Compose** installed on your system
2. **Ollama** running on your host machine with the embedding model:

   ```bash
   # Install Ollama (if not already installed)
   curl -fsSL https://ollama.com/install.sh | sh
   
   # Pull the embedding model
   ollama pull nomic-embed-text
   ```

### Setup & Launch

1. **Start the service:**

   ```bash
   docker-compose up -d
   ```

2. **Verify it's running:**

   ```bash
   curl http://localhost:8000/health
   ```

3. **View interactive API docs:**
   Open `http://localhost:8000/docs` in your browser

## 📚 Complete Usage Guide

### 1. Health Check

Check that all services are running properly:

```bash
curl http://localhost:8000/health
```

**Expected Response:**

```json
{
  "ollama_status": "ok",
  "qdrant_status": "ok",
  "status": "ok"
}
```

### 2. Adding Repositories

#### Add a GitHub Repository

```bash
curl -X POST "http://localhost:8000/repos" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "https://github.com/username/repository",
    "name": "my-project",
    "is_url": true
  }'
```

#### Add a Local Repository

```bash
curl -X POST "http://localhost:8000/repos" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "/path/to/local/project",
    "name": "local-project",
    "is_url": false
  }'
```

**Response Example:**

```json
{
  "documents_added": 157,
  "files_processed": 157,
  "metadata": {
    "languages": {
      "HTML": 23,
      "JavaScript": 45,
      "Python": 89
    },
    "name": "my-project",
    "total_files": 157
  },
  "repo_name": "my-project"
}
```

### 3. Listing Repositories

View all indexed repositories:

```bash
curl "http://localhost:8000/repos"
```

**Response Example:**

```json
[
  {
    "files_processed": 157,
    "is_url": true,
    "name": "my-project",
    "processed_at": "2024-01-15T10:30:00.000Z",
    "source": "https://github.com/username/repository"
  }
]
```

### 4. Semantic Search

#### Basic Search

```bash
curl "http://localhost:8000/search?q=authentication%20logic&limit=5"
```

#### Advanced Search with Repository Filter

```bash
curl "http://localhost:8000/search?q=database%20connection&repo_filter=my-project&limit=10"
```

**Response Example:**

```json
[
  {
    "content": "def authenticate_user(username, password):\n    # Authentication logic here\n    ...",
    "extension": "py",
    "modified": "2024-01-15T08:22:00.000Z",
    "path": "src/auth/login.py",
    "repo_name": "my-project",
    "score": 0.89,
    "size": 1524
  }
]
```

### 5. Repository Management

#### Update a Repository

Re-process a repository to sync with latest changes:

```bash
curl -X POST "http://localhost:8000/repos/my-project/update"
```

#### Remove a Repository

```bash
curl -X DELETE "http://localhost:8000/repos/my-project"
```

### 6. Statistics

Get comprehensive statistics about your knowledge graph:

```bash
curl "http://localhost:8000/stats"
```

**Response Example:**

```json
{
  "languages": {
    "HTML": 39,
    "JavaScript": 156,
    "Python": 203,
    "TypeScript": 89
  },
  "repositories": [
    {
      "files_processed": 157,
      "name": "my-project",
      "processed_at": "2024-01-15T10:30:00.000Z"
    }
  ],
  "total_files": 487,
  "total_repositories": 3,
  "vector_db": {
    "disk_usage": "45.2MB",
    "status": "healthy",
    "vectors_count": 487
  }
}
```

## 🔧 Configuration

Configure the service by editing the `.env` file:

```bash
# Copy example configuration
cp .env.example .env

# Edit with your preferred settings
nano .env
```

**Key Configuration Options:**

```env
# Ollama Configuration
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Qdrant Configuration
QDRANT_URL=http://qdrant:6333

# GitHub Access (for private repos)
GITHUB_TOKEN=your_github_token_here

# Processing Limits
MAX_FILE_SIZE_MB=10
SUPPORTED_EXTENSIONS=.py,.js,.ts,.java,.cpp,.c,.h,.hpp,.cs,.go,.rs,.rb,.php,.swift,.kt,.scala,.clj,.sh,.yaml,.yml,.json,.xml,.html,.css,.scss,.less,.md,.rst,.txt

# Performance
EMBEDDING_DEVICE=auto # Options: auto, cpu, mps, cuda
```

## 🔍 Advanced Usage Examples

### Semantic Search Workflow

```bash
# 1. Add your main project
curl -X POST "http://localhost:8000/repos" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "https://github.com/myorg/main-project",
    "name": "main-project",
    "is_url": true
  }'

# 2. Add a utility library
curl -X POST "http://localhost:8000/repos" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "/Users/me/dev/utils-lib",
    "name": "utils-lib", 
    "is_url": false
  }'

# 3. Search across all repositories
curl "http://localhost:8000/search?q=error%20handling%20patterns&limit=10"

# 4. Search within specific repository
curl "http://localhost:8000/search?q=API%20endpoints&repo_filter=main-project&limit=5"

# 5. Check your knowledge graph stats
curl "http://localhost:8000/stats"
```

### Batch Operations

```bash
# Process multiple repositories
repos=(
  "https://github.com/user/repo1|repo1"
  "https://github.com/user/repo2|repo2"
  "/local/path/repo3|repo3"
)

for repo in "${repos[@]}"; do
  IFS='|' read -r source name <<< "$repo"
  is_url=true
  [[ "$source" == /* ]] && is_url=false

  curl -X POST "http://localhost:8000/repos" \
    -H "Content-Type: application/json" \
    -d "{
      \"source\": \"$source\",
      \"name\": \"$name\",
      \"is_url\": $is_url
    }"
done
```

## 🐳 Docker Management

### Service Management

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f agent-semantic-code

# Stop services
docker-compose down

# Restart services
docker-compose restart
```

### Debugging & Maintenance

```bash
# View Qdrant logs
docker-compose logs qdrant

# Check service status
docker-compose ps

# Clean rebuild after code changes
docker-compose down --rmi all
docker-compose up -d --build

# Complete cleanup (removes all data)
docker-compose down -v
```

## 📁 Data Persistence

Your knowledge graph data is persisted in:

- `./data/` - Repository metadata and processing results
- `./repos/` - Cloned repository files (temporary)
- `./qdrant_storage/` - Vector database storage

## 🔧 Troubleshooting

### Common Issues

#### 1. Ollama Connection Failed

**Problem:** `ollama_status: "error: ..."`

**Solutions:**

- Ensure Ollama is running: `ollama serve`
- Check if model is available: `ollama list`
- Pull model if missing: `ollama pull nomic-embed-text`
- Verify host networking: `docker-compose logs agent-semantic-code`

#### 2. Qdrant Connection Failed

**Problem:** `qdrant_status: "error: ..."`

**Solutions:**

- Restart Qdrant container: `docker-compose restart qdrant`
- Check Qdrant logs: `docker-compose logs qdrant`
- Verify container networking: `docker-compose ps`

#### 3. Repository Processing Fails

**Problem:** Repository addition returns error

**Solutions:**

- Check file size limits in `.env`
- Verify GitHub token permissions for private repos
- Ensure local paths are accessible from container
- Review service logs: `docker-compose logs -f agent-semantic-code`

#### 4. Search Returns No Results

**Problem:** Semantic search returns empty results

**Solutions:**

- Verify repository was processed successfully
- Check that files were indexed: `curl localhost:8000/stats`
- Try broader search terms
- Ensure vector database is populated

### Performance Optimization

```bash
# Use CPU-only embeddings for better compatibility
echo "EMBEDDING_DEVICE=cpu" >> .env

# Increase file size limit for larger codebases
echo "MAX_FILE_SIZE_MB=50" >> .env

# Restart to apply changes
docker-compose restart
```

## 🧪 Testing

Run the test suite:

```bash
# Install test dependencies
pip install pytest

# Run tests
pytest tests/
```

## 📄 License

This project is part of the vessel-copy repository. See the main repository for license information.

## 🤝 Contributing

This agent is designed to be:

- **Single-purpose**: Semantic code understanding only
- **API-first**: All interactions through REST API
- **Containerized**: Fully isolated dependencies
- **Local & Private**: No external API dependencies

When contributing, maintain these architectural principles to ensure the agent can integrate with larger AI-powered development workflows.
