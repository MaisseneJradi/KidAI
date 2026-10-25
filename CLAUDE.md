# KidAI — instructions pour Claude Code

## Projet
Assistant IA sûr et adapté à l'âge (6-14 ans), sous contrôle parental.
Spécification complète : docs/CAHIER_DES_CHARGES.md — la lire avant toute tâche.

## Règles de travail
- Travailler UNE étape à la fois (section 16). Ne pas anticiper les étapes suivantes.
- Respecter le contrat d'API de la section 14 et le schéma de la section 15.
- Toujours écrire des tests (pytest / Vitest / Playwright) pour le code ajouté.
- Ne jamais mettre de clé ou d'appel modèle dans le frontend.
- Ne jamais inventer de données d'enfants réels ; utiliser data/ et les mocks.
- Mascotte et images : uniquement des créations originales, jamais de personnages existants.
- Expliquer brièvement ce qui a été fait et comment le vérifier à la fin de chaque tâche.

## Écarts par rapport au cahier des charges (décisions de l'équipe)
- **Pas de Docker** : pas de Dockerfile ni de docker-compose. Tout tourne en local
  (venv Python 3.11 pour le backend, npm pour le frontend). Pour les services du cahier,
  préférer des variantes locales/embarquées (Qdrant en mode local, MLflow avec stockage fichier,
  tâches de fond FastAPI à la place de RabbitMQ tant que c'est suffisant).
- **La mascotte s'appelle Chaty** (شاتي en arabe), et non Nouri comme dans le cahier : petit
  hibou-robot original. Utiliser « Chaty » partout (code, textes, prompts système de l'Annexe C).
- **PostgreSQL 17** installé en local (service Windows `postgresql-x64-17`, port 5432),
  base `kidai`, utilisateur `kidai`. URL dans `.env` (`DATABASE_URL`).

## Stack
Frontend : React 18 + Vite + TypeScript + Tailwind + Framer Motion + react-i18next (FR/AR RTL) + PWA
Backend : Python 3.11, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 17
IA : Ollama (qwen3), Qwen3Guard (mode strict), ShieldGemma 2, FLUX.1-schnell/SD-Turbo, Qdrant + bge-m3
RL : Gymnasium + Stable-Baselines3 ; MLOps : DVC, MLflow, GitLab CI, Prometheus, Grafana, Loki

## Commandes (Windows / PowerShell)
- Backend : cd backend ; .\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
- Frontend : cd frontend ; npm run dev   (http://localhost:5173)
- Tests backend : cd backend ; .\.venv\Scripts\python -m pytest
- Tests frontend : cd frontend ; npm test ; npm run test:e2e
- Frontend en mode démo (MSW, sans backend) par défaut ; VITE_USE_MOCKS=false pour l'API réelle
- Pipeline données/entraînement : dvc repro

## Style
- Python : ruff + black, type hints partout.
- TypeScript : strict, eslint + prettier, composants fonctionnels.
- Textes de l'interface dans frontend/src/i18n/{fr,ar}.json (jamais en dur).
