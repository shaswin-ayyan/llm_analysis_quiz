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

*   **FastAPI Server (`app/main.py`):** This is the entry point of the application. It exposes a single endpoint, `/solve`, that receives the quiz URL and other details. It's the bouncer of our little club, checking for secrets and making sure everyone behaves.
*   **Orchestrator (`app/orchestrator.py`):** This is the brains of the operation. It takes the quiz URL, renders the page using Playwright, and extracts the question, CSV URL, and submit URL. It then passes the question to the `DataAgent` to get the answer and submits it to the quiz server. It's the project manager, making sure everyone is doing their job and that the project is on track.
*   **Data Agent (`app/agents/data_agent.py`):** This is where the magic happens. The `DataAgent` uses an LLM to analyze the question and the provided CSV data to come up with an answer. It's our resident genius, the one who actually knows what they're doing.

## Setup

To run the application locally, you'll need to have Python 3.10+ and Docker installed.

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/your-repo.git
    cd your-repo
    ```

2.  **Create a `.env` file:**

    ```bash
    cp .env.example .env
    ```

3.  **Update the `.env` file with your secret:**

    ```bash
    QUIZ_SECRET=your-secret
    ```

4.  **Build and run the Docker container:**

    ```bash
    docker-compose up -d
    ```

5.  **Test the application:**

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
```

Then, you can run the tests using `pytest`:

```bash
pytest
```
