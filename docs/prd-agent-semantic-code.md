## **Product Requirements Document (PRD): `agent-semantic-code` v1.0**

| **Document Status** | **DRAFT**                                          |
| :------------------ | :------------------------------------------------- |
| **Version**         | 1.0                                                |
| **Date**            | 2024-05-24                                         |
| **Author(s)**       | Nathan Hart, AI Assistant                          |
| **Stakeholders**    | Platform Developer (us), Future Orchestrator Agent |

### **1. Overview & Vision**

This document outlines the requirements for **`agent-semantic-code`**, a headless, containerized microservice designed for the semantic analysis of code repositories. This agent is the foundational component of a larger architectural vision: the **Federated Knowledge Mesh**.

The core problem this project solves is the tendency for complex AI tools to evolve into convoluted, unmaintainable monoliths with conflicting dependencies. The Federated Knowledge Mesh architecture addresses this by creating a "council of specialists"—independent, single-purpose agents that communicate over a standardized API.

`agent-semantic-code` is the first and most crucial specialist: **The Semantic Expert**. Its sole purpose is to understand the _meaning_ of code and provide fast, accurate, and filterable semantic search capabilities.

### **2. The Problem**

Developers and future AI orchestrators need a way to query large codebases based on natural language concepts, not just keywords. Existing solutions often become bloated, combining semantic search, structural analysis, and history tracking into a single, fragile application. This leads to:

- **Dependency Hell:** Conflicting library requirements between different functionalities (e.g., AST parsing vs. vector embeddings).
- **Lack of Scalability:** The entire monolith must be scaled, even if only one feature is under heavy load.
- **Low Resilience:** A failure in one component (e.g., Git history analysis) can bring down the entire system.
- **High Maintenance Overhead:** A single, large codebase is difficult to understand, debug, and extend.

### **3. The Solution: A Headless Microservice**

`agent-semantic-code` will be a standalone, API-driven service that does one thing exceptionally well: it ingests code repositories and exposes their semantic meaning via a RESTful API. It will be 100% private and local, using Ollama for embeddings and Qdrant for vector storage. It will have no UI and will be designed to be consumed by other programs, primarily the future Orchestrator Agent.

### **4. Target Audience & User Personas**

1.  **The Platform Developer (us):** We need a stable, well-documented, and easily deployable service that forms the foundation of the larger mesh. It must be configurable, monitorable, and reliable.
2.  **The Orchestrator Agent (Future Consumer):** This future LangGraph/N8N agent is the primary "user." It needs a simple, predictable, and fast API to query for semantically relevant code snippets to inform its reasoning process.

### **5. Goals & Success Metrics**

| Goal                                          | Metric(s)                                                                                                                             |
| :-------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------ |
| **Provide a stable, deployable service**      | The agent can be deployed with a single `docker-compose up` command. Uptime > 99.9%.                                                  |
| **Deliver fast and relevant semantic search** | `/search` API endpoint response time < 500ms for a query (p95). Search results are demonstrably relevant to natural language queries. |
| **Ensure 100% local and private operation**   | No external network calls are made to third-party AI/embedding services.                                                              |
| **Isolate dependencies effectively**          | The agent runs in a self-contained Docker container with all dependencies defined in `requirements.txt`.                              |
| **Achieve robust data management**            | Adding, updating, and removing repositories is transactional and leaves no orphaned files or data.                                    |

### **6. Core Features & Requirements (V1 Scope)**

#### **Epic 1: Repository Ingestion & Processing**

- **User Story:** As the Platform Developer, I want to add a code repository via an API call so that its contents can be processed and indexed for semantic search.
- **Functional Requirements:**
  - A `POST /repos` endpoint that accepts a JSON payload containing the repository source (URL or local path).
  - The system must handle both public and private (via `GITHUB_TOKEN`) GitHub repositories.
  - The system must handle local file system paths.
  - The ingestion process must be idempotent; re-adding an existing repository will trigger an update, not a duplication.
- **Technical Requirements:**
  - Utilize `GitPython` for cloning and pulling repositories.
  - Use Ollama (`nomic-embed-text` model) via LangChain for creating embeddings.
  - Store processed file content and metadata in the Qdrant vector database.
  - Store repository metadata (source, path, etc.) in a local JSON file (`processed_repos.json`).

#### **Epic 2: Semantic Search API**

