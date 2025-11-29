import unittest
import pandas as pd
import asyncio
from app.agents.tools import run_python_code_tool

class TestPythonTool(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({
            "A": [1, 2, 3, 4, 5],
            "B": [10, 20, 30, 40, 50]
        })

    def run_async(self, coro):
        return asyncio.run(coro)

    def test_simple_math(self):
        code = "result = 1 + 1"
        res = self.run_async(run_python_code_tool({"code": code}, self.df))
        self.assertEqual(res, 2)

    def test_dataframe_operation(self):
        code = "result = df['A'].sum()"
        res = self.run_async(run_python_code_tool({"code": code}, self.df))
        self.assertEqual(res, 15)

    def test_filtering(self):
        code = "result = df[df['A'] > 3]"
        res = self.run_async(run_python_code_tool({"code": code}, self.df))
        self.assertTrue(isinstance(res, pd.DataFrame))
        self.assertEqual(len(res), 2)

    def test_error_handling(self):
        code = "result = 1 / 0"
        res = self.run_async(run_python_code_tool({"code": code}, self.df))
        self.assertTrue("division by zero" in str(res))

if __name__ == "__main__":
    unittest.main()
