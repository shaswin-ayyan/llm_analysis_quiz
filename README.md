# Project 2 — LLM Analysis Quiz-inator 3000

Welcome to the future of quiz-solving! This project is a FastAPI-based web application that uses the power of LLMs to solve data science quizzes. It's like having a tiny data scientist living in your computer, but without the need for coffee and snacks.

## System Design

The application is designed with a simple and modular architecture, making it easy to understand and extend. Here's a high-level overview of how it works:

```
                  +-----------------+
                  |                 |
                  |  FastAPI Server |
                  |                 |
                  +-------+---------+
                          |
                          | (POST /solve)
                          |
                  +-------v---------+
                  |                 |
                  |  Orchestrator   |
                  |                 |
                  +-------+---------+
                          |
                          | (Run, young padawan!)
                          |
                  +-------v---------+
                  |                 |
                  |    Data Agent   |
                  |                 |
                  +-----------------+
```

### Components

*   **FastAPI Server (`app/main.py`):** This is the entry point of the application. It exposes a single endpoint, `/solve`, that receives the quiz URL and other details. It's the bouncer of our little club, checking for secrets and making sure everyone behaves. It also has a `/health` endpoint to check the service's status.
*   **Orchestrator (`app/orchestrator.py`):** This is the brains of the operation. It takes the quiz URL, renders the page using Playwright, and extracts the question, CSV URL, and submit URL. It then passes the question to the `DataAgent` to get the answer and submits it to the quiz server. It's the project manager, making sure everyone is doing their job and that the project is on track.
*   **Data Agent (`app/agents/data_agent.py`):** This is where the magic happens. The `DataAgent` uses an LLM to analyze the question and the provided CSV data to come up with an answer. It's our resident genius, the one who actually knows what they're doing.

### Pros and Cons

#### Pros

*   **Modular Architecture:** The separation of concerns between the FastAPI server, the orchestrator, and the data agent makes the code easy to understand, test, and maintain.
*   **Scalability:** The application is built with modern, async-first technologies like FastAPI and `aiohttp`, which makes it highly scalable and able to handle a large number of concurrent requests.
*   **Flexibility:** The use of an LLM for data analysis allows the application to handle a wide variety of questions and data formats without requiring any changes to the code.

#### Cons

*   **Dependency on External Services:** The application relies on an external LLM service to function. If this service is unavailable, the application will not be able to solve quizzes.
*   **Cost:** The use of a powerful LLM can be expensive, especially when processing a large number of quizzes.
*   **Accuracy:** The accuracy of the answers provided by the LLM is not guaranteed. While LLMs are powerful, they can still make mistakes, and their performance can vary depending on the complexity of the question and the quality of the data.

## File-by-File Breakdown

*   **`app/`**: This directory contains the main application code.
    *   **`main.py`**: The entry point of the FastAPI application. It defines the `/solve` and `/health` endpoints.
    *   **`orchestrator.py`**: The core logic of the application. It orchestrates the process of solving a quiz, from fetching the question to submitting the answer.
    *   **`agents/`**: This directory contains the data agent code.
        *   **`data_agent.py`**: The data agent is responsible for analyzing the question and the provided data to come up with an answer.
        *   **`tools.py`**: This file contains a set of tools that the data agent can use to perform various data analysis tasks, such as reading CSV files, calculating correlations, and generating summary statistics.
    *   **`utils/`**: This directory contains utility functions that are used throughout the application.
        *   **`browser.py`**: A simple wrapper around Playwright that allows the application to render web pages and extract their HTML content.
        *   **`parse_table.py`**: A utility for parsing HTML tables and converting them into a structured format that can be used by the data agent.
        *   **`submitter.py`**: A simple utility for submitting the answer to the quiz server.
*   **`tests/`**: This directory contains the tests for the application.
    *   **`test_e2e.py`**: End-to-end tests that simulate the entire quiz-solving process.
    *   **`test_health.py`**: A simple test to verify that the `/health` endpoint is working correctly.
    *   **`mock_server.py`**: A simple mock server that is used to simulate the quiz server during testing.
*   **`.github/`**: This directory contains the GitHub Actions workflow for the project.
*   **`Dockerfile`**: A file that contains the instructions for building the Docker image for the application.
*   **`docker-compose.yml`**: A file that contains the configuration for running the application and its dependencies using Docker Compose.
*   **`requirements.txt`**: A file that lists the Python dependencies for the project.
*   **`requirements-dev.txt`**: A file that lists the Python dependencies for development and testing.

## Setup

To run the application locally, you'll need to have Python 3.11+ and Docker installed.

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/your-repo.git
    cd your-repo
    ```

2.  **Create a `.env` file:**

    There is no `.env.example` file anymore. You should create a `.env` file and add the following line:

    ```bash
    QUIZ_SECRET=your-secret
    ```

3.  **Build and run the Docker container:**

    ```bash
    docker-compose up -d
    ```

4.  **Test the application:**

    ```bash
    curl -X POST http://localhost:8000/solve -H "Content-Type: application/json" -d '{
      "email": "test@example.com",
      "secret": "your-secret",
      "url": "https://tds-llm-analysis.s-anand.net/demo"
    }'
    ```

## Running the Tests

To run the tests, you'll need to have the dependencies installed. You can do this by running:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Then, you can run the tests using `pytest`:

```bash
pytest
```
