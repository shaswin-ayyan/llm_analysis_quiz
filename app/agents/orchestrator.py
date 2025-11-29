import logging
import time
import asyncio
import os
import shutil
from app.agents.extractor_agent import extractor_agent
from app.agents.supervisor_agent import supervisor_agent
from app.utils.submitter import submit_answer

logger = logging.getLogger("uvicorn.error")

class Orchestrator:
    def __init__(self):
        self.MAX_QUESTION_TIME = 180 # 3 minutes per question
        self.MAX_RETRIES = 3

    async def handle_task(self, start_url: str, email: str, secret: str):
        """
        Orchestrates the full quiz solving process.
        """
        current_url = start_url
        
        # Create a base workspace for this run
        base_workspace = os.path.join(os.getcwd(), "workspace")
        os.makedirs(base_workspace, exist_ok=True)

        try:
            while True:
                question_start_time = time.time()
                logger.info(f"Processing Quiz URL: {current_url}")

                # 1. Extraction
                try:
                    context = await extractor_agent.extract(current_url, base_workspace)
                except Exception as e:
                    logger.error(f"Extraction failed: {e}")
                    return {"error": "extraction_failed"}

                if not context.get("submit_url"):
                    logger.error("No submit URL found.")
                    return {"error": "no_submit_url"}

                # 2. Reasoning (Retry Loop)
                final_answer = None
                next_url_candidate = None 

                for attempt in range(self.MAX_RETRIES):
                    elapsed = time.time() - question_start_time
                    
                    # TIMEOUT CHECK
                    if elapsed > self.MAX_QUESTION_TIME:
                        logger.warning("Question time limit exceeded.")
                        if next_url_candidate:
                             logger.info("Time limit reached, moving to next URL found in previous failed attempt.")
                             current_url = next_url_candidate
                             break
                        else:
                             logger.error("Time limit reached and no next URL available.")
                             return {"error": "timeout_and_no_next_url"}
                    
                    logger.info(f"Reasoning Attempt {attempt + 1} (Elapsed: {elapsed:.1f}s)")
                    
                    try:
                        context["email"] = email
                        context["secret"] = secret
                        context["quiz_url"] = current_url
                        
                        # Use SUPERVISOR AGENT
                        remaining_time = self.MAX_QUESTION_TIME - (time.time() - question_start_time) - 5
                        if remaining_time < 10: remaining_time = 10
                        
                        final_answer = await asyncio.wait_for(
                            supervisor_agent.run(context),
                            timeout=remaining_time
                        )
                    except asyncio.TimeoutError:
                        logger.error("Supervisor timed out.")
                        continue
                    except Exception as e:
                        logger.error(f"Reasoning failed: {e}")
                        continue
                    
                    if final_answer:
                        # 3. Submission
                        payload = {
                            "email": email,
                            "secret": secret,
                            "url": current_url,
                            "answer": final_answer
                        }
                        
                        logger.info(f"Submitting answer: {final_answer}")
                        response = await submit_answer(context["submit_url"], payload)
                        
                        if response and response.get("correct"):
                            logger.info("Correct answer!")
                            next_url = response.get("url") or response.get("next_url")
                            if next_url:
                                current_url = next_url # Move to next quiz
                                break # Break retry loop, continue main loop (next question)
                            else:
                                return {"status": "completed", "final_message": "No next URL provided."}
                        else:
                            logger.warning(f"Incorrect answer: {response}")
                            # Feedback loop
                            context["question_text"] += f"\n\n[SYSTEM]: Previous Attempt Failed. Server Response: {response}. Try again."
                            
                            next_url = response.get("url") or response.get("next_url")
                            if next_url:
                                next_url_candidate = next_url
                            
                            if (time.time() - question_start_time) > 150 and next_url:
                                logger.warning("Near timeout and incorrect answer. Skipping to next URL.")
                                current_url = next_url
                                break
                    
                else:
                    logger.error("Max retries exhausted for this question.")
                    if next_url_candidate:
                        logger.info("Moving to next URL after retries exhausted.")
                        current_url = next_url_candidate
                    else:
                        return {"error": "max_retries_exhausted"}
        finally:
            if os.path.exists(base_workspace):
                try:
                    shutil.rmtree(base_workspace)
                    logger.info(f"Cleaned up workspace: {base_workspace}")
                except Exception as e:
                    logger.error(f"Failed to clean up workspace: {e}")
