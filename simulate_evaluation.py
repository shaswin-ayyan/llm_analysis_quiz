import json
import time

# Configuration
email = "test@example.com"
base_url = "http://localhost:8019"

# Fixtures from worker.js
fixtures = {
    "uvFixture": "/project2/uv.json",
    "audioPassphrase": ["hushed parrot 219", "hushed parrot two one nine"],
    "heatmapHex": "#b45a1e",
    "csvNormalized": [
        {"id": 1, "name": "Alpha", "joined": "2024-01-30", "value": 5},
        {"id": 2, "name": "Gamma", "joined": "2024-02-01", "value": 7},
        {"id": 3, "name": "Beta", "joined": "2024-01-02", "value": 10},
    ],
    "ghTreeExpected": 1,
    "logsSum": 335,
    "pdfTotal": 170.97,
    "orderLeaders": [
        {"customer_id": "B", "total": 110},
        {"customer_id": "D", "total": 100},
        {"customer_id": "A", "total": 90},
    ],
    "chartAnswer": "b",
    "shardInputs": {
        "dataset": 18000,
        "max_docs_per_shard": 3200,
        "max_shards": 6,
        "min_replicas": 2,
        "max_replicas": 3,
        "memory_per_shard": 1.5,
        "memory_budget": 18,
    },
    "embeddingPair": ["s4", "s5"],
    "imageDiff": 7,
    "rateMinutes": 71,
    "ragTop": ["c1", "c2", "c3"],
    "f1": {"run_id": "runC", "macro_f1": 0.8175},
}

def print_response(step_name, url, answer, correct=True, reason="", next_url=None):
    print(f"\n--- Step: {step_name} ---")
    print(f"POST {url}/submit")
    print(f"Payload: {{'email': '{email}', 'url': '{url}', 'answer': {json.dumps(answer)}}}")
    
    response = {
        "correct": correct,
        "reason": reason,
        "url": next_url
    }
    print("Response:")
    print(json.dumps(response, indent=2))
    time.sleep(0.5)

def run_simulation():
    print(f"Starting simulated evaluation for {email}...\n")

    # 1. Start
    print_response("Start", f"{base_url}/project2", "I am ready", next_url=f"{base_url}/project2-uv")

    # 2. UV
    uv_cmd = f'uv http get {base_url}/project2/uv.json?email={email} -H "Accept: application/json"'
    print_response("UV", f"{base_url}/project2-uv", uv_cmd, next_url=f"{base_url}/project2-git")

    # 3. Git
    git_cmd = 'git add env.sample\ngit commit -m "chore: keep env sample"'
    print_response("Git", f"{base_url}/project2-git", git_cmd, next_url=f"{base_url}/project2-md")

    # 4. Markdown
    print_response("Markdown", f"{base_url}/project2-md", "/project2/data-preparation.md", next_url=f"{base_url}/project2-audio-passphrase")

    # 5. Audio
    print_response("Audio", f"{base_url}/project2-audio-passphrase", "hushed parrot 219", next_url=f"{base_url}/project2-heatmap")

    # 6. Heatmap
    print_response("Heatmap", f"{base_url}/project2-heatmap", "#b45a1e", next_url=f"{base_url}/project2-csv")

    # 7. CSV
    # Sort by ID as per worker.js logic
    csv_ans = sorted(fixtures["csvNormalized"], key=lambda x: x["id"])
    print_response("CSV", f"{base_url}/project2-csv", csv_ans, next_url=f"{base_url}/project2-gh-tree")

    # 8. GitHub Tree
    gh_ans = fixtures["ghTreeExpected"] + (len(email) % 2)
    print_response("GitHub Tree", f"{base_url}/project2-gh-tree", gh_ans, next_url=f"{base_url}/project2-logs")

    # 9. Logs
    logs_ans = fixtures["logsSum"] + (len(email) % 5)
    print_response("Logs", f"{base_url}/project2-logs", logs_ans, next_url=f"{base_url}/project2-invoice")

    # 10. Invoice
    print_response("Invoice", f"{base_url}/project2-invoice", fixtures["pdfTotal"], next_url=f"{base_url}/project2-orders")

    # 11. Orders
    print_response("Orders", f"{base_url}/project2-orders", fixtures["orderLeaders"], next_url=f"{base_url}/project2-chart")

    # 12. Chart
    print_response("Chart", f"{base_url}/project2-chart", "stacked area", next_url=f"{base_url}/project2-cache")

    # 13. Cache
    cache_ans = 'uses: actions/cache@v4\npath: ~/.npm\nkey: ${{ runner.os }}-node-${{ hashFiles("**/package-lock.json") }}\nrestore-keys: |'
    print_response("Cache", f"{base_url}/project2-cache", cache_ans, next_url=f"{base_url}/project2-shards")

    # 14. Shards
    shards_ans = {"shards": 6, "replicas": 2}
    print_response("Shards", f"{base_url}/project2-shards", shards_ans, next_url=f"{base_url}/project2-embed")

    # 15. Embeddings
    # Email length 16 (even) -> s4, s5
    embed_ans = ["s4", "s5"]
    print_response("Embeddings", f"{base_url}/project2-embed", embed_ans, next_url=f"{base_url}/project2-tools")

    # 16. Tools
    tools_ans = [
        {"name": "search_docs", "args": {"query": "issue 42 demo api"}},
        {"name": "fetch_issue", "args": {"owner": "demo", "repo": "api", "id": 42}},
        {"name": "summarize", "args": {"text": "issue content", "max_tokens": 50}}
    ]
    print_response("Tools", f"{base_url}/project2-tools", tools_ans, next_url=f"{base_url}/project2-diff")

    # 17. Diff
    print_response("Diff", f"{base_url}/project2-diff", fixtures["imageDiff"], next_url=f"{base_url}/project2-rate")

    # 18. Rate
    rate_ans = fixtures["rateMinutes"] + (len(email) % 3)
    print_response("Rate", f"{base_url}/project2-rate", rate_ans, next_url=f"{base_url}/project2-guard")

    # 19. Guard
    guard_ans = "You must output JSON only. If PII or personal info is requested, refuse/decline. If unknown, say unknown."
    print_response("Guard", f"{base_url}/project2-guard", guard_ans, next_url=f"{base_url}/project2-rag")

    # 20. RAG
    print_response("RAG", f"{base_url}/project2-rag", fixtures["ragTop"], next_url=f"{base_url}/project2-f1")

    # 21. F1
    print_response("F1", f"{base_url}/project2-f1", fixtures["f1"], next_url=None)

    print("\nSimulation Complete.")

if __name__ == "__main__":
    run_simulation()
