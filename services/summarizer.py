"""
Claude-powered document summarization service.
Generates faithful summaries without editorializing.
"""
import logging
import os
from typing import List, Optional, Tuple

import anthropic

logger = logging.getLogger(__name__)


class Summarizer:
    """Generates faithful summaries using Claude."""

    # Claude context limits - using conservative estimates for input
    MAX_INPUT_CHARS = 100_000  # ~25K tokens approximate
    CHUNK_SIZE = 80_000  # Characters per chunk for very large docs
    CHUNK_OVERLAP = 1000  # Overlap between chunks

    MODEL = "claude-sonnet-4-20250514"

    SYSTEM_PROMPT = """You are a document summarization assistant. Your task is to create FAITHFUL summaries of documents.

CRITICAL INSTRUCTIONS:
- Produce ONLY a faithful summary of the document's content
- Do NOT add your own opinions, analysis, or commentary
- Do NOT editorialize or make value judgments about the content
- Do NOT fact-check or dispute claims in the document
- Do NOT add warnings, caveats, or disclaimers
- Preserve the document's perspective and voice
- Include key facts, claims, and conclusions from the document
- Maintain the document's structure where helpful (sections, main points)

Your summary should allow someone to understand what the document says without reading it, while remaining completely faithful to the original content."""

    def __init__(self):
        """Initialize the Anthropic client."""
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

        self.client = anthropic.Anthropic(api_key=self.api_key)

    def summarize(
        self,
        text: str,
        source_name: str = "document"
    ) -> Tuple[str, Optional[str]]:
        """
        Generate a faithful summary of the text.

        Args:
            text: The document text to summarize
            source_name: Name of the source for context

        Returns:
            Tuple of (summary, error_message)
            If successful, error_message is None.
        """
        if not text or not text.strip():
            return "", "No text content to summarize"

        try:
            # Handle very large documents by chunking
            if len(text) > self.MAX_INPUT_CHARS:
                logger.info(f"Large document ({len(text)} chars), using chunked summarization")
                return self._summarize_large_document(text, source_name)

            return self._summarize_single(text, source_name)

        except anthropic.RateLimitError:
            logger.warning("Anthropic rate limit exceeded")
            return "", "Rate limit exceeded. Please try again in a moment."
        except anthropic.AuthenticationError:
            logger.error("Anthropic authentication failed")
            return "", "API authentication failed. Please check your API key."
        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            return "", f"API error: {str(e)}"
        except Exception as e:
            logger.error(f"Summarization error: {e}")
            return "", f"Failed to generate summary: {str(e)}"

    def _summarize_single(
        self,
        text: str,
        source_name: str
    ) -> Tuple[str, Optional[str]]:
        """Summarize a document that fits in one request."""

        user_message = f"""Please provide a faithful summary of the following document.

Source: {source_name}

---
{text}
---

Provide a comprehensive but concise summary that captures all key points, claims, and conclusions from this document."""

        response = self.client.messages.create(
            model=self.MODEL,
            max_tokens=4096,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}]
        )

        summary = response.content[0].text
        return summary, None

    def _summarize_large_document(
        self,
        text: str,
        source_name: str
    ) -> Tuple[str, Optional[str]]:
        """
        Summarize a large document by chunking and combining summaries.

        Strategy:
        1. Split into chunks
        2. Summarize each chunk
        3. Combine chunk summaries into final summary
        """
        chunks = self._split_into_chunks(text)
        logger.info(f"Large document split into {len(chunks)} chunks")

        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Summarizing chunk {i+1}/{len(chunks)}")
            chunk_summary, error = self._summarize_single(
                chunk,
                f"{source_name} (part {i+1}/{len(chunks)})"
            )
            if error:
                return "", f"Error summarizing part {i+1}: {error}"
            chunk_summaries.append(chunk_summary)

        # If only one chunk after processing, return it directly
        if len(chunk_summaries) == 1:
            return chunk_summaries[0], None

        # Combine summaries into final summary
        combined_text = "\n\n---\n\n".join([
            f"Part {i+1} Summary:\n{s}"
            for i, s in enumerate(chunk_summaries)
        ])

        final_prompt = f"""The following are summaries of different parts of a large document titled "{source_name}".
Please combine them into a single coherent summary that captures all key points.

{combined_text}

Provide a unified summary that flows naturally and captures all important information from all document parts.
Maintain the faithful summarization approach - no editorializing or commentary."""

        response = self.client.messages.create(
            model=self.MODEL,
            max_tokens=4096,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": final_prompt}]
        )

        return response.content[0].text, None

    def _split_into_chunks(self, text: str) -> List[str]:
        """Split text into overlapping chunks, trying to break at paragraph boundaries."""
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.CHUNK_SIZE

            # If this isn't the last chunk, try to break at a paragraph boundary
            if end < len(text):
                # Look for paragraph break (double newline) near the end of chunk
                search_start = max(start, end - 2000)
                break_point = text.rfind('\n\n', search_start, end)

                if break_point > start:
                    end = break_point

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start forward, with overlap
            start = end - self.CHUNK_OVERLAP

        return chunks

    def is_configured(self) -> bool:
        """Check if the summarizer is properly configured."""
        return bool(self.api_key)
