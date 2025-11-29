class Controller:
    def __init__(self, max_steps: int = 15, max_repeat_tool: int = 2):
        self.MAX_STEPS = max_steps
        self.MAX_REPEAT_TOOL = max_repeat_tool
        self.current_step = 0
        self.reflection_mode = False

    def check_limits(self, tool_history: list, next_tool: str) -> dict:
        """
        Checks if limits are exceeded.
        Returns {"ok": bool, "message": str}
        """
        if self.current_step >= self.MAX_STEPS:
            return {"ok": False, "message": "MAX_STEPS reached."}

        # Check tool repetition
        repeats = 0
        for entry in reversed(tool_history):
            if entry["tool"] == next_tool:
                repeats += 1
            else:
                break
        
        if repeats >= self.MAX_REPEAT_TOOL:
            return {"ok": False, "message": f"Tool '{next_tool}' repeated too many times ({repeats})."}

        return {"ok": True}

    def increment_step(self):
        self.current_step += 1

    def set_reflection_mode(self, enabled: bool):
        self.reflection_mode = enabled

    def check_identical_result(self, history: list, new_result: str) -> bool:
        # Simple check if the exact same result appeared recently
        # Implementation depends on how results are stored
        return False # Placeholder
