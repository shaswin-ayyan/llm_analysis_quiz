import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class AntiLoopController:
    def __init__(self, max_steps: int = 15, max_repeat_tool: int = 2):
        self.max_steps = max_steps
        self.max_repeat_tool = max_repeat_tool
        self.tool_counts: Dict[str, int] = {}
        self.last_action_signature: str = ""

    def check_loop(self, tool_name: str, args: Dict) -> Dict[str, Any]:
        """
        Checks for loops and repetition.
        Returns: { "is_loop": bool, "message": str, "mode": "normal" | "reflection" | "abort" }
        """
        # Signature to detect exact repetition
        current_signature = f"{tool_name}:{json.dumps(args, sort_keys=True)}"
        
        if current_signature == self.last_action_signature:
            return {
                "is_loop": True,
                "message": "Error: You just tried this EXACT action. Do not repeat the same mistake. Try a different approach.",
                "mode": "retry"
            }
        
        self.last_action_signature = current_signature
        
        # Count tool usage for broader loop detection (e.g. alternating fails)
        self.tool_counts[tool_name] = self.tool_counts.get(tool_name, 0) + 1
        
        if self.tool_counts[tool_name] > self.max_repeat_tool:
            # Reset count to allow retry with different args or approach after reflection
            self.tool_counts[tool_name] = 0 
            return {
                "is_loop": True,
                "message": f"SYSTEM WARNING: You have used tool '{tool_name}' too many times without success. I will rethink logically and choose a different approach.",
                "mode": "reflection"
            }
            
        return {"is_loop": False, "message": "", "mode": "normal"}

    def check_step_limit(self, step_count: int) -> bool:
        return step_count >= self.max_steps
