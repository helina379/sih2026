# Flash Flood Prediction — frontend_flood + FastAPI

This repository contains a minimal frontend (React + Vite) and a backend (FastAPI) skeleton for a flash-flood prediction demo.

What I added
- Frontend entry: `src/main.jsx`, `src/App.jsx`, `src/index.css` (simple UI that calls the API).
- Vite dev proxy in `vite.config.js` so `/api/*` requests are forwarded to the backend during development.
- Backend updated (`backend.py`) to expose API routes under `/api/*` (example: `/api/predict`) and to serve a built frontend from `dist/` when present.

Quickstart (development)

Requirements
- Python 3.8+
- Node.js 18+ and npm

1) Clone the repo

   git clone https://github.com/helina379/sih2026.git
   cd sih2026

2) Start the backend

   # create and activate virtualenv (Unix)
   python -m venv .venv
   source .venv/bin/activate

   # (Windows)
   # python -m venv .venv
   # .venv\Scripts\activate

   pip install fastapi uvicorn
   uvicorn backend:app --reload --port 8000

   Test the API:
   curl "http://localhost:8000/api/predict?lat=12.34&lon=56.78"

3) Start the frontend (Vite dev server)

   npm install
   npm run dev

   - Open the URL shown by Vite (default http://localhost:5173).
   - The frontend uses the relative path `/api` by default. Vite's dev server proxies `/api/*` to `http://localhost:8000` (see `vite.config.js`), avoiding CORS during development.

Environment configuration
- In development the app uses `/api` (the Vite proxy). If you prefer to call the backend directly, create a `.env` file at the project root with:

  VITE_API_BASE=http://localhost:8000

  Then the frontend will use that value (via `import.meta.env.VITE_API_BASE`).

Production build and serving from backend

1) Build the frontend

   npm run build

   This produces a `dist/` directory.

2) Serve from the backend

   If `dist/` exists, the updated `backend.py` will serve the static files at `/` and keep the API at `/api/*`. Start the backend as before:

   uvicorn backend:app --port 8000

   Now visiting `http://localhost:8000` serves the built frontend and `http://localhost:8000/api/predict` is the API endpoint.

Notes and recommendations
- CORS: For development convenience the backend allows all origins; restrict `allow_origins` to your production domain when deploying.
- API prefix: Keeping API routes under `/api` avoids collisions with frontend routes.
- If you host the frontend separately (Netlify, Vercel, GitHub Pages, a CDN), set `VITE_API_BASE` to the deployed API URL.
- Current `/api/predict` returns example/dummy data. Replace with real model logic or additional endpoints as needed.

If you'd like, I can:
- Add a Dockerfile to produce a single image that serves both frontend and backend.
- Add more frontend UI (lat/lon inputs, map integration with leaflet, charts).
- Restrict CORS and add simple configuration for production envs.

