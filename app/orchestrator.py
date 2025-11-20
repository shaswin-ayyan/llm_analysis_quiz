# app/orchestrator.py
import time
import logging
import re
from typing import Tuple, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup  # type: ignore

from app.utils.browser import render_page_with_retries
from app.agents.data_agent import DataAgent
from app.utils.submitter import submit_answer

logger = logging.getLogger("uvicorn.error")


class Orchestrator:
    def __init__(self):
        self.data_agent = DataAgent()
        self.MAX_SECONDS = 180  # 3-minute window
        self.MAX_ATTEMPTS_PER_QUESTION = 5

    # ---------------------------------------------------------
    # Helper: extract question text and CSV & submit URLs from HTML
    # ---------------------------------------------------------
    def extract_question_and_resources(
        self, html: str, page_url: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Returns (question_text, csv_url, submit_url)
        - question_text: cleaned page text
        - csv_url: detected CSV download link (supports Google Drive +
          relative paths)
        - submit_url: detected submit endpoint (href or form action
          containing 'submit')
        """

        soup = BeautifulSoup(html, "html.parser")

        # 1. Question text - page visible text concatenated
        text = soup.get_text(separator=" ").strip()
        question_text = re.sub(r"\s+", " ", text) if text else None

        # 2. CSV URL - detect anchors that look like downloadable CSVs
        csv_url = None
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            normalized = self._normalize_resource_url(href, page_url)
            text = a.get_text(strip=True) or ""
            if self._looks_like_csv_link(normalized, text):
                csv_url = normalized
                break

        # 3. Submit URL detection
        submit_url = None

        # a) Look for form action that contains 'submit'
        for form in soup.find_all("form", action=True):
            action = form["action"].strip()
            if "submit" in action.lower() or action.startswith("http"):
                submit_url = self._normalize_resource_url(action, page_url)
                break

        # b) Look for anchor with 'submit' in href
        if not submit_url:
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if "submit" in href.lower():
                    submit_url = self._normalize_resource_url(href, page_url)
                    break

        # c) Last resort: search raw html for URL-like strings
        if not submit_url:
            urls = re.findall(r"https?://[^\s'\"<>]+", html)
            for u in urls:
                if "submit" in u.lower():
                    submit_url = u
                    break

        return question_text, csv_url, submit_url

    def _normalize_resource_url(
        self, href: str, page_url: str
    ) -> Optional[str]:
        if not href:
            return None
        absolute = urljoin(page_url, href)
        return self._convert_drive_download(absolute)

    @staticmethod
    def _convert_drive_download(raw_url: str) -> str:
        """
        Convert Google Drive share links into direct download URLs when
        possible.
        """
        if not raw_url:
            return raw_url

        match = re.match(
            r"https://drive\.google\.com/file/d/([^/]+)/", raw_url
        )
        if match:
            file_id = match.group(1)
            return f"https://drive.google.com/uc?export=download&id={file_id}"
        return raw_url

    @staticmethod
    def _looks_like_csv_link(url: Optional[str], anchor_text: str) -> bool:
        if not url:
            return False

        lower_url = url.lower()
        if (
            lower_url.endswith(".csv")
            or ".csv?" in lower_url
            or ".csv#" in lower_url
        ):
            return True

        if "csv" in (anchor_text or "").lower():
            return True

        if "drive.google.com" in lower_url and "/file/" in lower_url:
            return True

        return False

    # ---------------------------------------------------------
    async def handle_task(self, question_url: str, email: str, secret: str):
        """
        Full flow:
        - Render page
        - Extract question + csv + submit url
        - Solve with DataAgent
        - Submit answer
        - If server returns next url, repeat until time expires or quiz
          completes
        """
        start_time = time.time()
        current_url = question_url

        while True:
            # timeout
            if time.time() - start_time > self.MAX_SECONDS:
                logger.error("Timeout exceeded")
                return {"error": "timeout"}

            logger.info(f"[Orchestrator] Loading: {current_url}")
            html = await render_page_with_retries(current_url)
            if not html:
                return {"error": "browser_failed"}

            (
                question_text,
                csv_url,
                submit_url,
            ) = self.extract_question_and_resources(html, current_url)

            if not question_text:
                logger.error("Could not extract question text")
                return {"error": "no_question_text"}

            if not csv_url:
                logger.error("Could not find CSV link")
                return {"error": "no_csv_url"}

            if not submit_url:
                logger.error("Could not find submit URL on page")
                return {"error": "no_submit_url"}

            logger.info(f"[Orchestrator] Question: {question_text[:120]}...")
            logger.info(f"[Orchestrator] CSV URL: {csv_url}")
            logger.info(f"[Orchestrator] Submit URL: {submit_url}")

            answer = None
            final_submit_response = None
            attempt_feedback = None
            next_url = None
            correct = False

            for attempt_num in range(1, self.MAX_ATTEMPTS_PER_QUESTION + 1):
                logger.info(
                    f"[Orchestrator] Attempt "
                    f"{attempt_num}/{self.MAX_ATTEMPTS_PER_QUESTION} "
                    f"for {current_url}"
                )
                answer = await self.data_agent.run(
                    question_text,
                    df=None,
                    csv_url=csv_url,
                    attempt_number=attempt_num,
                    prior_feedback=attempt_feedback,
                )

                if not answer or isinstance(answer, dict) and "error" in answer:
                    logger.error(f"DataAgent failed: {answer}")
                    return {"error": "agent_failed", "details": answer}

                logger.info(
                    f"[Orchestrator] Computed answer (attempt "
                    f"{attempt_num}): {answer}"
                )

                payload = {
                    "email": email,
                    "secret": secret,
                    "url": current_url,
                    "answer": answer,
                }

                logger.info(f"[Orchestrator] Submitting to {submit_url}")
                submit_response = await submit_answer(submit_url, payload)

                if not submit_response:
                    logger.error(
                        "Submit endpoint returned no data; retrying with "
                        "improved reasoning"
                    )
                    attempt_feedback = "Submit endpoint returned no data"
                    continue

                final_submit_response = submit_response
                logger.info(
                    f"[Orchestrator] Submit response: {submit_response}"
                )

                correct = submit_response.get("correct", False)
                next_url = submit_response.get("url")

                if correct:
                    logger.info("Answer accepted by server")
                    break

                attempt_feedback = (
                    submit_response.get("message")
                    or submit_response.get("detail")
                    or submit_response.get("text")
                    or "Answer incorrect"
                )
                logger.warning(
                    f"Answer incorrect (attempt {attempt_num}). "
                    f"Feedback: {attempt_feedback}"
                )

            if correct:
                if next_url:
                    logger.info(f"Next URL received: {next_url}")
                    current_url = urljoin(current_url, next_url)
                    continue
                else:
                    logger.info("Quiz finished successfully")
                    return {"status": "completed", "answer": answer}

            # Not correct after retries
            if next_url:
                logger.info(
                    "Server advanced to next URL despite incorrect "
                    f"answers: {next_url}"
                )
                current_url = next_url
                continue

            return {
                "status": "wrong",
                "answer": answer,
                "attempts": self.MAX_ATTEMPTS_PER_QUESTION,
                "server_response": final_submit_response,
            }
