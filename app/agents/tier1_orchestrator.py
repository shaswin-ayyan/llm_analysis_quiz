import logging
import json
from app.config import settings
from app.llm_client import chat_completion
from app.agents.tier2_worker import worker_tier2

logger = logging.getLogger(__name__)

TIER1_SYSTEM_PROMPT = """You are the ORCHESTRATOR (Tier 1) of a high-speed quiz solver.
Your goal is to solve the user's question as FAST as possible.

You have two modes:
1. **FAST PATH (Type 1)**: If the question is simple, direct, or explicitly asks for a specific value/format without complex analysis, SOLVE IT YOURSELF immediately.
   - Examples: "Return the value 42", "What is the capital of France?", "Extract the email from the text below".
   - OUTPUT: `{"final_answer": "your answer"}`

2. **DELEGATE (Type 2/3)**: If the question requires:
   - Complex math or data analysis (CSV, Excel).
   - Python code execution.
   - File downloading and parsing (PDF, Audio).
   - Multi-step reasoning.
   - DELEGATE to the Tier 2 Worker.
   - OUTPUT: `{"delegate_to_tier2": true, "task": "Detailed description for Tier 2", "context": "Any relevant extracted info"}`

**CRITICAL RULES**:
- SPEED IS KEY. Do not delegate trivial tasks.
- If the answer is in the text provided, extract it and return `final_answer`.
- If you delegate, provide a CLEAR task description.
"""

class Tier1Orchestrator:
    def __init__(self):
        self.model = settings.ORCHESTRATOR_MODEL

    async def run(self, context: dict):
        """
        Main entry point for the quiz task.
        """
        question = context.get("question", "")
        # We might need to scrape first if not already done, but Orchestrator usually receives the question.
        # Assuming context has 'question' and 'url'.
        
        logger.info(f"Tier 1 processing question: {question[:100]}...")

        # 1. Analyze/Solve with GPT-4.1 Nano
        messages = [
            {"role": "system", "content": TIER1_SYSTEM_PROMPT},
            {"role": "user", "content": f"QUESTION: {question}\n\nCONTEXT: {json.dumps(context, default=str)[:2000]}"}
        ]

        try:
            # Find model indices for GPT-4.1 Nano
            # We need to look up in ALL_PROVIDERS. 
            # Since we added it to AIPIPE_PROVIDER, we can just pass the model name if our client supports it,
            # but our client needs indices.
            # Let's use a helper or just iterate.
            provider_idx, model_idx = self._find_model_indices(self.model)
            
            response = await chat_completion(messages, provider_index=provider_idx, model_index=model_idx)
            
            # Parse JSON
            result = self._parse_json(response)
            
            if result.get("final_answer") is not None:
                logger.info("Tier 1 FAST PATH triggered.")
                return {"final_answer": result["final_answer"]}
            
            if result.get("delegate_to_tier2"):
                logger.info("Delegating to Tier 2 Worker...")
                # Call Tier 2
                tier2_task = result.get("task", question)
                # Pass full context plus any specific notes
                tier2_result = await worker_tier2.run(tier2_task, context)
                return tier2_result
            
            # Fallback
            logger.warning("Tier 1 did not return final_answer or delegate. Returning raw response.")
            return {"final_answer": str(result)}

        except Exception as e:
            logger.error(f"Tier 1 failed: {e}")
            return {"error": str(e)}

    def _parse_json(self, response: str) -> dict:
        try:
            if "```json" in response:
                import re
                match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
                if match:
                    return json.loads(match.group(1))
            return json.loads(response)
        except Exception:
            return {"final_answer": response} # Fallback to treating string as answer

    def _find_model_indices(self, target_model: str):
        from app.llm_client import ALL_PROVIDERS
        for p_i, provider in enumerate(ALL_PROVIDERS):
            if "models" in provider:
                for m_i, model in enumerate(provider["models"]):
                    if model == target_model:
                        return p_i, m_i
        return 0, 0

tier1_orchestrator = Tier1Orchestrator()
