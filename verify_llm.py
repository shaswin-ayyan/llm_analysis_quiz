import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.llm_client import ALL_PROVIDERS

print("LLM Providers Configuration:")
for i, provider in enumerate(ALL_PROVIDERS):
    print(f"{i+1}. {provider['name']} ({provider['type']})")
    print(f"   URL: {provider['url']}")
    print(f"   Models: {provider['models']}")
    print("-" * 20)
