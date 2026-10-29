# Nivaran — Deployment Guide (Frontend on Vercel & Backend on Render)

## Architecture Overview
- **Frontend**: Vite + React 19 + TypeScript (Single Page Application) -> Deployed to **Vercel**
- **Backend**: FastAPI + PostgreSQL / SQLAlchemy + Uvicorn -> Deployed to **Render**

---

## 1. Backend Deployment on Render

1. Push the repository to GitHub.
2. Sign in to [Render](https://dashboard.render.com/), select **New +** > **Blueprint**, and connect the repository.
3. Render will read the root [`render.yaml`](./render.yaml). Confirm the web service and PostgreSQL database, then click **Apply**.
4. The backend service uses `nivaran/backend` as its root, seeds synthetic demo data on startup, and gets a generated `SECRET_KEY`.
5. Copy the backend URL (for example, `https://nivaran-backend.onrender.com`).

---

## 2. Frontend Deployment on Vercel

1. Sign in to [Vercel](https://vercel.com/), select **Add New...** > **Project**, and import the same GitHub repository.
2. Set **Root Directory** to `nivaran/frontend`, **Build Command** to `npm run build`, and **Output Directory** to `dist`.
3. Add `VITE_API_URL` with the Render backend URL (no trailing slash), then deploy.
4. If the assigned Vercel domain differs from `https://nivaran-01.vercel.app`, update `ALLOWED_ORIGINS` in Render to include the new domain.

---

## 3. Post-Deployment Verification Checklist
1. Visit the Vercel URL and confirm the frontend API requests reach Render.
2. Check the backend health endpoint at `/api/health`.
3. This is a demonstration deployment with synthetic data and seeded demo accounts; do not use it for real complaint data.
