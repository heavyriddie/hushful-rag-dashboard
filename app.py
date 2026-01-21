"""
Hushful RAG Dashboard
Web interface for managing ChromaDB knowledge base
"""
import os
import logging
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

from chroma_client import ChromaManager

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

# Initialize ChromaDB manager
chroma_manager = None


def get_chroma():
    """Get or create ChromaDB manager."""
    global chroma_manager
    if chroma_manager is None:
        chroma_manager = ChromaManager()
    return chroma_manager


@app.route("/")
def index():
    """Main dashboard page."""
    return render_template("index.html")


@app.route("/api/documents", methods=["GET"])
def list_documents():
    """List all documents in the collection."""
    try:
        chroma = get_chroma()
        docs = chroma.list_documents()
        return jsonify({"success": True, "documents": docs})
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/documents", methods=["POST"])
def add_document():
    """Add a new document."""
    try:
        data = request.json
        content = data.get("content")
        metadata = data.get("metadata", {})

        if not content:
            return jsonify({"success": False, "error": "Content is required"}), 400

        chroma = get_chroma()
        doc_id = chroma.add_document(content, metadata)
        return jsonify({"success": True, "id": doc_id})
    except Exception as e:
        logger.error(f"Error adding document: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/documents/<doc_id>", methods=["PUT"])
def update_document(doc_id):
    """Update an existing document."""
    try:
        data = request.json
        content = data.get("content")
        metadata = data.get("metadata")

        chroma = get_chroma()
        success = chroma.update_document(doc_id, content, metadata)
        return jsonify({"success": success})
    except Exception as e:
        logger.error(f"Error updating document: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    """Delete a document."""
    try:
        chroma = get_chroma()
        success = chroma.delete_document(doc_id)
        return jsonify({"success": success})
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/query", methods=["POST"])
def query_documents():
    """Test retrieval query."""
    try:
        data = request.json
        query = data.get("query")
        n_results = data.get("n_results", 5)

        if not query:
            return jsonify({"success": False, "error": "Query is required"}), 400

        chroma = get_chroma()
        results = chroma.query(query, n_results)
        return jsonify({"success": True, "results": results})
    except Exception as e:
        logger.error(f"Error querying documents: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Get collection statistics."""
    try:
        chroma = get_chroma()
        stats = chroma.get_stats()
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
