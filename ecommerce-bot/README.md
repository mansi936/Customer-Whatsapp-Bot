# E-Commerce WhatsApp Bot

Project skeleton for the E-Commerce WhatsApp Bot.

## Structure
See folder layout — webhook handler (FastAPI), client (MCP client/pool), server (tools), and services (EnableX, Redis, MongoDB, LLM, Try-On, Logging).

## How to run (dev)
1. Create a Python virtualenv and install requirements (FastAPI, uvicorn, etc).
2. Start webhook: `python webhook/enablex_webhook.py`
3. Implement services and wire them up.

