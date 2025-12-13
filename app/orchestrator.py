import logging
import os
import time
import asyncio
from app.langgraph_agent import app as langgraph_app
from app.utils.submitter import submit_answer

logger = logging.getLogger("uvicorn.error")

class Orchestrator:
    """
    Intelligent orchestrator - 180 seconds PER question.
    Continues to all questions if next URL is provided.
    """
    
    def __init__(self):
        self.time_per_question = 180  # seconds PER question (NOT total)
        self.min_time_per_attempt = 5  # minimum seconds per retry
        self.max_retries_per_question = 2  # retry up to 2 times if wrong
    
    async def handle_task(self, url: str, email: str, secret: str, max_questions: int = 100):
        """
        Main handler - 180s per question, continues to all questions.
        """
        current_url = url
        question_count = 0
        total_start = time.time()
        
        while current_url and question_count < max_questions:
            question_count += 1
            question_start = time.time()
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Question {question_count}: {current_url}")
            logger.info(f"⏱️ Fresh timer: {self.time_per_question}s for this question")
            logger.info(f"{'='*60}")
            
            # Try solving (fresh 180s per question)
            success, next_url = await self._solve_with_retries(
                current_url, email, secret, 
                self.time_per_question, question_start
            )
            
            question_time = time.time() - question_start
            
            if success:
                logger.info(f"✅ Question {question_count} SOLVED in {question_time:.1f}s")
            else:
                logger.warning(f"❌ Question {question_count} FAILED after {question_time:.1f}s")
            
            # ALWAYS continue if we have a next URL
            if next_url and next_url != current_url:
                logger.info(f"➡️ Moving to next question")
                current_url = next_url
            else:
                logger.info(f"🛑 No next URL - quiz complete")
                break
        
        total_time = time.time() - total_start
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 FINAL STATS")
        logger.info(f"Questions attempted: {question_count}")
        logger.info(f"Total time: {total_time:.1f}s")
        logger.info(f"Average: {total_time/question_count if question_count > 0 else 0:.1f}s per question")
        logger.info(f"{'='*60}")
    
    async def _solve_with_retries(self, url: str, email: str, secret: str, 
                                   time_budget: float, start_time: float,
                                   max_retries: int = None) -> tuple[bool, str]:
        """
        Solve with retries. Returns (success, next_url).
        """
        if max_retries is None:
            max_retries = self.max_retries_per_question
        
        workspace = os.path.join(os.getcwd(), "workspace")
        os.makedirs(workspace, exist_ok=True)
        last_next_url = None
        
        for attempt in range(1, max_retries + 1):
            # Check time
            elapsed = time.time() - start_time
            remaining = time_budget - elapsed
            
            if remaining < self.min_time_per_attempt:
                logger.warning(f"⏱️ Time exhausted ({elapsed:.1f}s)")
                return False, last_next_url
            
            logger.info(f"🔄 Attempt {attempt}/{max_retries} ({remaining:.1f}s left)")
            
            # Build state
            initial_state = {
                "email": email,
                "email_offset": len(email),
                "url": url,
                "workspace_path": workspace,
                "messages": [],
                "retry_count": attempt - 1,
                "final_answer": None,
                "next_node": None
            }
            
            try:
                # Run LangGraph
                logger.info("🤖 Running LangGraph agent...")
                result = await langgraph_app.ainvoke(initial_state)
                answer = result.get("final_answer")
                logger.info(f"💡 Answer: {answer}")
                
                # Submit
                response = await submit_answer(url, email, secret, answer)
                
                if response:
                    next_url = response.get("url") or response.get("next_url")
                    is_correct = response.get("correct", False)
                    
                    if next_url:
                        last_next_url = next_url
                    
                    if is_correct:
                        logger.info(f"✅ CORRECT!")
                        return True, next_url
                    else:
                        error_msg = response.get("message", "Unknown")
                        logger.warning(f"❌ Wrong: {error_msg}")
                        
                        # Retry if we have time
                        if attempt < max_retries and remaining > 10:
                            await asyncio.sleep(1)
                            continue
                        # Otherwise return next_url to continue
                        elif next_url:
                            logger.info(f"⏭️ Continuing to next")
                            return False, next_url
                else:
                    logger.error(f"❌ No response")
                    
            except Exception as e:
                logger.error(f"❌ Error: {e}", exc_info=True)
        
        # Exhausted retries
        logger.error(f"❌ Failed after {max_retries} attempts")
        return False, last_next_url