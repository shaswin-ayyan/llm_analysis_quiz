# Project 2 — LLM Analysis Quiz Starter

This repo is a starter scaffold for the LLM Analysis Quiz project. It exposes a FastAPI POST endpoint that verifies a secret and solves quiz tasks using a small orchestrator + workers. It calls LLMs through AI Pipe by default.

See .env.example for required environment variables.

Run locally:

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000