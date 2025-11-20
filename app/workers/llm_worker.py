from app.llm_client import chat_completion


class LLMWorker:
    async def plan(self, prompt: str):
        messages = [
            {
                "role": "system",
                "content": "You are a planning agent that outputs JSON.",
            },
            {"role": "user", "content": prompt},
        ]
        response = await chat_completion(messages)
        return response
