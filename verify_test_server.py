import requests
import time
import sys

BASE_URL = "http://localhost:8004"

def test_static_files():
    print("Testing static files...")
    # Test project2.html
    resp = requests.get(f"{BASE_URL}/project2.html")
    assert resp.status_code == 200, f"Failed to get /project2.html: {resp.status_code}"
    assert "Project 2 entry" in resp.text, "Content mismatch in /project2.html"
    
    # Test project2-uv (no extension)
    resp = requests.get(f"{BASE_URL}/project2-uv")
    assert resp.status_code == 200, f"Failed to get /project2-uv: {resp.status_code}"
    assert "Craft the <em>command string</em>" in resp.text, "Content mismatch in /project2-uv"
    print("Static files OK")

def test_submit_project2():
    print("Testing /project2 submission...")
    payload = {
        "email": "test@example.com",
        "secret": "s3cret",
        "url": f"{BASE_URL}/project2",
        "answer": "Start"
    }
    resp = requests.post(f"{BASE_URL}/submit", json=payload)
    data = resp.json()
    if not data.get("correct"):
        print(f"DEBUG: Response data: {data}")
    assert data.get("correct") == True, f"Expected correct, got {data}"
    assert data["url"] == f"{BASE_URL}/project2-uv?email=test%40example.com", f"Next URL mismatch: {data.get('url')}"
    print("/project2 submission OK")

def test_submit_project2_uv():
    print("Testing /project2-uv submission...")
    # Correct answer
    answer = f"uv http get {BASE_URL}/project2/uv.json?email=test%40example.com -H \"Accept: application/json\""
    payload = {
        "email": "test@example.com",
        "secret": "s3cret",
        "url": f"{BASE_URL}/project2-uv",
        "answer": answer
    }
    resp = requests.post(f"{BASE_URL}/submit", json=payload)
    data = resp.json()
    assert data["correct"] == True, f"Expected correct, got {data}"
    assert "project2-git" in data["url"], f"Next URL mismatch: {data.get('url')}"
    
    # Incorrect answer
    payload["answer"] = "wrong answer"
    resp = requests.post(f"{BASE_URL}/submit", json=payload)
    data = resp.json()
    assert data["correct"] == False, f"Expected incorrect, got {data}"
    print("/project2-uv submission OK")

if __name__ == "__main__":
    try:
        # Wait for server to start
        time.sleep(2)
        test_static_files()
        test_submit_project2()
        test_submit_project2_uv()
        print("\nALL TESTS PASSED")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
