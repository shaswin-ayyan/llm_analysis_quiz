import logging
import json
import re
from app.config import settings
from app.core.router import call_llm
from app.core.memory import AgentMemory
from app.core.controller import Controller
from app.agents.worker_python import execute_python
from app.agents.worker_tools import execute_tool
from app.agents.worker_audio import transcribe_audio

logger = logging.getLogger(__name__)

class SupervisorAgent:
    def __init__(self):
        self.model = settings.SUPERVISOR_MODEL
        self.memory = AgentMemory()
        self.controller = Controller()
        with open("app/prompts/supervisor_prompt.txt", "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

    async def run(self, context: dict) -> dict:
        self.memory.clear()
        self.controller = Controller() # Reset controller
        
        # Initial Context
        question = context.get("question_text", "")
        files = context.get("files", {})
        
        # Check FAST PATH (if answer is explicitly in text)
        # Simple heuristic: if the question text contains "The answer is X", we might skip.
        # But let's let the LLM decide in the first step.

        # Add initial observation
        initial_obs = f"QUESTION: {question}\nFILES: {json.dumps(files, default=str)}"
        
        # Process Audio Files immediately if present (Supervisor rule: Audio Worker transcribes only)
        if files.get("audio"):
            for audio_file in files["audio"]:
                logger.info(f"Supervisor dispatching audio: {audio_file}")
                transcript = await transcribe_audio(audio_file)
                initial_obs += f"\n[AUDIO TRANSCRIPT ({audio_file})]: {transcript}"

        self.memory.add_observation(initial_obs)

        # Loop
        while True:
            # 1. Prepare Messages
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": self.memory.get_history_text() + f"\nOBSERVATION: {self.memory.last_observation}"}
            ]

            # 2. Call Supervisor LLM
            try:
                response = await call_llm(messages, self.model)
            except Exception as e:
                logger.error(f"Supervisor LLM failed: {e}")
                return {"error": str(e)}

            self.memory.add_history("assistant", response)
            
            # 3. Parse Response
            try:
                action = self._parse_json(response)
            except Exception:
                self.memory.add_observation("Error: Invalid JSON. Please output valid JSON.")
                continue

            # 4. Check Final Answer
            if "final_answer" in action:
                return action["final_answer"]

            # 5. Tool Execution
            tool_name = action.get("tool")
            args = action.get("args", {})
            
            if not tool_name:
                self.memory.add_observation("Error: No tool specified.")
                continue

            # 6. Controller Check
            limit_check = self.controller.check_limits(self.memory.tool_history, tool_name)
            if not limit_check["ok"]:
                self.memory.add_observation(f"System: {limit_check['message']} Please change strategy.")
                continue

            # 7. Execute
            logger.info(f"Supervisor calling tool: {tool_name}")
            result = None
            
            if tool_name == "python_execute":
                # Special handling for python worker
                code = args.get("code")
                result = await execute_python(code)
            else:
                # Data tools
                result = await execute_tool(tool_name, args)

            # 8. Update Memory
            self.memory.add_tool_call(tool_name, args, result)
            self.controller.increment_step()

            # 9. Max Steps Check
            if self.controller.current_step >= self.controller.MAX_STEPS:
                return {"error": "Max steps reached without solution."}

    def _parse_json(self, text: str) -> dict:
        # Extract JSON block
        match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        # Try raw
        try:
            return json.loads(text)
        except:
            # Try to find first { and last }
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                return json.loads(text[start:end+1])
            raise ValueError("No JSON found")

supervisor_agent = SupervisorAgent()
