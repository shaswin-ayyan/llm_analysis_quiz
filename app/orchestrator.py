import time
import logging
import re
from typing import Tuple, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from app.utils.browser import render_page_with_retries
from app.agents.data_agent import DataAgent
from app.utils.submitter import submit_answer

logger = logging.getLogger("uvicorn.error")

class Orchestrator:
    def __init__(self):
        self.data_agent = DataAgent()
        self.MAX_SECONDS = 180  # 3-minute window
        self.MAX_ATTEMPTS_PER_QUESTION = 5

    def extract_question_and_resources(
        self, html: str, page_url: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Returns (question_text, resource_url, submit_url)
        resource_url can be CSV, PDF, or JSON.
        """
        soup = BeautifulSoup(html, "html.parser")

        # 1. Question text
        text = soup.get_text(separator=" ").strip()
        question_text = re.sub(r"\s+", " ", text) if text else None

        # 2. Resource URL (CSV, PDF, JSON)
        resource_url = None
        
        # Priority 1: CSV
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            normalized = self._normalize_resource_url(href, page_url)
            text = a.get_text(strip=True) or ""
            if self._looks_like_data_link(normalized, text, "csv"):
                resource_url = normalized
                break
        
        # Priority 2: PDF (if no CSV found)
        if not resource_url:
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                normalized = self._normalize_resource_url(href, page_url)
                if self._looks_like_data_link(normalized, "", "pdf"):
                    resource_url = normalized
                    break

        # 3. Submit URL detection
        submit_url = None
        # a) Form action
        for form in soup.find_all("form", action=True):
            action = form["action"].strip()
            if "submit" in action.lower() or action.startswith("http"):
                submit_url = self._normalize_resource_url(action, page_url)
                break

        # b) Anchor with 'submit'
        if not submit_url:
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if "submit" in href.lower():
                    submit_url = self._normalize_resource_url(href, page_url)
                    break
        
        # c) Regex search
        if not submit_url:
            urls = re.findall(r"https?://[^\s'\"<>]+", html)
            for u in urls:
                if "submit" in u.lower():
                    submit_url = u
                    break

        return question_text, resource_url, submit_url

    def _normalize_resource_url(self, href: str, page_url: str) -> Optional[str]:
        if not href:
            return None
        absolute = urljoin(page_url, href)
        return self._convert_drive_download(absolute)

    @staticmethod
    def _convert_drive_download(raw_url: str) -> str:
        if not raw_url:
            return raw_url
        match = re.match(r"https://drive\.google\.com/file/d/([^/]+)/", raw_url)
        if match:
            file_id = match.group(1)
            return f"https://drive.google.com/uc?export=download&id={file_id}"
        return raw_url

    @staticmethod
    def _looks_like_data_link(
        url: Optional[str], anchor_text: str, file_type: str
    ) -> bool:
        if not url:
            return False
        lower = url.lower()
        if f".{file_type}" in lower:
            return True
        if file_type in (anchor_text or "").lower():
            return True
        return False

    async def handle_task(self, question_url: str, email: str, secret: str):
        start_time = time.time()
        current_url = question_url

        while True:
            if time.time() - start_time > self.MAX_SECONDS:
                logger.error("Timeout exceeded")
                return {"error": "timeout"}

            logger.info(f"[Orchestrator] Loading: {current_url}")
            html = await render_page_with_retries(current_url)
            if not html:
                return {"error": "browser_failed"}

            (q_text, res_url, sub_url) = self.extract_question_and_resources(
                html, current_url
            )

            if not q_text:
                return {"error": "no_question_text"}
            if not sub_url:
                return {"error": "no_submit_url"}
            
            # Allow proceeding without CSV/PDF, but log warning
            if not res_url:
                logger.warning("No data file (CSV/PDF) found. Agent will rely on text.")

            logger.info(f"[Orchestrator] Question: {q_text[:50]}...")
            logger.info(f"[Orchestrator] Resource: {res_url}")

            answer = None
            attempt_feedback = None
            
            # Retry loop for logic errors
            for attempt_num in range(1, self.MAX_ATTEMPTS_PER_QUESTION + 1):
                # Pass res_url as 'csv_url' arg to keep Agent interface compatible
                # The updated Agent/Tools will handle it if it's actually a PDF
                answer = await self.data_agent.run(
                    q_text,
                    df=None,
                    csv_url=res_url, 
                    attempt_number=attempt_num,
                    prior_feedback=attempt_feedback,
                )

                if not answer or (isinstance(answer, dict) and "error" in answer):
                    logger.error(f"DataAgent failed: {answer}")
                    return {"error": "agent_failed", "details": answer}

                payload = {
                    "email": email,
                    "secret": secret,
                    "url": current_url,
                    "answer": answer,
                }

                logger.info(f"[Orchestrator] Submitting answer: {answer}")
                submit_response = await submit_answer(sub_url, payload)

                if not submit_response:
                    attempt_feedback = "Submit endpoint returned no data"
                    continue

                correct = submit_response.get("correct", False)
                next_url = submit_response.get("url")

                if correct:
                    if next_url:
                        logger.info(f"Correct! Next URL: {next_url}")
                        current_url = urljoin(current_url, next_url)
                        break # Break inner loop, continue outer 'while True'
                    else:
                        logger.info("Quiz completed successfully!")
                        return {"status": "completed", "answer": answer}
                
                # If wrong
                attempt_feedback = submit_response.get("message", "Incorrect answer")
                logger.warning(f"Wrong answer. Feedback: {attempt_feedback}")
                
                # Check if server moved us forward anyway (rare but possible)
                if next_url:
                     logger.info("Server advanced despite wrong answer.")
                     current_url = urljoin(current_url, next_url)
                     break

            else:
                 # Inner loop finished without 'break' -> max attempts reached
                 return {"status": "failed", "reason": "max_attempts_reached"}