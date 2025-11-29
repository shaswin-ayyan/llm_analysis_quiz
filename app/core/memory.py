class AgentMemory:
    def __init__(self):
        self.history = []
        self.observations = []
        self.tool_history = []
        self.last_tool = None
        self.last_observation = None
        self.csv_metadata_cache = {}

    def add_history(self, role: str, content: str):
        self.history.append({"role": role, "content": content})

    def add_observation(self, content: str):
        self.observations.append(content)
        self.last_observation = content

    def add_tool_call(self, tool_name: str, args: dict, result: dict):
        self.tool_history.append({
            "tool": tool_name,
            "args": args,
            "result": result
        })
        self.last_tool = tool_name
        self.last_observation = str(result)

    def get_history_text(self) -> str:
        return "\n".join([f"{h['role'].upper()}: {h['content']}" for h in self.history])

    def clear(self):
        self.history = []
        self.observations = []
        self.tool_history = []
        self.last_tool = None
        self.last_observation = None
        self.csv_metadata_cache = {}
