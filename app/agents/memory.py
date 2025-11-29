import json
from typing import List, Dict, Any, Optional

class AgentMemory:
    def __init__(self):
        self.tool_history: List[Dict[str, Any]] = []
        self.last_observation: Optional[str] = None
        self.error_count: int = 0
        self.csv_metadata_cache: Dict[str, Any] = {}
        self.pdf_cache: Dict[str, Any] = {}
        self.kv_store: Dict[str, Any] = {}

    def add_observation(self, observation: str):
        """Records a text observation."""
        self.tool_history.append({
            "tool": "observation",
            "args": {},
            "result": observation
        })
        self.last_observation = observation
        
    def add_tool_call(self, tool_name: str, args: Dict, result: Any):
        """Records a tool execution."""
        entry = {
            "tool": tool_name,
            "args": args,
            "result": str(result)[:2000]  # Truncate for memory efficiency
        }
        self.tool_history.append(entry)
        self.last_observation = str(result)
        
        # Reset error count on successful execution (assuming result isn't an error string)
        # But we need to be careful, sometimes result IS an error message.
        # We'll let the controller handle error counting logic based on result content usually,
        # but here we just store it.
        
    def get_history_text(self) -> str:
        """Returns a formatted string of tool history for the LLM context."""
        if not self.tool_history:
            return "No tools executed yet."
        
        lines = []
        for i, entry in enumerate(self.tool_history):
            lines.append(f"Step {i+1}: Tool '{entry['tool']}'")
            lines.append(f"  Args: {json.dumps(entry['args'])}")
            lines.append(f"  Result: {entry['result']}")
            lines.append("-" * 20)
        return "\n".join(lines)

    def clear(self):
        self.tool_history = []
        self.last_observation = None
        self.error_count = 0
        self.csv_metadata_cache = {}
        self.pdf_cache = {}
        self.kv_store = {}
