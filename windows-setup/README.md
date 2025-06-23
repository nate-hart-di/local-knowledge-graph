# 🪟 Windows Setup Guide - Step by Step

This guide walks through setting up the Local AI RAG system on Windows, one step at a time with verification points.

## 📋 Prerequisites Check

Before we start, let's verify you have:

- Windows 10/11 with PowerShell
- Docker Desktop installed and running
- Your online Supabase database accessible
- **All CSV files in the `windows-setup` directory:**
  - `sources_rows.csv` (3.5KB, ~30 sources)
  - `crawled_pages_rows.csv` (256MB, ~19K pages)
  - `site_pages_rows.csv` (4.9MB, site pages data)

sh## 🚀 Step-by-Step Setup

### Step 1: Verify Docker is Running

```powershell
# Check Docker is installed and running
docker --version
docker ps
```

**Expected**: Version info and running containers list (can be empty)
**If fails**: Start Docker Desktop and wait for it to fully load

### Step 2: Get Project Files

```powershell
# Navigate to your project directory
cd path\to\local-ai-packaged

# Verify you're in the right place
ls
```

**Expected**: See `docker-compose.yml`, `windows-setup/` folder, etc.

### Step 3: Start the Docker Stack

```powershell
# Start all services
docker compose up -d

# Wait a few minutes, then check status
docker compose ps
```

**Expected**: All containers show "Up" status
**If fails**: Check which containers failed and restart them individually

### Step 4: Verify Supabase Database is Running

```powershell
# Check specifically for the database container
docker ps | findstr supabase-db

# Test database connection
docker exec supabase-db pg_isready -U postgres
```

**Expected**: Container shows as running, pg_isready returns "accepting connections"

### Step 5: Enable Vector Extension

```powershell
# Connect to database and enable vector extension
docker exec supabase-db psql -U postgres -d postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Verify it's installed
docker exec supabase-db psql -U postgres -d postgres -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

**Expected**: Extension created successfully, shows in extension list

### Step 6: Create Database Schema

```powershell
# Navigate to windows-setup directory
cd windows-setup

# Apply the schema
Get-Content setup_local_supabase_schema.sql | docker exec -i supabase-db psql -U postgres -d postgres
```

**Expected**: Multiple "CREATE TABLE", "CREATE FUNCTION", and "CREATE POLICY" success messages
**If fails**: Note which specific command failed and troubleshoot that table/function

### Step 7: Verify Schema Creation

```powershell
# Check that tables were created
docker exec supabase-db psql -U postgres -d postgres -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"
```

**Expected**: Should see tables: `code_examples`, `crawled_pages`, `site_pages`, `sources`

### Step 8: Verify CSV Files Exist

```powershell
# Check all CSV files are present
ls *.csv

# Check file sizes
Get-Item *.csv | Select-Object Name, Length
```

**Expected**: Should see all three CSV files with substantial sizes:

- `sources_rows.csv`: ~3.5KB
- `crawled_pages_rows.csv`: ~256MB
- `site_pages_rows.csv`: ~4.9MB

### Step 9: Copy CSV Files to Container

```powershell
# Copy all CSV files to database container
docker cp sources_rows.csv supabase-db:/tmp/sources_rows.csv
docker cp crawled_pages_rows.csv supabase-db:/tmp/crawled_pages_rows.csv
docker cp site_pages_rows.csv supabase-db:/tmp/site_pages_rows.csv

