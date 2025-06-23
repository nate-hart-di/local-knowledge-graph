# Local AI Stack

A comprehensive local AI development environment with automated RAG workflows, built with Docker Compose.

## 🚀 Quick Start

1. **Start all services:**

   ```bash
   python scripts/start_services.py
   ```

2. **Start with Supabase only (for development):**

   ```bash
   python scripts/start_services.py --profile none
   ```

3. **Access your services:**
   - N8N: http://localhost:5678
   - Open WebUI: http://localhost:8080
   - Flowise: http://localhost:3001
   - Langfuse: http://localhost:3000
   - Neo4j Browser: http://localhost:7474
   - Qdrant: http://localhost:6333
   - Supabase: http://localhost:8000

## 📁 Project Structure

```
local-ai-packaged/
├── scripts/                    # All utility scripts
│   ├── start_services.py      # Main service orchestration
│   ├── n8n_pipe.py           # N8N integration utilities
│   └── n8n-management/       # N8N backup & management tools
├── n8n/                      # N8N data & backups
├── flowise/                  # Flowise custom tools
├── supabase/                 # Supabase configuration
└── docker-compose.yml       # Main service definitions
```

## 🔧 N8N Management

### Backup Your Credentials (Important!)

```bash
# Quick backup
./scripts/n8n-management/backup_now.sh

# Full management interface
./scripts/n8n-management/manage_n8n.sh backup
./scripts/n8n-management/manage_n8n.sh restore
./scripts/n8n-management/manage_n8n.sh status
```

Your N8N credentials are automatically backed up to `n8n/backup/` and restored on startup.

## 📋 Services Included

- **N8N** - Workflow automation and AI agent orchestration
- **Supabase** - Database, auth, and vector storage
- **Ollama** - Local LLM inference
- **Open WebUI** - Chat interface for local models
- **Flowise** - Visual AI workflow builder
- **Langfuse** - LLM observability and analytics
- **Neo4j** - Graph database for knowledge graphs
- **Qdrant** - Vector database for embeddings
- **SearXNG** - Privacy-focused search engine
- **Caddy** - Reverse proxy and SSL termination

## 🐳 Docker Commands

If you prefer docker commands over the Python script:

```bash
# Start Supabase first
docker compose -p localai -f supabase/docker/docker-compose.yml up -d

# Wait for Supabase to be ready
sleep 10

# Start all other services
docker compose -p localai -f docker-compose.yml up -d
```

## 🔒 Environment Setup

1. Copy `.env.example` to `.env`
2. Configure your API keys and settings
3. The stack will automatically handle service dependencies

## 📖 Documentation

- See `scripts/README.md` for detailed script documentation
- Check individual service directories for specific configurations
- N8N workflows and tools are in `n8n-tool-workflows/`

## 🛠 Troubleshooting

- **Port conflicts**: Services use standard ports. Check `docker-compose.override.yml` for custom port mappings
- **N8N credentials lost**: Use `./scripts/n8n-management/backup_now.sh` to save them permanently
- **Services not starting**: Check logs with `docker compose logs [service-name]`

## 📄 License

MIT License - see LICENSE file for details.
