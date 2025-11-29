# LLM Analysis Quiz Solver

## Overview

The **LLM Analysis Quiz Solver** is an advanced, automated system designed to solve complex data analysis quizzes using Large Language Models (LLMs). It leverages a multi-agent architecture to extract questions, analyze data (CSV, JSON, etc.), write and execute Python code, and submit answers via a REST API.

The system is built for robustness and efficiency, featuring strict time management (180s per question), automatic retries with feedback loops, and self-cleaning workspace management.

## System Design

The architecture follows a hierarchical multi-agent pattern:

### 1. Orchestrator (`app/orchestrator.py`)
The central nervous system of the application.
-   **Responsibility**: Manages the high-level quiz loop.
-   **Time Management**: Enforces a strict **180-second (3-minute)** timeout per question.
-   **Flow Control**: Handles extraction, reasoning, submission, and navigation to the next question.
-   **Error Handling**: Manages retries (up to 3 attempts) and decides when to skip a question if the time limit is breached.
-   **Cleanup**: Automatically deletes the `workspace` directory and all temporary files upon completion to save storage.

### 2. Extractor Agent (`app/agents/extractor_agent.py`)
-   **Responsibility**: Fetches the quiz URL, parses the HTML, and extracts the question text, data file links, and submission endpoints.
-   **Output**: A structured context dictionary containing all necessary metadata for the reasoning agents.

### 3. Tier 1 Orchestrator (`app/agents/tier1_orchestrator.py`)
-   **Responsibility**: The high-level reasoning agent. It plans the solution steps but delegates the actual coding and execution to the Tier 2 Worker.
-   **Role**: Acts as the "Project Manager" for the solution.

### 4. Tier 2 Worker (`app/agents/workers/tier2_worker.py`)
-   **Responsibility**: The specialized "Data Scientist" agent.
-   **Capabilities**: Writes Python code, executes it using the `run_programming_task` tool, analyzes the output, and formulates the final answer.
-   **Safety**: Runs code in a controlled environment.

## Workflow

1.  **Initialization**: The system starts with a seed URL, email, and API secret.
2.  **Extraction**: The `Extractor Agent` scrapes the page to find the question and data links.
3.  **Reasoning Loop**:
    -   The `Orchestrator` starts a timer (180s limit).
    -   `Tier 1` analyzes the request and delegates to `Tier 2`.
    -   `Tier 2` writes code to download data, process it (using pandas, etc.), and compute the answer.
    -   The code is executed, and results are returned to the agents.
4.  **Submission**:
    -   The computed answer is submitted to the quiz API.
    -   **Success**: If correct, the system extracts the `next_url` and proceeds immediately.
    -   **Failure**: If incorrect, the system receives feedback and retries (up to 3 times).
5.  **Timeout Handling**:
    -   If the process exceeds **180 seconds**, the system attempts to gracefully fail.
    -   If a `next_url` was discovered in a previous failed attempt, the system skips the current question and moves forward to keep the exam going.
6.  **Cleanup**:
    -   Once the quiz is finished (or a terminal error occurs), the `Orchestrator` automatically deletes the `workspace` folder, removing all downloaded datasets and temporary scripts.

## Usage

### Prerequisites
-   Python 3.10+
-   Gemini API Key (or compatible LLM key)

### Installation

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Set up environment variables (create a `.env` file):
    ```env
    GEMINI_API_KEY=your_api_key_here
    ```

### Running the Solver

Execute the main application (assuming `main.py` or similar entry point):

```bash
python -m app.main
```

*Note: Ensure you have the correct starting URL and credentials configured in your launch configuration or passed as arguments.*

## Key Features

-   **Strict Time Limits**: Ensures no single question blocks the entire exam. Hard limit of 3 minutes per question.
-   **Auto-Cleanup**: Keeps your disk clean by removing gigabytes of potential data files after the run.
-   **Resilient Logic**: Can recover from incorrect answers and navigate through the quiz even if some questions are missed (provided a next link is available).
-   **Multi-Agent Reasoning**: Separates planning from execution for higher accuracy.
