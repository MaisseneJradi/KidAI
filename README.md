# KidAI

Assistant IA générative sûr et adapté à l'âge (6–14 ans), sous contrôle parental.
Spécification : [docs/CAHIER_DES_CHARGES.md](docs/CAHIER_DES_CHARGES.md).

> Le projet tourne **sans Docker** : backend et frontend sont lancés en local.

## Prérequis

- Python 3.11 (`py -3.11 --version`)
- Node.js 20+ (`node --version`)
- PostgreSQL 17 en local, avec la base `kidai` :
  ```powershell
  & "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost -c "CREATE USER kidai WITH PASSWORD 'kidai_dev';"
  & "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost -c "CREATE DATABASE kidai OWNER kidai;"
  ```
- Ollama avec `qwen3:4b` (utile à partir de l'étape 2)

## Installation

```powershell
Copy-Item .env.example .env

cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
cd ..

cd frontend
npm install
cd ..
```

## Lancer (deux terminaux)

```powershell
# Terminal 1 — backend (http://localhost:8000)
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend (http://localhost:5173)
cd frontend
npm run dev
```

Ouvrir http://localhost:5173 : la page affiche **« backend OK »**.
`http://localhost:8000/health` renvoie `{"status":"ok","database":"ok"}`.

## Tests et qualité

```powershell
cd backend;  .\.venv\Scripts\python -m pytest
cd frontend; npm test; npm run lint; npm run format:check
```

Pre-commit (ruff, black, eslint, prettier), une fois le dépôt Git initialisé :

```powershell
backend\.venv\Scripts\pre-commit install
```

## Structure

```
backend/    FastAPI (app/, tests/)
frontend/   React + Vite + TS + Tailwind (src/, tests/)
data/raw/   datasets téléchargés (non versionnés par Git, DVC à l'étape 4)
docs/       cahier des charges
```
