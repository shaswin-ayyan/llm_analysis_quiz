
import asyncio
import logging
from app.orchestrator import Orchestrator

# Configure logging to show INFO level
logging.basicConfig(level=logging.INFO)


async def test_extraction():
    orch = Orchestrator()
    
    # Simulated HTML based on user description (Round 2)
    # Note: The span breaks the URL in raw HTML, but text content should be fine.
    html_content = """
    <html><head></head><body>POST this JSON to <span class="origin">https://tds-llm-analysis.s-anand.net</span>/submit

    <pre>{
      "email": "your email",
      "secret": "your secret",
      "url": "<span class="origin">https://tds-llm-analysis.s-anand.net</span>/demo",
      "answer": "anything you want"
    }
    </pre>

    <script type="module">
    for (const el of document.querySelectorAll(".origin")) {
      el.innerHTML = window.location.origin;
    }
    </script>
    </body></html>
    """
    
    page_url = "https://tds-llm-analysis.s-anand.net/demo"
    
    print("Testing extraction...")
    q_text, res_url, sub_url = orch.extract_question_and_resources(html_content, page_url)
    
    print(f"Question Text: {q_text}")
    print(f"Resource URL: {res_url}")
    print(f"Submit URL: {sub_url}")
    
    if sub_url == "https://tds-llm-analysis.s-anand.net/submit":
        print("SUCCESS: Submit URL found.")
    else:
        print("FAILURE: Submit URL NOT found.")

if __name__ == "__main__":
    asyncio.run(test_extraction())
