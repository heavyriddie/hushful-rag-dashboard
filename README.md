# Hushful RAG Dashboard

Web dashboard for managing the Hushful knowledge base stored in ChromaDB Cloud.

## Features

- **View Documents**: Browse all documents in the ChromaDB collection
- **Add Documents**: Upload new documents (PDF, text, markdown)
- **Edit Documents**: Update document content and metadata
- **Remove Documents**: Delete documents from the knowledge base
- **Test Retrieval**: Query the knowledge base and see results with similarity scores
- **Metadata Management**: Add source links and categorize documents

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your ChromaDB Cloud credentials
```

3. Run the dashboard:
```bash
python app.py
```

## Environment Variables

```
CHROMA_API_KEY=your_chroma_cloud_api_key
CHROMA_TENANT_ID=your_tenant_id
CHROMA_DATABASE=hushful-testbot
CHROMA_COLLECTION=hushful_knowledge
```

## Tech Stack

- **Backend**: Flask
- **Frontend**: HTML/CSS/JavaScript (simple, no framework)
- **Database**: ChromaDB Cloud
- **Embeddings**: Google Generative AI (same as main bot)

## Related Projects

- [telegram-test](../telegram-test) - Main Hushful Telegram bot
- ChromaDB Cloud: https://trychroma.com
