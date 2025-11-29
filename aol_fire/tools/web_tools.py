"""
NullForge Web Tools - Search and Content Extraction

Provides web capabilities:
- DuckDuckGo search integration
- URL content extraction
- HTML to markdown conversion
- API documentation fetching
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Type
from urllib.parse import urlparse

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


# =============================================================================
# Input Schemas
# =============================================================================

class WebSearchInput(BaseModel):
    """Input for web search."""
    query: str = Field(..., description="Search query")
    max_results: int = Field(default=5, description="Maximum number of results")
    region: str = Field(default="wt-wt", description="Region code (wt-wt for worldwide)")


class FetchURLInput(BaseModel):
    """Input for fetching URL content."""
    url: str = Field(..., description="URL to fetch")
    extract_text: bool = Field(default=True, description="Extract main text content")
    include_links: bool = Field(default=False, description="Include extracted links")


# =============================================================================
# Tool Implementations
# =============================================================================

class WebSearchTool(BaseTool):
    """
    Search the web using DuckDuckGo.
    
    Features:
    - Privacy-focused search
    - Technical documentation search
    - Code example discovery
    - No API key required
    """
    
    name: str = "web_search"
    description: str = """Search the web for information using DuckDuckGo.

Use this for:
- Finding documentation
- Looking up error messages
- Discovering code examples
- Researching libraries and frameworks
- Getting current information

Returns titles, URLs, and snippets."""
    
    args_schema: Type[BaseModel] = WebSearchInput
    
    def _run(
        self,
        query: str,
        max_results: int = 5,
        region: str = "wt-wt",
    ) -> str:
        try:
            from duckduckgo_search import DDGS
            
            results = []
            
            with DDGS() as ddgs:
                for r in ddgs.text(query, region=region, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    })
            
            if not results:
                return f"No results found for: {query}"
            
            output = [f"🔍 Search results for: {query}\n"]
            
            for i, r in enumerate(results, 1):
                output.append(f"{i}. **{r['title']}**")
                output.append(f"   🔗 {r['url']}")
                output.append(f"   {r['snippet'][:200]}...")
                output.append("")
            
            return "\n".join(output)
            
        except ImportError:
            return "❌ Web search requires 'duckduckgo-search' package. Install with: pip install duckduckgo-search"
        except Exception as e:
            return f"❌ Search error: {str(e)}"


class FetchURLTool(BaseTool):
    """
    Fetch and extract content from URLs.
    
    Features:
    - HTML to text conversion
    - Main content extraction
    - Link extraction
    - Handles various content types
    """
    
    name: str = "fetch_url"
    description: str = """Fetch content from a URL and extract readable text.

Use this for:
- Reading documentation pages
- Extracting API references
- Getting README content from GitHub
- Analyzing web pages

Automatically extracts main content and removes navigation/ads."""
    
    args_schema: Type[BaseModel] = FetchURLInput
    
    def _run(
        self,
        url: str,
        extract_text: bool = True,
        include_links: bool = False,
    ) -> str:
        try:
            import httpx
            
            # Validate URL
            parsed = urlparse(url)
            if not parsed.scheme:
                url = f"https://{url}"
            
            # Fetch content
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; NullForge/2.0; +https://nullforge.io)"
            }
            
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
            
            content_type = response.headers.get("content-type", "")
            
            # Handle different content types
            if "application/json" in content_type:
                import json
                data = response.json()
                return f"📄 JSON from {url}:\n```json\n{json.dumps(data, indent=2)[:5000]}\n```"
            
            if "text/plain" in content_type:
                return f"📄 Text from {url}:\n{response.text[:5000]}"
            
            if "text/html" not in content_type:
                return f"📄 Content type: {content_type}\nSize: {len(response.content):,} bytes"
            
            # Extract text from HTML
            if extract_text:
                try:
                    from trafilatura import extract
                    
                    text = extract(response.text, include_links=include_links)
                    if text:
                        return f"📄 Content from {url}:\n\n{text[:8000]}"
                except ImportError:
                    pass
                
                # Fallback: basic extraction
                try:
                    from bs4 import BeautifulSoup
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Remove script and style elements
                    for element in soup(['script', 'style', 'nav', 'header', 'footer']):
                        element.decompose()
                    
                    text = soup.get_text(separator='\n', strip=True)
                    
                    # Clean up whitespace
                    lines = [line.strip() for line in text.splitlines() if line.strip()]
                    text = '\n'.join(lines)
                    
                    return f"📄 Content from {url}:\n\n{text[:8000]}"
                    
                except ImportError:
                    return f"📄 Raw HTML from {url} ({len(response.text):,} chars)"
            
            return f"📄 Fetched {url} ({len(response.text):,} chars)"
            
        except httpx.HTTPStatusError as e:
            return f"❌ HTTP error {e.response.status_code}: {url}"
        except httpx.RequestError as e:
            return f"❌ Request failed: {str(e)}"
        except Exception as e:
            return f"❌ Error fetching URL: {str(e)}"
