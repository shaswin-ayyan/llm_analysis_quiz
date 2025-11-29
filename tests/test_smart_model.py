import unittest
from app.agents.data_agent import DataAgent
from app.llm_client import ALL_PROVIDERS

class TestSmartModel(unittest.TestCase):
    def test_model_attempts_order(self):
        # Mock providers
        original_providers = list(ALL_PROVIDERS)
        ALL_PROVIDERS.clear()
        ALL_PROVIDERS.append({
            "name": "Gemini",
            "models": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"]
        })
        
        try:
            agent = DataAgent()
            
            # Attempt 1: Default order (flash -> pro -> flash)
            attempts_1 = agent._model_attempts(attempt_number=1)
            # Expected: [(0,0), (0,1), (0,2)]
            self.assertEqual(attempts_1[0], (0, 0)) # gemini-2.0-flash
            self.assertEqual(attempts_1[1], (0, 1)) # gemini-1.5-pro
            
            # Attempt 2: Stronger first (pro -> flash -> flash)
            attempts_2 = agent._model_attempts(attempt_number=2)
            # Expected: [(0,1), (0,0), (0,2)]
            self.assertEqual(attempts_2[0], (0, 1)) # gemini-1.5-pro (Stronger)
            self.assertEqual(attempts_2[1], (0, 0)) # gemini-2.0-flash
            
            print("SUCCESS: Smart model switching logic verified.")
            
        finally:
            # Restore
            ALL_PROVIDERS.clear()
            ALL_PROVIDERS.extend(original_providers)

if __name__ == "__main__":
    unittest.main()
