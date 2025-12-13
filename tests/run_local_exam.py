"""
Local Exam Test Runner with Checkpointing Support

This script enables resumable testing of the LangGraph agent:
- Loads test questions from local test data
- Tracks progress in progress.json
- Resumes from last checkpoint on failure
- Generates failure reports for debugging
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.langgraph_agent import app, create_thread_config
from app.utils.submitter import submit_answer

# Configuration
PROGRESS_FILE = Path(__file__).parent / "progress.json"
FAILURE_REPORT_FILE = Path(__file__).parent / "failure_report.json"
TEST_DATA_DIR = Path(__file__).parent.parent / "tds-llm-analysis-main-tests" / "public"


class LocalTestRunner:
    """Manages local exam testing with checkpoint resume capability"""
    
    def __init__(self, email: str, secret: str):
        self.email = email
        self.secret = secret
        self.progress = self.load_progress()
        self.session_id = self.progress.get("session_id") or f"local_exam_{email}"
        
    def load_progress(self) -> Dict[str, Any]:
        """Load progress from JSON file"""
        if PROGRESS_FILE.exists():
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
        return {"completed_questions": [], "last_question": 0, "session_id": None}
    
    def save_progress(self, question_num: int, status: str):
        """Save progress to JSON file"""
        self.progress["last_question"] = question_num
        if status == "PASS":
            if question_num not in self.progress["completed_questions"]:
                self.progress["completed_questions"].append(question_num)
        self.progress["session_id"] = self.session_id
        self.progress["last_updated"] = datetime.now().isoformat()
        
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def save_failure_report(self, question_num: int, question: Dict, result: Dict, state: Dict):
        """Save detailed failure report"""
        report = {
            "failed_at": datetime.now().isoformat(),
            "question_number": question_num,
            "question": question,
            "agent_result": result,
            "last_state": {
                "url": state.get("url"),
                "final_answer": state.get("final_answer"),
                "messages": [m for m in state.get("messages", [])[-3:]]  # Last 3 messages only
            },
            "session_id": self.session_id
        }
        
        with open(FAILURE_REPORT_FILE, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"FAILURE REPORT saved to: {FAILURE_REPORT_FILE}")
        print(f"Failed at Question {question_num}")
        print(f"Agent Answer: {result.get('agent_answer')}")
        print(f"Expected: (see test data)")
        print(f"{'='*60}\n")
    
    def load_test_questions(self) -> List[Dict[str, Any]]:
        """
        Load test questions from test data directory
        
        For now, returns a mock structure. You should implement
        loading from actual test files in tds-llm-analysis-main-tests
        """
        # TODO: Implement actual test data loading
        # This is a placeholder - adapt to your test data structure
        
        questions = [
            {"num": 1, "url": "http://localhost:8000/project2", "description": "Start"},
            {"num": 2, "url": "http://localhost:8000/project2-uv", "description": "UV Command"},
            {"num": 3, "url": "http://localhost:8000/project2-git", "description": "Git Command"},
            # Add more questions based on your test data
        ]
        
        return questions
    
    async def run_question(self, question: Dict[str, Any], question_num: int) -> Dict[str, Any]:
        """
        Execute a single question using LangGraph with checkpointing
        
        Args:
            question: Question data dict
            question_num: Question number
        
        Returns:
            Result dict with 'correct' status and details
        """
        print(f"\n--- Running Question {question_num}: {question['description']} ---")
        
        # Create initial state
        initial_state = {
            "email": self.email,
            "email_offset": len(self.email),
            "url": question["url"],
            "workspace_path": os.path.join(os.getcwd(), "workspace"),
            "messages": [],
            "retry_count": 0,
            "final_answer": None,
            "next_node": None
        }
        
        # Create thread config for checkpointing
        config = create_thread_config(self.email, self.session_id)
        
        try:
            # Invoke graph with checkpointing
            result_state = await app.ainvoke(initial_state, config=config)
            answer = result_state.get("final_answer")
            
            print(f"Agent Answer: {answer}")
            
            # For local testing, you might mock submission or use actual API
            # Here we'll just return a mock result
            # TODO: Implement actual answer validation or submission
            
            return {
                "correct": True,  # Mock - implement actual validation
                "agent_answer": answer,
                "state": result_state
            }
            
        except Exception as e:
            print(f"Error executing question: {e}")
            return {
                "correct": False,
                "error": str(e),
                "agent_answer": None,
                "state": initial_state
            }
    
    async def run_exam(self):
        """
        Run the full exam with resume capability
        """
        print(f"\n{'='*60}")
        print(f"LOCAL EXAM RUNNER - Resumable Execution")
        print(f"Email: {self.email}")
        print(f"Session ID: {self.session_id}")
        print(f"Progress File: {PROGRESS_FILE}")
        print(f"{'='*60}\n")
        
        # Load questions
        questions = self.load_test_questions()
        
        # Resume from last checkpoint
        completed = self.progress.get("completed_questions", [])
        if completed:
            print(f"Resuming from checkpoint. Completed questions: {completed}")
        
        for question in questions:
            question_num = question["num"]
            
            # Skip completed questions
            if question_num in completed:
                print(f"Skipping Q{question_num} (already completed)")
                continue
            
            # Run question
            result = await self.run_question(question, question_num)
            
            if result["correct"]:
                self.save_progress(question_num, "PASS")
                print(f"✓ Q{question_num} PASSED")
            else:
                self.save_progress(question_num, "FAIL")
                self.save_failure_report(question_num, question, result, result.get("state", {}))
                print(f"✗ Q{question_num} FAILED - Stopping execution")
                print(f"\nTo resume: Fix the issue and run this script again")
                print(f"The test will resume from Q{question_num}")
                break
        else:
            print(f"\n{'='*60}")
            print(f"ALL QUESTIONS COMPLETED!")
            print(f"Total: {len(questions)}")
            print(f"{'='*60}\n")


async def main():
    """Main entry point"""
    # Configuration - update with your credentials
    email = "23f1000266@ds.study.iitm.ac.in"
    secret = os.getenv("QUIZ_SECRET", "jarvis_execute")
    
    runner = LocalTestRunner(email, secret)
    await runner.run_exam()


if __name__ == "__main__":
    asyncio.run(main())
