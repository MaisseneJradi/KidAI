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
- **La mascotte s'appelle Kotty** (كوتي en arabe), et non Nouri comme dans le cahier : petit
  hibou-robot original. Utiliser « Kotty » partout (code, textes, prompts système de l'Annexe C).
- **Pas de langue dans le profil enfant** (ni `children.lang`, section 15, ni formulaire parent) :
  la langue se choisit dans Réglages et s'applique à l'appareil.
  Exception (décidée à l'étape 3) : une question écrite majoritairement en lettres arabes reçoit
  une réponse en arabe, même sur un appareil en français (backend : app/core/lang.py).
  La derja en lettres latines suit la langue des Réglages.
- **LLM : `qwen3:4b-instruct`** et non `qwen3:4b` : le tag `qwen3:4b` est la variante
  « Thinking-2507 » (réflexion obligatoire, 45-60 s par réponse, incompatible avec NF-01).
  `OLLAMA_THINK=true` seulement si on revient à un modèle qui réfléchit.
- **Actions (étape 5)** : ASK_ADULT et BLOCK sont rédigés par Kotty (prompts de l'Annexe C) puis
  contrôlés, avec repli sur un texte pré-écrit (jamais d'erreur pour ASK_ADULT). Deux ajouts à
  l'Annexe C : ASK_ADULT ne se termine pas par une question pour relancer un autre sujet, et un
  secret à cacher aux parents (signal d'emprise) reçoit toujours le texte pré-écrit « secret »
  (le modèle 4B approuvait parfois le secret). Politique B2 : app/services/policy.py, mots-clés
  complémentaires du gardien : app/services/signals.py (à faire relire en arabe et derja).
- **Données du RAG dans Git LFS** (`data/processed/cnp/`, `data/qdrant/`) : le dépôt GitHub doit
  rester **privé** (manuels CNP sous droits). Les PDF (`data/raw/cnp/`) restent hors Git.
- **CI : GitHub Actions** (`.github/workflows/ci.yml`) au lieu de GitLab CI : le dépôt est sur GitHub.
- **Monitoring sans Docker** : Prometheus et Grafana portables, téléchargés et lancés par
  `scripts\monitoring.ps1` ; configuration et tableaux de bord dans `ops/`.
- **PostgreSQL 17** installé en local (service Windows `postgresql-x64-17`, port 5432),
  base `kidai`, utilisateur `kidai`. URL dans `.env` (`DATABASE_URL`).

## Stack
Frontend : React 18 + Vite + TypeScript + Tailwind + Framer Motion + react-i18next (FR/AR RTL) + PWA
Backend : Python 3.11, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 17
IA : Ollama (qwen3), Qwen3Guard (mode strict), ShieldGemma 2, FLUX.1-schnell/SD-Turbo, Qdrant + bge-m3
RL : Gymnasium + Stable-Baselines3 ; MLOps : DVC, MLflow, GitLab CI, Prometheus, Grafana, Loki

## Commandes (Windows / PowerShell)
- Installation après un clone : powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
- Tout lancer : powershell -ExecutionPolicy Bypass -File scripts\dev.ps1   (-Demo : API simulée)
- Backend : cd backend ; .\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
- Frontend : cd frontend ; npm run dev   (http://localhost:5173)
- Tests backend : cd backend ; .\.venv\Scripts\python -m pytest
- Tests avec les vrais modèles (Ollama) : $env:KIDAI_REAL_MODELS = "1" ; .\.venv\Scripts\python -m pytest -m real_models
- Évaluation sécurité (20 exemples, rapport docs/evaluation/etape3_securite.md) : cd backend ; .\.venv\Scripts\python -m scripts.eval_safety
- Démo des 5 actions, vrais modèles (rapport docs/evaluation/etape5_actions.md) : cd backend ; .\.venv\Scripts\python -m scripts.demo_actions
- Tests frontend : cd frontend ; npm test ; npm run test:e2e
- Monitoring : powershell -ExecutionPolicy Bypass -File scripts\monitoring.ps1 [-ApiPort 8010]   (Prometheus :9090, Grafana :3000 ; métriques API sur /metrics)
- Frontend en mode démo (MSW, sans backend) par défaut ; VITE_USE_MOCKS=false pour l'API réelle
- RAG CNP (venv racine .venv) : .\.venv\Scripts\python -m rag.ingest ; tests : -m pytest rag\tests
- Pipeline données/entraînement : .\.venv\Scripts\Activate.ps1 ; dvc repro (paramètres : params.yaml ; venv activé obligatoire, les étapes appellent « python »)
- Dataset, une étape : .\.venv\Scripts\python data\prepare.py normalize|translate|synthetic|build|stats|annotate ; tests : -m pytest data\tests
- Dataset : pas de derja traduite automatiquement (qualité insuffisante en local) ; derja = T-HSAB uniquement pour l'instant

## Style
- Python : ruff + black, type hints partout.
- TypeScript : strict, eslint + prettier, composants fonctionnels.
- Textes de l'interface dans frontend/src/i18n/{fr,ar}.json (jamais en dur).
