import logging
from bs4 import BeautifulSoup
from app.utils.browser import render_page_with_retries
from app.config import settings

logger = logging.getLogger(__name__)

async def scrape_url(args):
    """
    Visits a URL and returns the text content.
    args:
      - url: str
    """
    url = args.get("url")
    if not url:
        return {"error": "url argument is required."}
    
    try:
        # Use AI Pipe Proxy as requested
        proxy_base = settings.AIPIPE_PROXY_URL.rstrip("/")
        if not url.startswith(proxy_base):
            target_url = f"{proxy_base}/{url}"
        else:
            target_url = url
            
        logger.info(f"Scraping via Proxy: {target_url}")
        html = await render_page_with_retries(target_url)
        if not html:
            return {"error": "Failed to load page (empty content)."}
        
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n").strip()
        import re
        text = re.sub(r"\n\s*\n", "\n\n", text)
        
        return {"content": text[:10000] + "..." if len(text) > 10000 else text}
    except Exception as e:
        logger.error(f"Scrape tool failed: {e}")
        return {"error": f"Error scraping URL: {str(e)}"}
