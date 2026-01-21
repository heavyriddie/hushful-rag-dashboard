# Hushful RAG Dashboard - Claude Code Context

## Project Overview

Web dashboard for managing the Hushful knowledge base in ChromaDB Cloud. Allows viewing, adding, editing, removing documents, and testing retrieval queries.

## Architecture

- **Flask web app** with simple HTML/JS frontend
- **ChromaDB Cloud** for vector storage (same instance as telegram-test bot)
- **Google Generative AI embeddings** (text-embedding-004)

## Key Files

- `app.py` - Flask application entry point
- `chroma_client.py` - ChromaDB Cloud connection and operations
- `templates/` - HTML templates
- `static/` - CSS and JavaScript

## ChromaDB Cloud Connection

Uses same credentials as telegram-test:
- Tenant: from CHROMA_TENANT_ID
- Database: hushful-testbot
- Collection: hushful_knowledge

## Document Schema

Each document has:
- `id`: Unique identifier
- `content`: The text content
- `metadata`:
  - `category`: dietary_fats, food_mental_health, keto_diet, etc.
  - `source`: Original source (optional)
  - `source_link`: URL to source (optional)
  - `created_at`: Timestamp

## Related Project

The main bot is at ../telegram-test - shares the same ChromaDB Cloud instance.
