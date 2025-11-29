import logging
import asyncio
from typing import Dict, Any

from app.agents.tier1_orchestrator import tier1_orchestrator

logger = logging.getLogger(__name__)

class QuizOrchestrator:
    def __init__(self):
        pass

    async def solve_quiz(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrates the quiz solving process using Tier 1 Agent.
        context: { "question_text": ..., "files": ..., "email": ..., "secret": ... }
        """
        logger.info(f"Starting QuizOrchestrator for question: {context.get('question_text')[:50]}...")
        
        try:
            # 1. Validation
            if not context.get("question_text"):
                return {"error": "No question text provided."}
            
            # 2. Run Tier 1 Pipeline
            # We wrap it in a timeout to prevent hanging
            try:
                result = await asyncio.wait_for(
                    tier1_orchestrator.run(context), 
                    timeout=120 # 2 minutes timeout
                )
            except asyncio.TimeoutError:
                logger.error("Tier 1 timed out.")
                return {"error": "Processing timed out."}
            
            # 3. Post-processing
            if result.get("error"):
                logger.error(f"Tier 1 failed: {result['error']}")
                return {"error": result["error"]}
                
            final_answer = result.get("final_answer")
            if final_answer is None:
                return {"error": "No final answer returned."}
                
            return {"final_answer": final_answer}

        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            return {"error": str(e)}

    async def handle_task(self, url: str, email: str, secret: str):
        """
        Main handler called by the background task.
        """
        from app.agents.extractor_agent import extractor_agent
        from app.utils.browser import browser_manager
        import aiohttp
        import json
        
        logger.info(f"Starting quiz task for {email} at {url}")
        
        try:
            # 1. Extraction
            logger.info("Extracting content...")
            extraction = await extractor_agent.extract_content(url)
            
            if extraction.get("error"):
                logger.error(f"Extraction failed: {extraction['error']}")
                return

            question_text = extraction.get("question")
            submit_url = extraction.get("submit_url")
            files = extraction.get("files", [])
            
            # Create context
            context = {
                "email": email,
                "secret": secret,
                "url": url,
                "question_text": question_text,
                "files": files,
                "submit_url": submit_url
            }
            
            # 2. Solve
            logger.info("Solving quiz...")
            result = await self.solve_quiz(context)
            final_answer = result.get("final_answer")
            
            if final_answer:
                # Unwrap if it's a dict from the agent
                if isinstance(final_answer, dict):
                    if "final_answer" in final_answer:
                        final_answer = final_answer["final_answer"]
                    elif "answer" in final_answer:
                        final_answer = final_answer["answer"]

                # 3. Submission
                payload = {
                    "email": email,
                    "secret": secret,
                    "url": url, # Current URL
                    "answer": final_answer
                }
                
                logger.info(f"Submitting answer: {final_answer} to {submit_url}")
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(submit_url, json=payload) as resp:
                        if resp.status == 200:
                            logger.info("Submission SUCCESS")
                            resp_json = await resp.json()
                            logger.info(f"Response: {resp_json}")
                            
                            # Check for next URL
                            next_url = resp_json.get("next_url") or resp_json.get("url")
                            if next_url:
                                logger.info(f"Proceeding to next URL: {next_url}")
                                # Recursive call? Or loop?
                                # For safety, let's just call handle_task again?
                                # But we need to be careful about recursion depth.
                                # Ideally we should have a loop in handle_task.
                                # But for now, let's just call it recursively.
                                await self.handle_task(next_url, email, secret)
                        else:
                            logger.error(f"Submission FAILED: {resp.status}")
                            text = await resp.text()
                            logger.error(f"Response: {text}")
            else:
                logger.error("No answer generated.")
                
        except Exception as e:
            logger.error(f"Task failed: {e}")

orchestrator = QuizOrchestrator()
