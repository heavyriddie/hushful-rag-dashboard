"""
Services for document processing, AI summarization, and expert dialogue.
"""
from .document_extractor import DocumentExtractor
from .url_extractor import URLExtractor
from .summarizer import Summarizer
from .dialogue_service import SocraticDialogue

__all__ = ['DocumentExtractor', 'URLExtractor', 'Summarizer', 'SocraticDialogue']
