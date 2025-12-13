import asyncio
import os
from dotenv import load_dotenv
from e2b_code_interpreter import Sandbox

load_dotenv()

async def test_e2b():
    api_key = os.getenv("E2B_API_KEY")
    if not api_key:
        print("❌ E2B_API_KEY not found in environment.")
        return

    print(f"🔑 Found E2B_API_KEY: {api_key[:4]}...{api_key[-4:]}")
    
    import inspect
    from e2b_code_interpreter import Sandbox
    print("🔍 Inspecting Sandbox attributes:")
    print([d for d in dir(Sandbox) if not d.startswith("_")])
    
    try:
        if hasattr(Sandbox, "create"):
            print("🚀 Found Sandbox.create! Trying it...")
            sb = Sandbox.create(api_key=api_key)
        else:
            print("🚀 No .create() method. Trying Sandbox(apiKey=...)")
            sb = Sandbox(apiKey=api_key)
            
        print("✅ Sandbox created successfully!")
        sb.close()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_e2b())
