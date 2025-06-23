-- Setup script for local Supabase database schema
-- This script prepares the database for CSV import

-- Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the crawled_pages table
CREATE TABLE IF NOT EXISTS crawled_pages (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    url TEXT NOT NULL,
    chunk_number INT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    source_id TEXT,
    embedding VECTOR(768),  -- Updated to 768 dimensions for local embeddings
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create the code_examples table
CREATE TABLE IF NOT EXISTS code_examples (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    url TEXT NOT NULL,
    chunk_number INT NOT NULL,
    code_example TEXT NOT NULL,
    summary TEXT,
    metadata JSONB,
    embedding VECTOR(768),  -- Updated to 768 dimensions for local embeddings
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create the sources table
CREATE TABLE IF NOT EXISTS sources (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name TEXT NOT NULL,
    url TEXT NOT NULL
);

-- Create the site_pages table
CREATE TABLE IF NOT EXISTS site_pages (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    url TEXT NOT NULL,
    chunk_number INT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    embedding VECTOR(1536),  -- OpenAI embeddings are 1536 dimensions
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(url, chunk_number)  -- Unique constraint to prevent duplicate chunks for the same URL
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS crawled_pages_embedding_idx ON crawled_pages USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS code_examples_embedding_idx ON code_examples USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS site_pages_embedding_idx ON site_pages USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_site_pages_metadata ON site_pages USING gin (metadata);

-- Create the match_documents function
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding VECTOR(768),
  match_count INT DEFAULT 5,
  filter JSONB DEFAULT '{}'
)
RETURNS TABLE (
  id BIGINT,
  url TEXT,
  chunk_number INT,
  content TEXT,
  metadata JSONB,
  source_id TEXT,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
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
$$;

-- Create the match_code_examples function
CREATE OR REPLACE FUNCTION match_code_examples(
  query_embedding VECTOR(768),
  match_count INT DEFAULT 5,
  filter JSONB DEFAULT '{}'
)
RETURNS TABLE (
  id BIGINT,
  url TEXT,
  chunk_number INT,
  code_example TEXT,
  summary TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
#variable_conflict use_column
BEGIN
  RETURN QUERY
  SELECT
    code_examples.id,
    code_examples.url,
    code_examples.chunk_number,
    code_examples.code_example,
    code_examples.summary,
    code_examples.metadata,
    (code_examples.embedding <#> query_embedding) * -1 AS similarity
  FROM code_examples
  WHERE code_examples.metadata @> filter
  ORDER BY code_examples.embedding <#> query_embedding
  LIMIT match_count;
END;
$$;

-- Create the match_site_pages function
CREATE OR REPLACE FUNCTION match_site_pages (
  query_embedding VECTOR(1536),
  match_count INT DEFAULT 10,
  filter JSONB DEFAULT '{}'::JSONB
) RETURNS TABLE (
  id BIGINT,
  url TEXT,
  chunk_number INT,
  title TEXT,
  summary TEXT,
  content TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
#variable_conflict use_column
BEGIN
  RETURN QUERY
  SELECT
    id,
    url,
    chunk_number,
    title,
    summary,
    content,
    metadata,
    1 - (site_pages.embedding <=> query_embedding) AS similarity
  FROM site_pages
  WHERE metadata @> filter
  ORDER BY site_pages.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Enable RLS on the tables
ALTER TABLE crawled_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE code_examples ENABLE ROW LEVEL SECURITY;
ALTER TABLE site_pages ENABLE ROW LEVEL SECURITY;

-- Create a policy that allows anyone to read
CREATE POLICY "Allow public read access"
  ON crawled_pages
  FOR SELECT
  TO public
  USING (true);

CREATE POLICY "Allow public read access"
  ON code_examples
  FOR SELECT
  TO public
  USING (true);

CREATE POLICY "Allow public read access"
  ON site_pages
  FOR SELECT
  TO public
  USING (true);

-- Migration complete!
-- Your database is now ready for local embeddings and public access 
