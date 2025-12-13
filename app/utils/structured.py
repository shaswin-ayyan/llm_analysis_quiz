import instructor
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from app.router import query_llm
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Define common Pydantic models for agent outputs

class CodeSnippet(BaseModel):
    language: str = Field(..., description="Programming language (python, bash, javascript)")
    code: str = Field(..., description="The code to execute")
    description: str = Field(..., description="Brief description of what the code does")

class AnalysisPlan(BaseModel):
    steps: List[str] = Field(..., description="List of steps to perform the analysis")
    required_files: List[str] = Field(default_factory=list, description="Files needed for the analysis")
    tool_calls: List[CodeSnippet] = Field(default_factory=list, description="Initial code to run")

class FinalAnswer(BaseModel):
    answer: str | int | float | dict | list = Field(..., description="The final answer to the user's question")
    reasoning: str = Field(..., description="Explanation of how the answer was derived")
    is_correct: bool = Field(default=True, description="Self-assessment of correctness")

async def query_structured(messages: list, response_model: type[BaseModel], model: str = None):
    """
    Uses Instructor to get structured output from the LLM.
    Since we are using a custom router (LiteLLM) which might not be directly compatible 
    with Instructor's patching of the OpenAI client in all cases (especially with AIPIPE proxy),
    we might need to use Instructor's 'from_litellm' or similar if available, 
    OR manually parse if the model is very dumb.
    
    However, Instructor works best by patching the client.
    For now, we will use a simple approach: 
    Ask LLM to output JSON matching the schema, then parse it.
    Instructor has a 'patch' mode but it requires a client instance.
    """
    
    # Ideally we would do:
    # client = instructor.from_litellm(completion)
    # resp = client.chat.completions.create(..., response_model=response_model)
    
    # But let's try to use the router's raw output and parse it with Pydantic first 
    # to keep our router logic central.
    # OR we can use instructor to wrap our router? No, instructor wraps the client.
    
    # Let's try to use instructor with litellm directly if possible.
    # Instructor supports 'mode=instructor.Mode.MD_JSON' which is good for generic models.
    
    try:
        # We will construct a system prompt that enforces the schema
        schema_json = response_model.model_json_schema()
        system_msg = {
            "role": "system", 
            "content": f"You must respond with a valid JSON object matching this schema:\n{schema_json}"
        }
        
        # Prepend system message
        full_messages = [system_msg] + messages
        
        # Get raw response from router
        content = await query_llm(full_messages, model=model, temperature=0.0)
        
        # Parse with Pydantic
        # This is a "poor man's instructor" but robust enough for now given our custom router
        import json
        
        # Try to find JSON block if wrapped in markdown
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        data = json.loads(content)
        return response_model.model_validate(data)
        
    except Exception as e:
        logger.error(f"Structured query failed: {e}")
        # Retry or re-raise?
        raise e
