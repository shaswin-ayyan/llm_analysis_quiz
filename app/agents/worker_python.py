from app.sandbox.python_execute import PythonSandbox

sandbox = PythonSandbox()

async def execute_python(code: str) -> dict:
    """
    Executes Python code in the sandbox.
    """
    return sandbox.execute(code)
