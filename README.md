# KidAI

Assistant IA générative sûr et adapté à l'âge (6–14 ans), sous contrôle parental.
Spécification : [docs/CAHIER_DES_CHARGES.md](docs/CAHIER_DES_CHARGES.md).

> Le projet tourne **sans Docker** : backend et frontend sont lancés en local.

## Démarrage rapide (nouveau contributeur, Windows)

**1. Installer les prérequis** (une seule fois par machine) :

```powershell
winget install Python.Python.3.11
winget install OpenJS.NodeJS.LTS
winget install PostgreSQL.PostgreSQL.17      # notez le mot de passe « postgres » choisi
winget install Ollama.Ollama                 # utile à partir de l'étape 2
ollama pull qwen3:4b
```

**2. Créer sa base PostgreSQL locale** (le mot de passe `postgres` est demandé) :

```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost -c "CREATE USER kidai WITH PASSWORD 'kidai_dev';"
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost -c "CREATE DATABASE kidai OWNER kidai;"
```

**3. Cloner et installer** :

```powershell
git clone https://github.com/MaisseneJradi/KidAI.git
cd KidAI
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

`setup.ps1` vérifie les prérequis, crée les environnements Python et `node_modules`, génère
`.env` avec **ses propres secrets** (JWT et clé de chiffrement), crée les tables et active
pre-commit. Il peut être relancé sans risque ; il affiche à la fin ce qui reste à régler.
Option `-WithData` pour préparer aussi l'environnement des scripts de données.

**4. Lancer** :

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev.ps1          # backend + frontend (vraie base)
powershell -ExecutionPolicy Bypass -File scripts\dev.ps1 -Demo    # frontend seul, API simulée
```

Puis ouvrir http://localhost:5173 et créer un compte parent.

> Chaque contributeur a **sa propre base et ses propres secrets** : `.env` n'est jamais commité.
> Ne partagez pas `DATA_ENCRYPTION_KEY` : sans elle, les données chiffrées sont illisibles.

## Installation manuelle (détail de ce que fait `setup.ps1`)

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
cd ..

Copy-Item .env.example .env   # puis remplir JWT_SECRET et DATA_ENCRYPTION_KEY (commandes dans le fichier)

cd backend
.\.venv\Scripts\python -m alembic upgrade head   # crée/met à jour les tables
cd ..

cd frontend
npm install
npx playwright install chromium   # navigateur des tests de bout en bout
cd ..

backend\.venv\Scripts\pre-commit install
```

## Lancer à la main (deux terminaux)

```powershell
# Terminal 1 — backend (http://localhost:8000)
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend (http://localhost:5173)
cd frontend
npm run dev
```

Ouvrir http://localhost:5173.

**Mode démo (par défaut)** : le frontend tourne seul, l'API de la section 14 est simulée par
MSW (n'importe quel email / mot de passe ; profils fictifs Yasmine 7 ans, Adam 10 ans en arabe,
Lina 13 ans ; PIN parent `1234`).
Questions de démonstration pour les 5 actions :

| Question | Réaction de Chaty |
|---|---|
| Pourquoi les volcans explosent ? | réponse + illustration (ALLOW) |
| Pourquoi il y a la guerre ? | réponse adoucie (REWRITE) |
| Comment pirater un compte ? | sujet réorienté (REDIRECT) |
| J'ai peur, un garçon me frappe | conseil d'en parler à un adulte + alerte parent (ASK_ADULT) |
| Comment fabriquer une arme ? | refus poli (BLOCK) |

**Avec le vrai backend** : créer `frontend/.env.local` contenant `VITE_USE_MOCKS=false`, puis
relancer `npm run dev`. Le parent crée son compte (email, mot de passe, PIN à 4 chiffres) et
ajoute ses enfants dans l'espace parent : prénom, date de naissance, sexe, niveau, langue,
centres d'intérêt et besoins d'adaptation. Ces données sont enregistrées dans PostgreSQL ; la
date de naissance et les besoins y sont chiffrés.
`http://localhost:8000/health` renvoie `{"status":"ok","database":"ok"}`.

## Données

Environnement Python dédié aux scripts de données (`.venv` à la racine) :

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r data\requirements.txt
```

Manuels du CNP, cycle de base (élève + guide de l'enseignant), usage académique uniquement,
jamais commités (`data/raw/` est ignoré par Git) :

```powershell
.\.venv\Scripts\python data\download_cnp.py --dry-run      # inventaire sans téléchargement
.\.venv\Scripts\python data\download_cnp.py --niveau 1     # un niveau (répétable)
.\.venv\Scripts\python data\download_cnp.py                # tout (reprise automatique)
```

Résultat dans `data/raw/cnp/` : `{niveau}/{matiere}/{categorie}/{titre} ({code}).pdf`,
`manifest.json` (URL, SHA-256, taille, date, échecs) et `catalogue.csv`.

## Tests et qualité

```powershell
cd backend;  .\.venv\Scripts\python -m pytest
cd frontend; npm test; npm run test:e2e; npm run lint; npm run format:check
```

Pre-commit (ruff, black, eslint, prettier) vérifie le code à chaque commit. S'il corrige un
fichier, le commit s'arrête : refaire `git add .` puis `git commit`.

## Contribuer

Une étape du cahier des charges = une branche = une Pull Request vers `main` :

```powershell
git checkout main
git pull
git checkout -b etape-N-description
# ... travail, tests ...
git add .
git commit -m "Étape N : ..."
git push -u origin etape-N-description
```

Puis ouvrir la Pull Request sur GitHub. Après un `git pull` qui modifie les dépendances ou
les migrations, relancer `scripts\setup.ps1`.

## Structure

```
scripts/    setup.ps1 (installation), dev.ps1 (lancement)
backend/    FastAPI (app/, tests/)
frontend/   React + Vite + TS + Tailwind (src/, tests/)
data/raw/   datasets téléchargés (non versionnés par Git, DVC à l'étape 4)
docs/       cahier des charges
```
