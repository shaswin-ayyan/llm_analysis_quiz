import asyncio
import json
import os
import logging
logging.basicConfig(level=logging.INFO)
from app.langgraph_agent import app as graph_app, create_thread_config
from app.utils.submitter import submit_answer
from urllib.parse import urljoin

async def run_loop(start_url: str, email: str, secret: str, max_tasks: int = 100):
    current_url = start_url
    history = []
    
    for i in range(max_tasks):
        print(f"\n--- Step {i+1}: {current_url} ---")
        
        # 1. Solve using LangGraph
        initial_state = {
            "email": email,
            "email_offset": len(email),
            "url": current_url,
            "workspace_path": os.path.join(os.getcwd(), "workspace"),
            "messages": [],
            "retry_count": 0,
            "final_answer": None,
            "next_node": None
        }
        
        try:
            # Create checkpointing config for resumable execution
            thread_config = create_thread_config(email, f"live_exam_{i+1}")
            
            # Invoke Graph with checkpointing
            result = await graph_app.ainvoke(initial_state, thread_config)
            answer = result.get("final_answer")
            print(f"Agent Answer: {answer}")
            
            # 2. Submit Answer
            # Handle JSON parsing if needed (similar to Orchestrator logic)
            if isinstance(answer, str):
                try:
                    import json
                    if (answer.startswith("[") and answer.endswith("]")) or \
                       (answer.startswith("{") and answer.endswith("}")):
                        answer = json.loads(answer)
                except:
                    pass
            
            payload = {
                "email": email,
                "secret": secret,
                "url": current_url,
                "answer": answer
            }
            
            # Guess submit URL (usually /submit)
            # But wait, ExtractorAgent finds the submit URL.
            # The LangGraph state doesn't explicitly return submit_url unless we put it in final_answer or state.
            # The `node_web_agent` uses `extractor_agent` which finds it.
            # But `node_data_agent` might not.
            # For this quiz, it's always `https://tds-llm-analysis.s-anand.net/submit` (or relative /submit).
            submit_url = "https://tds-llm-analysis.s-anand.net/submit" 
            
            response = await submit_answer(submit_url, payload)
            
            next_url = None
            error = None
            
            if response and response.get("correct"):
                next_url = response.get("next_url") or response.get("url")
                print(f"[PASS] Correct! Next: {next_url}")
            else:
                error = response.get("message") if response else "Submission failed"
                print(f"[FAIL] Incorrect: {error}")
                # Stop on failure? Or retry?
                # For live test, we usually stop or try to debug.
                # Let's stop to avoid spamming.
                history.append({
                    "url": current_url,
                    "answer": answer,
                    "next_url": None,
                    "error": error
                })
                break
                
            history.append({
                "url": current_url,
                "answer": answer,
                "next_url": next_url,
                "error": None
            })
            
            if next_url:
                current_url = next_url
            else:
                print("No next URL. Finished?")
                break
                
        except Exception as e:
            print(f"Error executing graph: {e}")
            history.append({
                "url": current_url,
                "answer": None,
                "next_url": None,
                "error": str(e)
            })
            break
            
    return history

async def main():
    email = "23f1000266@ds.study.iitm.ac.in"
    secret = "jarvis_execute" # From .env
    start_url = "https://tds-llm-analysis.s-anand.net/project2"
    
    print(f"Starting Live Test (LangGraph) for {email} on {start_url}...")
    
    history = await run_loop(start_url, email, secret)
    
    # Generate Report
    print("\nGenerating Report...")
    md_content = "# Live Test Results (LangGraph)\n\n"
    md_content += f"**URL**: {start_url}\n"
    md_content += f"**Email**: {email}\n\n"
    md_content += "| Step | URL | Answer | Next URL | Error |\n"
    md_content += "| :--- | :--- | :--- | :--- | :--- |\n"
    
    for i, step in enumerate(history):
        url = step['url'].replace("https://tds-llm-analysis.s-anand.net", "")
        next_url = step['next_url'].replace("https://tds-llm-analysis.s-anand.net", "") if step['next_url'] else "None"
        answer = str(step['answer']).replace("\n", " ")[:50] + "..." if step['answer'] else "None"
        error = step['error'] or ""
        
        md_content += f"| {i+1} | `{url}` | `{answer}` | `{next_url}` | {error} |\n"
        
    with open("live_test_results.md", "w", encoding="utf-8") as f:
        f.write(md_content)
        
    print("Report saved to live_test_results.md")

if __name__ == "__main__":
    asyncio.run(main())
