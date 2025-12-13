import asyncio
from app.config import settings
from app.orchestrator import Orchestrator

# Use settings from config.py, do not override unless necessary
# settings.USE_AIPIPE = True 

PORT = 8003
BASE_URL = f"http://localhost:{PORT}"

async def main():
    print(f"Starting Agent against Mock Server at {BASE_URL}...")
    orchestrator = Orchestrator()
    
    # Run the agent
    # Note: The agent expects to start at the index page
    try:
        result = await orchestrator.handle_task(
            start_url=f"{BASE_URL}/index.html",
            email="agent@test.com",
            secret="s3cret"
        )
        
        print("\n--- Agent Result ---")
        print(result)
    except Exception as e:
        print(f"\n--- Agent Failed ---")
        print(e)

if __name__ == "__main__":
    asyncio.run(main())
