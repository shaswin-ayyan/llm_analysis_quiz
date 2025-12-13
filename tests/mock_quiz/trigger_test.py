import requests
import json
import time

def run_test():
    url = "http://127.0.0.1:8000/solve"
    payload = {
        "url": "http://127.0.0.1:8011",
        "email": "test_user@example.com",
        "secret": "jarvis_execute"
    }
    
    print(f"Sending request to {url}...")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("\n[OK] Request accepted!")
            print("Response:", response.json())
            print("\nThe agent is now working in the background.")
            print("Check the terminal output of the Main App (Port 8000) to see the logs.")
            print("Check the terminal output of the Mock Server (Port 8010) to see the traffic.")
        else:
            print(f"\n[ERROR] Request failed with status {response.status_code}")
            print("Response:", response.text)
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        print("Make sure the Main App is running on port 8000.")

if __name__ == "__main__":
    # Wait a moment for servers to fully start if running immediately
    time.sleep(2)
    run_test()
