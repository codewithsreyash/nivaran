# Nivaran — Deployment Guide (Frontend on Vercel & Backend on Render)

## Architecture Overview
- **Frontend**: Vite + React 19 + TypeScript (Single Page Application) -> [Vercel](https://nivaran-swart.vercel.app)
- **Backend**: FastAPI + PostgreSQL / SQLAlchemy + Uvicorn -> [Render](https://nivaran-backend-pug7.onrender.com)

---

## 1. Backend Deployment on Render

1. Push the repository to GitHub.
2. Sign in to [Render](https://dashboard.render.com/), select **New +** > **Blueprint**, and connect the repository.
3. Render will read the root [`render.yaml`](./render.yaml). Confirm the web service and PostgreSQL database, then click **Apply**.
4. The backend service uses `nivaran/backend` as its root, seeds synthetic demo data on startup, and gets a generated `SECRET_KEY`.
5. The deployed backend URL is `https://nivaran-backend-pug7.onrender.com`.

---

## 2. Frontend Deployment on Vercel

1. Sign in to [Vercel](https://vercel.com/), select **Add New...** > **Project**, and import the same GitHub repository.
2. Set **Root Directory** to `nivaran/frontend`, **Build Command** to `npm run build`, and **Output Directory** to `dist`.
3. Set `VITE_API_URL` to `https://nivaran-backend-pug7.onrender.com` (no trailing slash), then deploy.
4. The Render Blueprint allows `https://nivaran-swart.vercel.app`. If the Vercel domain changes, update `ALLOWED_ORIGINS` in the root `render.yaml` and sync the Blueprint.

---

## 3. Post-Deployment Verification Checklist
1. Visit [https://nivaran-swart.vercel.app](https://nivaran-swart.vercel.app) and confirm the dashboard loads.
2. Check the backend health endpoint at [https://nivaran-backend-pug7.onrender.com/api/health](https://nivaran-backend-pug7.onrender.com/api/health).
3. This is a demonstration deployment with synthetic data and seeded demo accounts; do not use it for real complaint data.
4. The free Render web service may spin down while idle, delaying the first request after inactivity.
