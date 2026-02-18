"""
Hushful RAG Dashboard
Web interface for managing ChromaDB knowledge base + Socratic expert dialogue
"""
import os
import logging
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from chroma_client import ChromaManager
from services import DocumentExtractor, URLExtractor, Summarizer
from services.dialogue_service import SocraticDialogue

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
dialogue_service = None


def get_chroma():
    """Get or create ChromaDB manager (retries on failure)."""
    global chroma_manager
    if chroma_manager is None:
        try:
            chroma_manager = ChromaManager()
        except Exception as e:
            logger.error(f"ChromaDB connection failed: {e}")
            raise
    return chroma_manager


def get_summarizer():
    """Get or create Summarizer instance (lazy initialization)."""
    global summarizer
    if summarizer is None:
        summarizer = Summarizer()
    return summarizer


def get_dialogue():
    """Get or create dialogue service (lazy initialization)."""
    global dialogue_service
    if dialogue_service is None:
        dialogue_service = SocraticDialogue()
    return dialogue_service


# =============================================================================
# Authentication
# =============================================================================

DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "hushful-admin-2026")


@app.route("/health")
def health():
    """Health check with env var diagnostics (no auth required)."""
    env_keys = [
        "GOOGLE_API_KEY", "CHROMA_CLOUD_API_KEY", "CHROMA_CLOUD_TENANT",
        "CHROMA_CLOUD_DATABASE", "ANTHROPIC_API_KEY", "DASHBOARD_PASSWORD",
        "FLASK_SECRET_KEY"
    ]
    env_status = {k: ("set" if os.getenv(k) else "MISSING") for k in env_keys}

    chroma_ok = False
    chroma_error = None
    try:
        cm = get_chroma()
        count = cm.collection.count()
        chroma_ok = True
        chroma_error = f"connected, {count} docs"
    except Exception as e:
        chroma_error = str(e)

    return jsonify({
        "status": "ok" if chroma_ok else "degraded",
        "chroma": chroma_error,
        "env": env_status
    })


def auth_required(f):
    """Require authentication for dashboard routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Not authenticated"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login page."""
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == DASHBOARD_PASSWORD:
            session["authenticated"] = True
            return redirect(url_for("index"))
        return render_template("login.html", error="Invalid password")
    return render_template("login.html", error=None)


@app.route("/logout")
def logout():
    """Logout."""
    session.pop("authenticated", None)
    return redirect(url_for("login"))


# =============================================================================
# Main Pages
# =============================================================================

@app.route("/")
@auth_required
def index():
    """Main dashboard page."""
    return render_template("index.html")


# =============================================================================
# Document CRUD
# =============================================================================

@app.route("/api/documents", methods=["GET"])
@auth_required
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
@auth_required
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
@auth_required
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
@auth_required
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
@auth_required
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
@auth_required
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
# Document Upload & Summarization
# =============================================================================

@app.route("/api/upload", methods=["POST"])
@auth_required
def upload_document():
    """Handle file upload and extract text."""
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400

        filename = secure_filename(file.filename)
        file_bytes = file.read()

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
@auth_required
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
@auth_required
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
        logger.error(f"Summarizer configuration error: {e}")
        return jsonify({
            "success": False,
            "error": "Summarization service not configured. Please set ANTHROPIC_API_KEY."
        }), 500
    except Exception as e:
        logger.error(f"Summarization error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# =============================================================================
# Socratic Expert Dialogue
# =============================================================================

@app.route("/api/dialogue", methods=["POST"])
@auth_required
def dialogue_turn():
    """Process one turn of the Socratic expert dialogue."""
    try:
        data = request.json
        messages = data.get("messages", [])
        new_message = data.get("new_message", data.get("message", ""))
        topic = data.get("topic", "")
        consensus_points = data.get("consensus_points", [])

        if not new_message.strip():
            return jsonify({"success": False, "error": "Message is required"}), 400

        # Search existing knowledge for context
        chroma = get_chroma()
        related = chroma.query(new_message, n_results=3)
        related_context = "\n".join([
            f"[Existing: {r['metadata'].get('title', r['id'])}] {r['content'][:500]}"
            for r in related if r.get("similarity", 0) > 0.3
        ])

        dlg = get_dialogue()
        result = dlg.process_turn(
            messages=messages,
            new_message=new_message,
            topic=topic,
            consensus_points=consensus_points,
            related_context=related_context
        )

        return jsonify({
            "success": True,
            "reply": result["reply"],
            "consensus_point": result.get("consensus_point"),
            "related_existing": [
                {"title": r["metadata"].get("title", r["id"]), "similarity": r.get("similarity")}
                for r in related[:3]
            ]
        })

    except Exception as e:
        logger.error(f"Dialogue error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/generate-article", methods=["POST"])
@auth_required
def generate_article():
    """Generate a markdown article from confirmed consensus points."""
    try:
        data = request.json
        topic = data.get("topic", "")
        consensus_points = data.get("consensus_points", [])
        category = data.get("category", "general")

        if not consensus_points:
            return jsonify({"success": False, "error": "No consensus points provided"}), 400

        dlg = get_dialogue()
        article = dlg.generate_article(topic, consensus_points, category)

        return jsonify({
            "success": True,
            "article": article,
            "topic": topic,
            "category": category
        })

    except Exception as e:
        logger.error(f"Article generation error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
