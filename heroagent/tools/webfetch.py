"""
HeroAgent WebFetch Tool

Fetch and parse web pages.
"""

import re
import urllib.request
import urllib.error
import ssl
from typing import Dict, Any, Optional
from html.parser import HTMLParser

from .base import BaseTool, ToolResult


class HTMLToTextParser(HTMLParser):
    """Simple HTML to text converter."""

    def __init__(self):
        super().__init__()
        self.result = []
        self.current_tag = None
        self.skip_tags = {'script', 'style', 'noscript', 'iframe'}
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        if tag in self.skip_tags:
            self.skip_depth += 1
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.result.append(f"\n\n{'#' * int(tag[1])} ")
        elif tag == 'p':
            self.result.append('\n\n')
        elif tag == 'br':
            self.result.append('\n')
        elif tag == 'li':
            self.result.append('\n- ')
        elif tag == 'a':
            href = dict(attrs).get('href', '')
            if href and not href.startswith('#'):
                self.result.append('[')
        elif tag == 'div':
            self.result.append('\n')

    def handle_endtag(self, tag):
        if tag in self.skip_tags:
            self.skip_depth -= 1
        elif tag == 'a':
            self.result.append(']')
        self.current_tag = None

    def handle_data(self, data):
        if self.skip_depth > 0:
            return
        text = data.strip()
        if text:
            self.result.append(text + ' ')

    def get_text(self):
        return ''.join(self.result).strip()


class WebFetchTool(BaseTool):
    """Fetch web pages."""

    name = "WebFetch"
    description = "Fetch a web page and return its content as text/markdown."

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.timeout = self.config.get('timeout', 30)
        self.max_size = self.config.get('max_size', 500000)  # 500KB

    def execute(self, url: str, **kwargs) -> ToolResult:
        """Fetch a web page.

        Args:
            url: URL to fetch

        Returns:
            ToolResult with page content
        """
        if not url:
            return ToolResult(output="Error: No URL provided", is_error=True)

        # Ensure HTTPS
        if url.startswith('http://'):
            url = url.replace('http://', 'https://', 1)
        elif not url.startswith('https://'):
            url = 'https://' + url

        try:
            # Create SSL context that doesn't verify (for self-signed certs)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            # Create request with user agent
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; HeroAgent/1.0)',
                    'Accept': 'text/html,application/xhtml+xml,*/*',
                    'Accept-Language': 'en-US,en;q=0.9,el;q=0.8',
                }
            )

            # Fetch
            with urllib.request.urlopen(req, timeout=self.timeout, context=ctx) as response:
                content_type = response.headers.get('Content-Type', '')

                # Read with size limit
                content = response.read(self.max_size)

                # Decode
                encoding = 'utf-8'
                if 'charset=' in content_type:
                    encoding = content_type.split('charset=')[-1].split(';')[0].strip()

                try:
                    html = content.decode(encoding)
                except:
                    html = content.decode('utf-8', errors='ignore')

            # Convert HTML to text
            parser = HTMLToTextParser()
            parser.feed(html)
            text = parser.get_text()

            # Also extract some useful raw HTML elements
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else 'No title'

            # Extract color scheme from CSS
            colors = set(re.findall(r'#[0-9A-Fa-f]{6}|#[0-9A-Fa-f]{3}', html))

            # Extract CSS classes for design hints
            classes = set(re.findall(r'class="([^"]+)"', html))

            # Build response
            result = f"""=== Fetched: {url} ===
Title: {title}

=== Colors Found ===
{', '.join(sorted(colors)[:20]) if colors else 'None detected'}

=== Content ===
{text[:15000]}

=== Raw HTML (excerpt) ===
{html[:5000]}
"""
            return ToolResult(
                output=result,
                metadata={'url': url, 'title': title, 'colors': list(colors)[:10]}
            )

        except urllib.error.HTTPError as e:
            return ToolResult(output=f"HTTP Error {e.code}: {e.reason}", is_error=True)
        except urllib.error.URLError as e:
            return ToolResult(output=f"URL Error: {str(e.reason)}", is_error=True)
        except Exception as e:
            return ToolResult(output=f"Error fetching URL: {str(e)}", is_error=True)

    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema."""
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch"
                }
            },
            "required": ["url"]
        }
