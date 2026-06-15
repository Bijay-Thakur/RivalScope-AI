# RivalScope AI

Monorepo for **RivalScope AI** — source-grounded competitive intelligence for GTM teams.

## Structure

```
rivalscope-ai/
├── frontend/     Next.js dashboard (TypeScript, Tailwind)
└── backend/      FastAPI research agent API (Python, mock demo)
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs

## Status

- **Frontend:** Portfolio demo with simulated agent progress and mock report
- **Backend:** Mock workflow API — ready to wire to the frontend

No API keys required for the current demo.
