import logging
import json
from app.config import settings
from app.llm_client import chat_completion
from app.agents.tools import VALID_TOOLS
from app.agents.memory import AgentMemory

logger = logging.getLogger(__name__)

TIER2_SYSTEM_PROMPT = """You are the WORKER (Tier 2) of a high-speed quiz solver.
Your goal is to solve COMPLEX data analysis tasks delegated by the Orchestrator.

You have access to:
- Python Sandbox (pandas, numpy, scipy, matplotlib, geopandas, requests)
- PDF/File Parsing
- Web Scraping (if needed for deeper data)
- API Sourcing (via requests, using provided headers)
- Visualization (charts, maps)

**CRITICAL RULES**:
1. **USE PYTHON FOR EVERYTHING**: Do not do math in your head. Write code.
2. **VERIFY**: Check your results with print statements.
3. **OUTPUT**: JSON ONLY.
   - If you need to run a tool: `{"action": "tool_name", "args": {...}}`
   - If you have the final answer: `{"final_answer": "the answer"}`

### MANDATORY DATA PROTOCOL (Python Sandbox)
You are an autonomous Data Scientist. When writing Python code to analyze CSVs or data files, you MUST follow this defensive coding pattern to prevent errors:

1. **Header Detection**: Never blindly assume the first row is a header. If the task implies the data starts immediately (or if the file looks like a matrix), use logic to detect or handle `header=None`.

2. **Sanitize Inputs**: NEVER assume a column is numeric just because it looks like it. Real-world data is dirty (e.g., "$1,000", "998 ", "NaN").
   - **Rule**: You MUST explicitly convert target columns to numeric types before calculation.
   - **Code Pattern**: Use `df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[^\d\.\-]', '', regex=True), errors='coerce')`.

3. **Verify & Drop**: After conversion, drop NaN values that resulted from bad data to ensure your sum, mean, or filter logic is accurate.

4. **Solve**: Only after cleaning, proceed with the specific logic requested (e.g., sum, product, standard deviation, matrix multiplication).

**Goal**: Your code must be able to run on "dirty" string-heavy CSVs without crashing or giving the wrong answer.

**TOOLS**:
- `python_execute(code)`: Run python code.
- `load_csv_metadata(path)`: Get CSV info.
- `load_pdf(path)`: Extract text/tables from PDF.
- `scrape_url(url)`: Scrape a web page.
- `plot_to_base64(code)`: Generate charts.

**PROCESS**:
1. Analyze the task and context.
2. Formulate a plan (mental or explicit).
3. Execute tools step-by-step.
4. When you have the answer, return it.

### CRITICAL INSTRUCTION
DO NOT explain your plan. DO NOT say "I will now do this." IMMEDIATELY output the Python code inside the tool block.
"""

class Tier2Worker:
    def __init__(self):
        self.model = settings.WORKER_MODEL
        self.memory = AgentMemory()

    async def run(self, task: str, context: dict) -> dict:
        """
        Executes the delegated task.
        """
        logger.info(f"Tier 2 received task: {task[:100]}...")
        self.memory.clear()
        
        # Add initial context to memory/history
        self.memory.add_observation(f"TASK: {task}\nCONTEXT: {json.dumps(context, default=str)}")
        
        # Execution Loop (Max 10 steps)
        for step in range(10):
            messages = [
                {"role": "system", "content": TIER2_SYSTEM_PROMPT},
                {"role": "user", "content": self.memory.get_history_text()}
            ]
            
            try:
                provider_idx, model_idx = self._find_model_indices(self.model)
                response = await chat_completion(messages, provider_index=provider_idx, model_index=model_idx)
                
                result = self._parse_json(response)
                
                if result.get("final_answer") is not None:
                    logger.info(f"Tier 2 finished: {result['final_answer']}")
                    return {"final_answer": result["final_answer"]}
                
                action = result.get("action")
                if action:
                    args = result.get("args", {})
                    logger.info(f"Tier 2 executing: {action}")
                    
                    if action in VALID_TOOLS:
                        tool_result = await VALID_TOOLS[action](args)
                        self.memory.add_tool_call(action, args, tool_result)
                    else:
                        self.memory.add_observation(f"Error: Unknown tool '{action}'")
                else:
                    # No action or final answer?
                    logger.warning("Tier 2 returned no action or final answer.")
                    self.memory.add_observation("Error: You must return valid JSON with 'action' or 'final_answer'.")
                    
            except Exception as e:
                logger.error(f"Tier 2 step failed: {e}")
                self.memory.add_observation(f"Error: {str(e)}")
                
        return {"error": "Tier 2 max steps reached."}

    def _parse_json(self, response: str) -> dict:
        try:
            if "```json" in response:
                import re
                match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
                if match:
                    return json.loads(match.group(1))
            return json.loads(response)
        except Exception:
            return {"error": "Failed to parse JSON response"}

    def _find_model_indices(self, target_model: str):
        from app.llm_client import ALL_PROVIDERS
        for p_i, provider in enumerate(ALL_PROVIDERS):
            if "models" in provider:
                for m_i, model in enumerate(provider["models"]):
                    if model == target_model:
                        return p_i, m_i
        return 0, 0

worker_tier2 = Tier2Worker()
