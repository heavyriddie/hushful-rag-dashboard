"""
ChromaDB Cloud client for RAG dashboard
"""
import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class ChromaManager:
    """Manages ChromaDB Cloud connection and operations."""

    def __init__(self):
        """Initialize ChromaDB Cloud connection."""
        self.api_key = os.getenv("CHROMA_API_KEY")
        self.tenant_id = os.getenv("CHROMA_TENANT_ID")
        self.database = os.getenv("CHROMA_DATABASE", "hushful-testbot")
        self.collection_name = os.getenv("CHROMA_COLLECTION", "hushful_knowledge")

        if not all([self.api_key, self.tenant_id]):
            raise ValueError("CHROMA_API_KEY and CHROMA_TENANT_ID are required")

        # Connect to ChromaDB Cloud
        self.client = chromadb.HttpClient(
            host="api.trychroma.com",
            port=443,
            ssl=True,
            headers={"Authorization": f"Bearer {self.api_key}"},
            tenant=self.tenant_id,
            database=self.database
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Hushful metabolic health knowledge base"}
        )

        logger.info(f"Connected to ChromaDB Cloud: {self.collection_name}")

    def list_documents(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List all documents in the collection."""
        result = self.collection.get(
            limit=limit,
            offset=offset,
            include=["documents", "metadatas"]
        )

        documents = []
        for i, doc_id in enumerate(result["ids"]):
            documents.append({
                "id": doc_id,
                "content": result["documents"][i] if result["documents"] else "",
                "metadata": result["metadatas"][i] if result["metadatas"] else {}
            })

        return documents

    def add_document(
        self,
        content: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """Add a new document to the collection."""
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"

        # Ensure metadata has required fields
        if metadata is None:
            metadata = {}

        metadata["created_at"] = datetime.utcnow().isoformat()

        self.collection.add(
            ids=[doc_id],
            documents=[content],
            metadatas=[metadata]
        )

        logger.info(f"Added document: {doc_id}")
        return doc_id

    def update_document(
        self,
        doc_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Update an existing document."""
        try:
            update_kwargs = {"ids": [doc_id]}

            if content:
                update_kwargs["documents"] = [content]

            if metadata:
                # Get existing metadata and merge
                existing = self.collection.get(ids=[doc_id], include=["metadatas"])
                if existing["metadatas"]:
                    merged = {**existing["metadatas"][0], **metadata}
                else:
                    merged = metadata
                merged["updated_at"] = datetime.utcnow().isoformat()
                update_kwargs["metadatas"] = [merged]

            self.collection.update(**update_kwargs)
            logger.info(f"Updated document: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating document {doc_id}: {e}")
            return False

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the collection."""
        try:
            self.collection.delete(ids=[doc_id])
            logger.info(f"Deleted document: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            return False

    def query(
        self,
        query_text: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Query the collection for similar documents."""
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )

        formatted = []
        for i, doc_id in enumerate(results["ids"][0]):
            formatted.append({
                "id": doc_id,
                "content": results["documents"][0][i] if results["documents"] else "",
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else None,
                "similarity": 1 - results["distances"][0][i] if results["distances"] else None
            })

        return formatted

    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        count = self.collection.count()

        # Get category counts
        all_docs = self.list_documents(limit=1000)
        categories = {}
        for doc in all_docs:
            cat = doc["metadata"].get("category", "uncategorized")
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_documents": count,
            "collection_name": self.collection_name,
            "categories": categories
        }
