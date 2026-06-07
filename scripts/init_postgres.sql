-- Initialize PostgreSQL database
-- This script runs once when the postgres container is created.
-- The main database (pdf_rag) is created automatically by the environment variables,
-- but we can add custom schemas, extensions, or default data here if needed.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Additional setup (if any) can be placed below
