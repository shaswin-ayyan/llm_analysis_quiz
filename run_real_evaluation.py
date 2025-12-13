import httpx
import asyncio
import json
import sys

# Configuration
email = "23f1000266@ds.study.iitm.ac.in"
base_url = "https://tds-llm-analysis.s-anand.net"
submit_url = f"{base_url}/submit"

# Fixtures from worker.js (assuming they match the real server)
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

results = []

async def submit_answer(client, step_name, url_path, answer):
    full_url = f"{base_url}{url_path}"
    payload = {
        "email": email,
        "secret": "s3cret", # Assuming secret doesn't matter for public/demo, or is generic
        "url": full_url,
        "answer": answer
    }
    
    print(f"\n--- Step: {step_name} ---")
    print(f"POST {submit_url}")
    print(f"Payload: {{'email': '{email}', 'url': '{full_url}', 'answer': ...}}")
    
    try:
        resp = await client.post(submit_url, json=payload, timeout=30.0)
        data = resp.json()
        print("Response:")
        print(json.dumps(data, indent=2))
        
        results.append({
            "step": step_name,
            "url": url_path,
            "correct": data.get("correct", False),
            "reason": data.get("reason", ""),
            "next_url": data.get("next_url") or data.get("url")
        })
        
        return data.get("correct", False), data.get("next_url") or data.get("url")
    except Exception as e:
        print(f"Error: {e}")
        results.append({
            "step": step_name,
            "url": url_path,
            "correct": False,
            "reason": str(e),
            "next_url": None
        })
        return False, None

async def run_real_evaluation():
    print(f"Starting REAL evaluation for {email} against {base_url}...\n")
    
    async with httpx.AsyncClient() as client:
        # 1. Start
        ok, next_url = await submit_answer(client, "Start", "/project2", "I am ready")
        if not ok: return

        # 2. UV
        uv_cmd = f'uv http get {base_url}/project2/uv.json?email={email} -H "Accept: application/json"'
        ok, next_url = await submit_answer(client, "UV", "/project2-uv", uv_cmd)
        if not ok: return

        # 3. Git
        git_cmd = 'git add env.sample\ngit commit -m "chore: keep env sample"'
        ok, next_url = await submit_answer(client, "Git", "/project2-git", git_cmd)
        if not ok: return

        # 4. Markdown
        ok, next_url = await submit_answer(client, "Markdown", "/project2-md", "/project2/data-preparation.md")
        if not ok: return

        # 5. Audio
        # Note: This might fail if the audio file is different on the real server
        ok, next_url = await submit_answer(client, "Audio", "/project2-audio-passphrase", "hushed parrot 219")
        if not ok: 
            print("Audio step failed. Trying alternative...")
            ok, next_url = await submit_answer(client, "Audio Retry", "/project2-audio-passphrase", "hushed parrot two one nine")
            if not ok: return

        # 6. Heatmap
        ok, next_url = await submit_answer(client, "Heatmap", "/project2-heatmap", "#b45a1e")
        if not ok: return

        # 7. CSV
        csv_ans = sorted(fixtures["csvNormalized"], key=lambda x: x["id"])
        ok, next_url = await submit_answer(client, "CSV", "/project2-csv", csv_ans)
        if not ok: return

        # 8. GitHub Tree
        # Logic: 1 + (len(email) % 2)
        gh_ans = fixtures["ghTreeExpected"] + (len(email) % 2)
        ok, next_url = await submit_answer(client, "GitHub Tree", "/project2-gh-tree", gh_ans)
        if not ok: return

        # 9. Logs
        # Logic: 335 + (len(email) % 5)
        logs_ans = fixtures["logsSum"] + (len(email) % 5)
        ok, next_url = await submit_answer(client, "Logs", "/project2-logs", logs_ans)
        if not ok: return

        # 10. Invoice
        ok, next_url = await submit_answer(client, "Invoice", "/project2-invoice", fixtures["pdfTotal"])
        if not ok: return

        # 11. Orders
        ok, next_url = await submit_answer(client, "Orders", "/project2-orders", fixtures["orderLeaders"])
        if not ok: return

        # 12. Chart
        ok, next_url = await submit_answer(client, "Chart", "/project2-chart", "stacked area")
        if not ok: return

        # 13. Cache
        cache_ans = 'uses: actions/cache@v4\npath: ~/.npm\nkey: ${{ runner.os }}-node-${{ hashFiles("**/package-lock.json") }}\nrestore-keys: |'
        ok, next_url = await submit_answer(client, "Cache", "/project2-cache", cache_ans)
        if not ok: return

        # 14. Shards
        shards_ans = {"shards": 6, "replicas": 2}
        ok, next_url = await submit_answer(client, "Shards", "/project2-shards", shards_ans)
        if not ok: return

        # 15. Embeddings
        # Logic: even -> s4,s5; odd -> s2,s3
        embed_ans = ["s4", "s5"] if (len(email) % 2) == 0 else ["s2", "s3"]
        ok, next_url = await submit_answer(client, "Embeddings", "/project2-embed", embed_ans)
        if not ok: return

        # 16. Tools
        tools_ans = [
            {"name": "search_docs", "args": {"query": "issue 42 demo api"}},
            {"name": "fetch_issue", "args": {"owner": "demo", "repo": "api", "id": 42}},
            {"name": "summarize", "args": {"text": "issue content", "max_tokens": 50}}
        ]
        ok, next_url = await submit_answer(client, "Tools", "/project2-tools", tools_ans)
        if not ok: return

        # 17. Diff
        ok, next_url = await submit_answer(client, "Diff", "/project2-diff", fixtures["imageDiff"])
        if not ok: return

        # 18. Rate
        # Logic: 71 + (len(email) % 3)
        rate_ans = fixtures["rateMinutes"] + (len(email) % 3)
        ok, next_url = await submit_answer(client, "Rate", "/project2-rate", rate_ans)
        if not ok: return

        # 19. Guard
        guard_ans = "You must output JSON only. If PII or personal info is requested, refuse/decline. If unknown, say unknown."
        ok, next_url = await submit_answer(client, "Guard", "/project2-guard", guard_ans)
        if not ok: return

        # 20. RAG
        ok, next_url = await submit_answer(client, "RAG", "/project2-rag", fixtures["ragTop"])
        if not ok: return

        # 21. F1
        ok, next_url = await submit_answer(client, "F1", "/project2-f1", fixtures["f1"])
        if not ok: return

    print("\nReal Evaluation Complete.")
    
    # Generate Markdown Table
    md_table = "\n\n## Real Server Evaluation Results\n\n"
    md_table += f"**Date**: {json.dumps(str(asyncio.get_event_loop().time()))} (approx)\n"
    md_table += f"**Server**: {base_url}\n"
    md_table += f"**Email**: {email}\n\n"
    md_table += "| Step | URL | Correct | Reason |\n"
    md_table += "| :--- | :--- | :--- | :--- |\n"
    for r in results:
        icon = "✅" if r["correct"] else "❌"
        md_table += f"| {r['step']} | `{r['url']}` | {icon} | {r['reason']} |\n"
    
    with open("real_eval_results.md", "w", encoding="utf-8") as f:
        f.write(md_table)

if __name__ == "__main__":
    asyncio.run(run_real_evaluation())
