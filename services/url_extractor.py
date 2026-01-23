"""
URL content extraction service.
Fetches web pages and extracts readable text content.
"""
import logging
from typing import Optional, Tuple

import html2text
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class URLExtractor:
    """Extracts readable text content from web URLs."""

    TIMEOUT = 30  # seconds
    MAX_CONTENT_SIZE = 10 * 1024 * 1024  # 10MB limit

    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    def extract(self, url: str) -> Tuple[str, str, Optional[str]]:
        """
        Extract text content from a URL.

        Args:
            url: The URL to fetch and extract content from

        Returns:
            Tuple of (extracted_text, page_title, error_message)
            If successful, error_message is None.
        """
        # Validate URL
        if not url:
            return "", "", "URL is required"

        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        try:
            response = requests.get(
                url,
                timeout=self.TIMEOUT,
                headers={
                    'User-Agent': self.USER_AGENT,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                },
                allow_redirects=True
            )
            response.raise_for_status()

            # Check content size
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > self.MAX_CONTENT_SIZE:
                return "", "", "Content too large (>10MB)"

            # Check content type
            content_type = response.headers.get('content-type', '')
            if 'text/html' not in content_type and 'application/xhtml' not in content_type:
                return "", "", f"Unsupported content type: {content_type}"

            # Parse HTML
            soup = BeautifulSoup(response.content, 'lxml')

            # Get title
            title = ""
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
            else:
                # Try og:title or h1
                og_title = soup.find('meta', property='og:title')
                if og_title and og_title.get('content'):
                    title = og_title['content'].strip()
                elif soup.h1:
                    title = soup.h1.get_text().strip()
                else:
                    title = url

            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header',
                                'aside', 'form', 'iframe', 'noscript']):
                element.decompose()

            # Remove common ad/sidebar elements by class/id
            for selector in ['.sidebar', '.advertisement', '.ad', '.ads',
                           '#sidebar', '#advertisement', '.nav', '.menu',
                           '.comment', '.comments', '#comments']:
                for element in soup.select(selector):
                    element.decompose()

            # Convert to markdown/text
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = True
            h.ignore_emphasis = False
            h.body_width = 0  # Don't wrap lines
            h.skip_internal_links = True
            h.inline_links = True

            text = h.handle(str(soup))

            # Clean up excessive whitespace
            lines = text.split('\n')
            cleaned_lines = []
            prev_empty = False

            for line in lines:
                line = line.rstrip()
                is_empty = not line.strip()

                if is_empty:
                    if not prev_empty:
                        cleaned_lines.append('')
                    prev_empty = True
                else:
                    cleaned_lines.append(line)
                    prev_empty = False

            text = '\n'.join(cleaned_lines).strip()

            if not text:
                return "", title, "No text content could be extracted from the URL"

            return text, title, None

        except requests.exceptions.Timeout:
            return "", "", "Request timed out after 30 seconds"
        except requests.exceptions.TooManyRedirects:
            return "", "", "Too many redirects"
        except requests.exceptions.SSLError:
            return "", "", "SSL certificate error"
        except requests.exceptions.ConnectionError:
            return "", "", "Could not connect to the server"
        except requests.exceptions.HTTPError as e:
            return "", "", f"HTTP error: {e.response.status_code}"
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching URL {url}: {e}")
            return "", "", f"Failed to fetch URL: {str(e)}"
        except Exception as e:
            logger.error(f"Error processing URL {url}: {e}")
            return "", "", f"Failed to process content: {str(e)}"