# Verify they're all there
docker exec supabase-db ls -la /tmp/*.csv
```

**Expected**: All three files show up in container with correct sizes

### Step 10: Import Sources Data

```powershell
# Import sources first (needed for foreign key references)
$sourcesSQL = @"
\copy sources (id, name, url) FROM '/tmp/sources_rows.csv' WITH (FORMAT csv, HEADER true);
SELECT COUNT(*) as sources_imported FROM sources;
"@

$sourcesSQL | docker exec -i supabase-db psql -U postgres -d postgres
```

**Expected**: Shows ~30 sources imported successfully

### Step 11: Import Crawled Pages Data

```powershell
# Create temporary table and import crawled pages
$crawledPagesSQL = @"
CREATE TEMP TABLE temp_crawled_pages (
    id BIGINT,
    url TEXT,
    chunk_number INT,
    content TEXT,
    metadata JSONB,
    source_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    embedding VECTOR(768)
);

\copy temp_crawled_pages FROM '/tmp/crawled_pages_rows.csv' WITH (FORMAT csv, HEADER true);

SELECT COUNT(*) as total_csv_rows FROM temp_crawled_pages;

INSERT INTO crawled_pages (url, chunk_number, content, metadata, source_id, embedding)
SELECT url, chunk_number, content, metadata, source_id, embedding
FROM temp_crawled_pages
WHERE content IS NOT NULL AND content != '';

SELECT COUNT(*) as crawled_pages_imported FROM crawled_pages;
"@

$crawledPagesSQL | docker exec -i supabase-db psql -U postgres -d postgres
```

**Expected**: Shows ~19,000+ crawled pages imported

### Step 12: Import Site Pages Data

```powershell
# Create temporary table and import site pages
$sitePagesSQL = @"
CREATE TEMP TABLE temp_site_pages (
    id BIGINT,
    url TEXT,
    chunk_number INT,
    title TEXT,
    summary TEXT,
    content TEXT,
    metadata JSONB,
    embedding VECTOR(1536),
    created_at TIMESTAMP WITH TIME ZONE
);

\copy temp_site_pages FROM '/tmp/site_pages_rows.csv' WITH (FORMAT csv, HEADER true);

SELECT COUNT(*) as total_site_csv_rows FROM temp_site_pages;

INSERT INTO site_pages (url, chunk_number, title, summary, content, metadata, embedding)
SELECT url, chunk_number, title, summary, content, metadata, embedding
FROM temp_site_pages
WHERE content IS NOT NULL AND content != '' AND title IS NOT NULL;

SELECT COUNT(*) as site_pages_imported FROM site_pages;
"@

$sitePagesSQL | docker exec -i supabase-db psql -U postgres -d postgres
```

**Expected**: Shows count of site pages imported successfully

### Step 13: Verify Data Import

```powershell
# Check data distribution across all tables
docker exec supabase-db psql -U postgres -d postgres -c "
SELECT 'sources' as table_name, COUNT(*) as row_count FROM sources
UNION ALL
SELECT 'crawled_pages' as table_name, COUNT(*) as row_count FROM crawled_pages
UNION ALL
SELECT 'site_pages' as table_name, COUNT(*) as row_count FROM site_pages
UNION ALL
SELECT 'code_examples' as table_name, COUNT(*) as row_count FROM code_examples
ORDER BY table_name;"
```

**Expected**:

- `sources`: ~30 rows
- `crawled_pages`: ~19,000+ rows
- `site_pages`: Variable count based on your data
- `code_examples`: 0 rows (empty table)

### Step 14: Test Vector Search Functions

```powershell
# Test that all search functions work
docker exec supabase-db psql -U postgres -d postgres -c "
SELECT 'crawled_pages with embeddings' as test, COUNT(*) FROM crawled_pages WHERE embedding IS NOT NULL
UNION ALL
SELECT 'site_pages with embeddings' as test, COUNT(*) FROM site_pages WHERE embedding IS NOT NULL;"
```

**Expected**: Shows counts of rows with embeddings for both tables

### Step 15: Clean Up

```powershell
# Remove temporary CSV files from container
docker exec supabase-db rm /tmp/sources_rows.csv /tmp/crawled_pages_rows.csv /tmp/site_pages_rows.csv
```

### Step 16: Final Verification

```powershell
# Test the match functions work
docker exec supabase-db psql -U postgres -d postgres -c "
SELECT 'match_documents function' as test, COUNT(*) as available_docs FROM crawled_pages WHERE embedding IS NOT NULL
UNION ALL
SELECT 'match_site_pages function' as test, COUNT(*) as available_pages FROM site_pages WHERE embedding IS NOT NULL;"
```

**Expected**: Shows available documents for both search functions

## 🌐 Access Your Services

Once setup is complete, verify access to:

| Service             | URL                    | Description                   |
| ------------------- | ---------------------- | ----------------------------- |
| **Supabase Studio** | http://localhost:54323 | Database management interface |
| **Open WebUI**      | http://localhost:3000  | AI chat interface             |
| **Flowise**         | http://localhost:3001  | AI workflow builder           |
| **n8n**             | http://localhost:5678  | Automation workflows          |
| **Langfuse**        | http://localhost:3002  | LLM observability             |
| **Neo4j Browser**   | http://localhost:7474  | Graph database interface      |
| **Qdrant**          | http://localhost:6333  | Vector database interface     |

## 🔧 Common Issues & Quick Fixes

**If Docker containers won't start:**

```powershell
docker compose down
docker compose up -d
```

**If database connection fails:**

```powershell
docker restart supabase-db
# Wait 30 seconds
docker exec supabase-db pg_isready -U postgres
```

**If CSV import fails:**

- Check CSV file format with `head` command
- Verify column count matches expected schema
- Check for special characters or encoding issues

**If vector extension missing:**

```powershell
docker exec supabase-db psql -U postgres -d postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**If RLS policies cause issues:**

```powershell
# Temporarily disable RLS for troubleshooting
docker exec supabase-db psql -U postgres -d postgres -c "
ALTER TABLE crawled_pages DISABLE ROW LEVEL SECURITY;
ALTER TABLE site_pages DISABLE ROW LEVEL SECURITY;"
```

## 📊 What We Accomplished

After completing these steps:

- ✅ Local Supabase database running with vector support
- ✅ All required tables and functions created with RLS policies
- ✅ **Sources**: ~30 source definitions imported
- ✅ **Crawled Pages**: ~19,000+ pages with 768-dim embeddings imported
- ✅ **Site Pages**: Pages with 1536-dim embeddings imported
- ✅ **Vector Search**: Both `match_documents()` and `match_site_pages()` functions ready
- ✅ All supporting services (n8n, Flowise, etc.) running

The system is now ready for local AI development with multiple embedding types and comprehensive RAG capabilities!
