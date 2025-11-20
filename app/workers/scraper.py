import logging
from urllib.parse import urljoin
from app.utils.browser import render_page_with_retries
import aiohttp
import pandas as pd
from io import StringIO

logger = logging.getLogger(__name__)


async def scrape(url: str):
    """
    Scrapes the quiz page at URL.
    Detects:
      - CSV links
      - PDF links
      - Question text in the page
    Returns dict:
      {
        "type": "csv" or "pdf" or "text",
        "question": "...",
        "file_url": "...",     # if CSV or PDF
        "df": df OR None
      }
    """

    logger.info(f"Scraping {url}")

    # render_page_with_retries returns full HTML after JS execution
    html = await render_page_with_retries(url)

    if not html:
        raise RuntimeError(f"Failed to render page: {url}")

    # 1. Extract question
    question = extract_question(html)
    logger.info(f"Detected question: {question[:100]}...")

    # 2. Check for CSV
    csv_url = find_csv_link(html, url)
    if csv_url:
        logger.info(f"Detected CSV file: {csv_url}")
        df = await load_csv_from_url(csv_url)
        return {
            "type": "csv",
            "question": question,
            "file_url": csv_url,
            "df": df,
        }

    # 3. Check for PDF
    pdf_url = find_pdf_link(html, url)
    if pdf_url:
        logger.info(f"Detected PDF file: {pdf_url}")
        return {
            "type": "pdf",
            "question": question,
            "file_url": pdf_url,
            "df": None,
        }

    # Fallback: text only question
    return {
        "type": "text",
        "question": question,
        "file_url": None,
        "df": None,
    }


# ---------------------------------------------------
# Helpers
# ---------------------------------------------------
def extract_question(html: str) -> str:
    """
    Extract the main question from rendered HTML.
    Looks for:
      - <pre> blocks
      - <p> blocks
      - quiz text content
    """
    import re

    # Try <pre> block (most quiz pages use ATob -> pre)
    pre_match = re.search(r"<pre[^>]*>(.*?)</pre>", html, re.DOTALL)
    if pre_match:
        txt = pre_match.group(1)
        return clean_html_text(txt)

    # Try <div id="result">
    res_match = re.search(r'<div id="result"[^>]*>(.*?)</div>', html, re.DOTALL)
    if res_match:
        txt = res_match.group(1)
        return clean_html_text(txt)

    # Fallback: remove HTML tags
    return clean_html_text(html)


def clean_html_text(txt: str) -> str:
    import re

    # Remove HTML tags
    txt = re.sub(r"<.*?>", "", txt)
    # Normalize whitespace
    return txt.strip()


def find_csv_link(html, base_url):
    import re

    match = re.search(r'href="([^"]+\.csv)"', html)
    if match:
        link = match.group(1)
        return urljoin(base_url, link)
    return None


def find_pdf_link(html: str, base_url: str):
    """
    Detects PDF hyperlink in HTML.
    """
    import re

    match = re.search(r'href="([^"]+\.pdf)"', html)
    if match:
        link = match.group(1)
        if link.startswith("http"):
            return link
        return base_url + "/" + link.lstrip("/")
    return None


async def load_csv_from_url(url: str):
    """
    Load CSV safely. Detects HTML pages masquerading as CSV and handles them.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            raw = await resp.text()

            # Detect HTML error
            if "<html" in raw.lower() or "<!doctype" in raw.lower():
                raise RuntimeError(
                    f"URL returned HTML, not CSV: {url}\nContent snippet: {raw[:200]}"
                )

            # Detect malformed CSV: if lines contain commas mismatch
            # But pandas will handle actual CSV
            try:
                df = pd.read_csv(StringIO(raw))
                return df
            except Exception as e:
                raise RuntimeError(
                    f"Failed to parse CSV from URL: {url}\n"
                    f"Reason: {str(e)}\n"
                    f"First 200 chars: {raw[:200]}"
                )
