---
title: Enterprise Knowledge Copilot API
emoji: 🧠
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Enterprise Knowledge Copilot — Backend

FastAPI + LangGraph API for the Enterprise Knowledge Copilot. See the project
root for the full spec and the `frontend/` folder for the Next.js client.

This Space expects the following secrets to be set under Settings → Repository secrets:

- `DATABASE_URL`
- `JWT_SECRET`
- `CREDENTIAL_ENCRYPTION_KEY`
- `FRONTEND_ORIGIN`
- `COOKIE_SECURE=true`
- `COOKIE_SAMESITE=none`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`
- `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET`, `SLACK_REDIRECT_URI`
- `GEMINI_API_KEY`, `GROQ_API_KEY`
