import asyncio
from app.agents.tools import scrape_url_tool

async def test_scrape():
    print("Testing scrape_url_tool...")
    # Use a reliable public URL for testing
    url = "https://example.com"
    
    result = await scrape_url_tool({"url": url}, None)
    
    if isinstance(result, dict) and "content" in result:
        print("SUCCESS: Scraped content.")
        print(f"Preview: {result['content'][:100]}...")
    else:
        print(f"FAILURE: {result}")

if __name__ == "__main__":
    asyncio.run(test_scrape())
