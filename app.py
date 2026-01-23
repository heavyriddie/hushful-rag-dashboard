"""
Hushful RAG Dashboard
Web interface for managing ChromaDB knowledge base
"""
import os
import logging
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from chroma_client import ChromaManager
from services import DocumentExtractor, URLExtractor, Summarizer

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

# Configure upload limits (50MB max)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# Initialize services
chroma_manager = None
document_extractor = DocumentExtractor()
url_extractor = URLExtractor()
summarizer = None


def get_chroma():
    """Get or create ChromaDB manager."""
    global chroma_manager
    if chroma_manager is None:
        chroma_manager = ChromaManager()
    return chroma_manager


def get_summarizer():
    """Get or create Summarizer instance (lazy initialization)."""
    global summarizer
    if summarizer is None:
        summarizer = Summarizer()
    return summarizer


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


# =============================================================================
# Document Upload & Summarization Endpoints
# =============================================================================

@app.route("/api/upload", methods=["POST"])
def upload_document():
    """
    Handle file upload and extract text.
    Returns extracted text for summarization step.
    """
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400

        filename = secure_filename(file.filename)
        file_bytes = file.read()

        # Extract text
        text, error = document_extractor.extract(file_bytes, filename)

        if error:
            return jsonify({"success": False, "error": error}), 400

        if not text.strip():
            return jsonify({
                "success": False,
                "error": "No text content could be extracted from the file"
            }), 400

        return jsonify({
            "success": True,
            "filename": filename,
            "text": text,
            "char_count": len(text),
            "word_count": len(text.split())
        })

    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/extract-url", methods=["POST"])
def extract_url():
    """Extract text content from a URL."""
    try:
        data = request.json
        url = data.get("url")

        if not url:
            return jsonify({"success": False, "error": "URL is required"}), 400

        text, title, error = url_extractor.extract(url)

        if error:
            return jsonify({"success": False, "error": error}), 400

        if not text.strip():
            return jsonify({
                "success": False,
                "error": "No text content could be extracted from the URL"
            }), 400

        return jsonify({
            "success": True,
            "url": url,
            "title": title,
            "text": text,
            "char_count": len(text),
            "word_count": len(text.split())
        })

    except Exception as e:
        logger.error(f"URL extraction error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/summarize", methods=["POST"])
def summarize_text():
    """Generate a faithful summary of the provided text using Claude."""
    try:
        data = request.json
        text = data.get("text")
        source_name = data.get("source_name", "document")

        if not text:
            return jsonify({"success": False, "error": "Text is required"}), 400

        summ = get_summarizer()
        summary, error = summ.summarize(text, source_name)

        if error:
            return jsonify({"success": False, "error": error}), 400

        return jsonify({
            "success": True,
            "summary": summary,
            "original_length": len(text),
            "summary_length": len(summary)
        })

    except ValueError as e:
        # Missing API key
        logger.error(f"Summarizer configuration error: {e}")
        return jsonify({
            "success": False,
            "error": "Summarization service not configured. Please set ANTHROPIC_API_KEY."
        }), 500
    except Exception as e:
        logger.error(f"Summarization error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
