import re
import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def extract_urls(text: str, base_url: str = None) -> list[str]:
    """
    Extracts URLs from text (HTML or plain text).
    Resolves relative URLs if base_url is provided.
    """
    urls = []
    
    # 1. Try parsing as HTML
    try:
        soup = BeautifulSoup(text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if base_url:
                href = urljoin(base_url, href)
            urls.append(href)
    except Exception as e:
        logger.warning(f"HTML parsing failed in extract_urls: {e}")
        
    # 2. Fallback/Additional: Regex for raw URLs in text
    # This regex is a simple one for demonstration; production might need more robust one
    # It finds http/https URLs.
    raw_urls = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*', text)
    for url in raw_urls:
        if url not in urls:
            urls.append(url)
            
    return list(set(urls))
