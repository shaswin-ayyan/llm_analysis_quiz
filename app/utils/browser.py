from playwright.async_api import async_playwright, Error as PlaywrightError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from loguru import logger

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10),
       retry=retry_if_exception_type(PlaywrightError))
async def render_page_with_retries(url: str, timeout: int = 30) -> str:
    logger.info(f"Rendering page: {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"], headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until='networkidle', timeout=timeout*1000)
        content = await page.content()
        await browser.close()
        return content
