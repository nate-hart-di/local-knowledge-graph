# PowerShell script to set up local Supabase on Windows and import CSV data
# Run this script from your project directory

Write-Host "🚀 Setting up Local Supabase Database Schema..." -ForegroundColor Green

# Check if Docker is running
try {
    docker ps | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Check if Supabase containers are running
$supabaseDb = docker ps --filter "name=supabase-db" --format "{{.Names}}"
if (-not $supabaseDb) {
    Write-Host "❌ Supabase database container not found. Please start your Supabase stack first." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Found Supabase database container: $supabaseDb" -ForegroundColor Green

# Step 1: Set up the database schema
Write-Host "📝 Creating database schema..." -ForegroundColor Yellow

$schemaSQL = @"
-- Setup script for local Supabase database schema
-- This script prepares the database for CSV import

-- Enable the vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the sources table (matches your existing data structure)
CREATE TABLE IF NOT EXISTS sources (
    source_id text PRIMARY KEY,
    summary text,
    total_word_count integer,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Create the crawled_pages table (matches CSV structure)
CREATE TABLE IF NOT EXISTS crawled_pages (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    url text NOT NULL,
    chunk_number integer NOT NULL,
    content text NOT NULL,
    metadata jsonb,
    source_id text,
    embedding vector(768)
);

-- Create the code_examples table (for future use)
CREATE TABLE IF NOT EXISTS code_examples (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    url text NOT NULL,
    chunk_number integer NOT NULL,
    content text NOT NULL,
    summary text,
    metadata jsonb,
    source_id text,
    created_at timestamp with time zone DEFAULT now(),
    embedding vector(768)
);

-- Create the site_pages table (from your dump)
CREATE TABLE IF NOT EXISTS site_pages (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    url text NOT NULL,
    chunk_number integer NOT NULL,
    title text,
    summary text,
    content text NOT NULL,
    metadata jsonb,
    embedding vector(768),
    created_at timestamp with time zone DEFAULT now()
);

-- Create the match_documents function (updated for crawled_pages)
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding vector(768),
  match_count int DEFAULT 5,
  filter jsonb DEFAULT '{}'
)
RETURNS TABLE (
  id bigint,
  url text,
  chunk_number int,
  content text,
  metadata jsonb,
  source_id text,
  similarity float
)
LANGUAGE plpgsql
AS `$`$
#variable_conflict use_column
BEGIN
  RETURN QUERY
  SELECT
    crawled_pages.id,
    crawled_pages.url,
    crawled_pages.chunk_number,
    crawled_pages.content,
    crawled_pages.metadata,
    crawled_pages.source_id,
    (crawled_pages.embedding <#> query_embedding) * -1 AS similarity
  FROM crawled_pages
  WHERE crawled_pages.metadata @> filter
  ORDER BY crawled_pages.embedding <#> query_embedding
  LIMIT match_count;
END;
`$`$;

-- Create the match_code_examples function
CREATE OR REPLACE FUNCTION match_code_examples(
  query_embedding vector(768),
  match_count int DEFAULT 5,
  filter jsonb DEFAULT '{}'
)
RETURNS TABLE (
  id bigint,
  url text,
  chunk_number int,
  content text,
  summary text,
  metadata jsonb,
  source_id text,
  similarity float
)
LANGUAGE plpgsql
AS `$`$
#variable_conflict use_column
BEGIN
  RETURN QUERY
  SELECT
    code_examples.id,
    code_examples.url,
    code_examples.chunk_number,
    code_examples.content,
    code_examples.summary,
    code_examples.metadata,
    code_examples.source_id,
    (code_examples.embedding <#> query_embedding) * -1 AS similarity
  FROM code_examples
  WHERE code_examples.metadata @> filter
  ORDER BY code_examples.embedding <#> query_embedding
  LIMIT match_count;
END;
`$`$;

-- Create the match_site_pages function
CREATE OR REPLACE FUNCTION match_site_pages(
  query_embedding vector(768),
  match_count int DEFAULT 5,
  filter jsonb DEFAULT '{}'
)
RETURNS TABLE (
  id bigint,
  url text,
  chunk_number int,
  title text,
  summary text,
  content text,
  metadata jsonb,
  similarity float
)
LANGUAGE plpgsql
AS `$`$
#variable_conflict use_column
BEGIN
  RETURN QUERY
  SELECT
    site_pages.id,
    site_pages.url,
    site_pages.chunk_number,
    site_pages.title,
    site_pages.summary,
    site_pages.content,
    site_pages.metadata,
    (site_pages.embedding <#> query_embedding) * -1 AS similarity
  FROM site_pages
  WHERE site_pages.metadata @> filter
  ORDER BY site_pages.embedding <#> query_embedding
  LIMIT match_count;
END;
`$`$;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS crawled_pages_embedding_idx ON crawled_pages USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS code_examples_embedding_idx ON code_examples USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS site_pages_embedding_idx ON site_pages USING ivfflat (embedding vector_cosine_ops);

-- Add foreign key constraints (optional but recommended)
ALTER TABLE crawled_pages ADD CONSTRAINT IF NOT EXISTS fk_crawled_pages_source 
    FOREIGN KEY (source_id) REFERENCES sources(source_id) ON DELETE SET NULL;

ALTER TABLE code_examples ADD CONSTRAINT IF NOT EXISTS fk_code_examples_source 
    FOREIGN KEY (source_id) REFERENCES sources(source_id) ON DELETE SET NULL;

-- Grant permissions
GRANT ALL ON TABLE sources TO postgres, anon, authenticated, service_role;
GRANT ALL ON TABLE crawled_pages TO postgres, anon, authenticated, service_role;
GRANT ALL ON TABLE code_examples TO postgres, anon, authenticated, service_role;
GRANT ALL ON TABLE site_pages TO postgres, anon, authenticated, service_role;

GRANT EXECUTE ON FUNCTION match_documents TO postgres, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION match_code_examples TO postgres, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION match_site_pages TO postgres, anon, authenticated, service_role;
"@

# Execute the schema setup
try {
    $schemaSQL | docker exec -i $supabaseDb psql -U postgres -d postgres
    Write-Host "✅ Database schema created successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to create database schema: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Step 2: Check for CSV file
$csvPath = "$env:USERPROFILE\Downloads\crawled_pages_rows.csv"
if (-not (Test-Path $csvPath)) {
    Write-Host "❌ CSV file not found at: $csvPath" -ForegroundColor Red
    Write-Host "Please ensure crawled_pages_rows.csv is in your Downloads folder" -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ Found CSV file: $csvPath" -ForegroundColor Green

# Step 3: Copy CSV to container
Write-Host "📁 Copying CSV file to container..." -ForegroundColor Yellow
try {
    docker cp $csvPath "${supabaseDb}:/tmp/crawled_pages_rows.csv"
    Write-Host "✅ CSV file copied to container" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to copy CSV file: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Step 4: Import CSV data
Write-Host "📊 Importing CSV data..." -ForegroundColor Yellow

$importSQL = @"
-- Create temporary table for CSV import
CREATE TEMP TABLE temp_crawled_pages (
    id bigint,
    url text,
    chunk_number integer,
    content text,
    metadata jsonb,
    source_id text,
    created_at timestamp with time zone,
    embedding vector(768)
);

-- Import CSV data
\copy temp_crawled_pages FROM '/tmp/crawled_pages_rows.csv' WITH (FORMAT csv, HEADER true);

-- Check data quality
SELECT COUNT(*) as total_csv_rows FROM temp_crawled_pages;
SELECT COUNT(*) as rows_with_content FROM temp_crawled_pages WHERE content IS NOT NULL AND content != '';

-- Insert valid data into main table
INSERT INTO crawled_pages (url, chunk_number, content, metadata, source_id, embedding)
SELECT url, chunk_number, content, metadata, source_id, embedding 
FROM temp_crawled_pages 
WHERE content IS NOT NULL AND content != '';

-- Show final count
SELECT COUNT(*) as imported_rows FROM crawled_pages;

-- Show distribution by source
SELECT source_id, COUNT(*) as pages_count 
FROM crawled_pages 
GROUP BY source_id 
ORDER BY pages_count DESC 
LIMIT 10;
"@

try {
    $importSQL | docker exec -i $supabaseDb psql -U supabase_admin -d postgres
    Write-Host "✅ CSV data imported successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to import CSV data: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Step 5: Clean up
Write-Host "🧹 Cleaning up..." -ForegroundColor Yellow
try {
    docker exec $supabaseDb rm /tmp/crawled_pages_rows.csv
    Write-Host "✅ Temporary files cleaned up" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Warning: Could not clean up temporary file" -ForegroundColor Yellow
}

# Step 6: Final verification
Write-Host "🔍 Final verification..." -ForegroundColor Yellow
$verificationSQL = @"
SELECT 
    'sources' as table_name, 
    COUNT(*) as row_count 
FROM sources
UNION ALL
SELECT 
    'crawled_pages' as table_name, 
    COUNT(*) as row_count 
FROM crawled_pages
UNION ALL
SELECT 
    'code_examples' as table_name, 
    COUNT(*) as row_count 
FROM code_examples
UNION ALL
SELECT 
    'site_pages' as table_name, 
    COUNT(*) as row_count 
FROM site_pages
ORDER BY table_name;
"@

try {
    $verificationSQL | docker exec -i $supabaseDb psql -U postgres -d postgres
} catch {
    Write-Host "⚠️ Warning: Could not verify final state" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 Setup Complete!" -ForegroundColor Green
Write-Host "Your local Supabase database is now ready with:" -ForegroundColor White
Write-Host "  • Vector extension enabled" -ForegroundColor White
Write-Host "  • All required tables created" -ForegroundColor White
Write-Host "  • Match functions for similarity search" -ForegroundColor White
Write-Host "  • Indexes for performance" -ForegroundColor White
Write-Host "  • CSV data imported" -ForegroundColor White
Write-Host ""
Write-Host "You can now use your RAG system with local embeddings! 🚀" -ForegroundColor Green 