- **User Story:** As the Orchestrator Agent, I want to send a natural language query to an API endpoint and receive a ranked list of relevant code snippets.
- **Functional Requirements:**
  - A `GET /search` endpoint.
  - Must accept a mandatory `q` (query) parameter.
  - Must accept optional `repo_filter` (string) and `limit` (integer) parameters.
  - The response must be a JSON array of search results, each containing the file path, content, repository name, and relevance score.
- **Technical Requirements:**
  - The endpoint queries the Qdrant collection using the embedded query vector.
  - Filters are applied at the database level for efficiency.

#### **Epic 3: Repository Lifecycle Management**

- **User Story:** As the Platform Developer, I want to manage the indexed repositories via an API to keep the knowledge graph clean and up-to-date.
- **Functional Requirements:**
  - `GET /repos`: Lists all indexed repositories and their metadata.
  - `DELETE /repos/{repo_name}`: Removes a repository, its indexed vectors, its cloned directory, and all associated metadata.
  - `POST /repos/{repo_name}/update`: Triggers a `git pull` on the repository and re-processes its content.
- **Technical Requirements:**
  - Deletion must be complete, removing data from Qdrant, the file system (`repos/`, `data/`), and `processed_repos.json`.

#### **Epic 4: System Operations & Health**

- **User Story:** As the Platform Developer, I want to check the health and status of the agent and its dependencies to ensure system reliability.
- **Functional Requirements:**
  - A `GET /health` endpoint.
  - The endpoint should return a `200 OK` status and a JSON body confirming the status of:
    - The agent itself ("status": "ok").
    - The connection to the Qdrant database.
    - The connection to the Ollama server.
- **Technical Requirements:**
  - The health check will perform a lightweight operation (e.g., `client.get_collections()` for Qdrant) to verify connectivity.

### **7. Technical Architecture & Stack**

| Component            | Technology                     | Purpose & Validation                                                                        |
| :------------------- | :----------------------------- | :------------------------------------------------------------------------------------------ |
| **API Framework**    | FastAPI & Uvicorn              | High-performance, asynchronous web server for the API.                                      |
| **Containerization** | Docker & Docker Compose        | For creating a reproducible, isolated, and deployable service.                              |
| **Embedding Model**  | Ollama (`nomic-embed-text`)    | 100% local, private text embeddings. Pattern validated by multiple `rag_tutorials`.         |
| **Vector Database**  | Qdrant                         | High-performance vector search with filtering. Pattern validated by `qwen_local_rag_agent`. |
| **Repo Processing**  | GitPython                      | For cloning and managing Git repositories.                                                  |
| **Configuration**    | `python-dotenv`                | Manages environment variables for keys, URLs, and settings.                                 |
| **Core Libraries**   | `langchain-community`, `torch` | For clean integration with Ollama and M1 GPU acceleration.                                  |

### **8. Out of Scope for V1**

To maintain focus and prevent monolith-building, the following are explicitly **out of scope** for this initial version:

- **Any User Interface (Streamlit/Gradio):** This is a headless service only.
- **Structural Code Analysis (AST/Graph DB):** This will be the job of the `Structural-Agent`.
- **Git History Analysis:** This will be the job of the `Time-Travel-Agent`.
- **Direct LLM Integration for Q&A or Code Generation:** This will be the job of the `Orchestrator-Agent`.
- **Advanced document chunking strategies.** (We will embed full files for V1).

### **9. Risks & Mitigation**

| Risk                                                                                                                            | Mitigation                                                                                                                                                           |
| :------------------------------------------------------------------------------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Ollama Performance/Resource Bottleneck:** Ollama can be memory/CPU intensive.                                                 | The `EMBEDDING_DEVICE` setting in `config.py` allows forcing CPU. The architecture allows scaling the Ollama service independently if needed in the future.          |
| **Docker Networking Complexity:** Ensuring containers can communicate (`agent` -> `qdrant`, `agent` -> `ollama`) can be tricky. | Use a clear `docker-compose.yml` with defined service names and networks. Provide clear instructions for `host.docker.internal` for host-to-container communication. |
| **Data Persistence & State Management:** Corrupted or out-of-sync state between Qdrant, JSON metadata, and file system.         | Implement robust error handling and transactional logic for add/remove operations. Provide a `/wipe` or `/reset` endpoint for development to easily start fresh.     |

This PRD provides the definitive blueprint for creating a robust, professional, and scalable foundation for our Federated Knowledge Mesh. It is grounded in sound architectural principles and validated by existing best practices. **Let's begin.**
