import unittest
import pandas as pd
import asyncio
from app.agents.tools import python_execute, sandbox

# We need to inject the dataframe into the sandbox globals manually for the test
# because python_execute doesn't take 'df' argument in the new implementation (it uses sandbox globals)

class TestPythonTool(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({
            "A": [1, 2, 3, 4, 5],
            "B": [10, 20, 30, 40, 50]
        })
        # Inject into sandbox
        sandbox.globals["df"] = self.df

    def run_async(self, coro):
        return asyncio.run(coro)

    def test_simple_math(self):
        code = "result = 1 + 1"
        res = self.run_async(python_execute({"code": code}))
        self.assertEqual(res["result"], "2")

    def test_dataframe_operation(self):
        code = "result = df['A'].sum()"
        res = self.run_async(python_execute({"code": code}))
        self.assertEqual(res["result"], "15")

    def test_filtering(self):
        # Result is a dataframe, so string representation might be tricky.
        # Let's just check if it runs without error.
        code = "result = len(df[df['A'] > 3])"
        res = self.run_async(python_execute({"code": code}))
        self.assertEqual(res["result"], "2")

    def test_error_handling(self):
        code = "result = 1 / 0"
        res = self.run_async(python_execute({"code": code}))
        self.assertTrue("division by zero" in res["error"])

if __name__ == "__main__":
    unittest.main()
