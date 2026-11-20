# Données KidAI

Usage académique uniquement.

- **Dans Git** (un `git pull` suffit) : `processed/` (dataset final, traductions, synthétiques,
  statistiques), `cache/` (réponses du LLM : des jours de calcul) et `annotation/` (travail
  humain de l'équipe). DVC garde leurs empreintes dans `dvc.lock`.
- **Dans Git LFS** (`git lfs install` une fois, puis `git pull`) : les données du RAG,
  `processed/cnp/` (texte extrait des manuels CNP) et `qdrant/` (index). Elles sont sous droits :
  **le dépôt doit rester privé**. Chaque réindexation ajoute ~240 Mo au quota LFS du propriétaire
  (10 Gio de stockage, 10 Gio de téléchargement par mois, pull des collaborateurs compris) :
  ne les recommiter que pour une vraie nouvelle version.
- **Hors Git** : `raw/`, PDF des manuels compris (retéléchargés par `python data\download.py` et
  `python data\download_cnp.py`).

Après un `git pull`, le dataset est utilisable tel quel. Pour relancer le pipeline, il faut
d'abord les données brutes (`python data\download.py`) ; grâce au cache, `dvc repro` ne refait
alors aucune traduction déjà faite.

## Sources (cahier des charges, section 9.1)

| # | Dataset | Dossier | Licence | Utilisé pour |
|---|---|---|---|---|
| D1 | KIDBench (MichiganNLP) | `raw/kidbench` | MIT | 500 questions × 2 variantes (avec / sans indices d'enfant) + 103 questions réelles (« wild ») |
| D2 | MinorBench (GovTech) | `raw/minorbench` | MIT | 299 questions inadaptées aux enfants |
| D3 | OR-Bench | `raw/orbench` | CC BY 4.0 | échantillon : 500 « semblent dangereuses » (hard-1k) + 300 toxiques |
| D4 | Safe-Child-LLM | `raw/safechild` | MIT (code) ; données à citer | 200 questions piégées (6-12 et 13-17 ans) |
| D5 | PKU-SafeRLHF | `raw/pku_saferlhf` | CC BY-NC 4.0 | paires de réponses sécurité / utilité (modèle de récompense) |
| D6 | T-HSAB | `raw/thsab` | à citer (article des auteurs) | commentaires en derja : normal / abusive / hate |
| D7 | TEET | — | — | non obtenu (données sur demande aux auteurs) |
| D8 | Manuels CNP | `raw/cnp` | droits CNP | corpus du RAG, voir `rag/README.md` |
| D9 | Synthétiques | `cache/synthetic.jsonl` | équipe | questions générées en FR par sujet et âge, traduites en AR |

Les KIDBench multi-tours (scénarios, pas des questions) et les données SFT dérivées
(`gold/`, `judge/`) ne sont pas reprises : elles serviront au MDP multi-tours (V2).

## Pipeline (`dvc repro`)

À lancer depuis la racine, `.venv` activé (`.\.venv\Scripts\Activate.ps1`) : les étapes
appellent `python`, qui doit être celui du `.venv`. Ollama doit tourner avec `qwen3:4b` et
`llama3.1:8b`.

```
download ─> normalize ─┬─> translate ─┐
                       │              ├─> build ─> stats
            synthetic ─┴──────────────┘     ↑
                              annotation/ ──┘
```

| Étape | Code | Résultat |
|---|---|---|
| download | `download.py` | `raw/` (clones Git et Hugging Face ; laisse intact ce qui est déjà là) |
| normalize | `prep/sources.py` | `processed/base_en.parquet` (questions anglaises, sans doublons), `pku_preferences.parquet`, `thsab_derja.parquet` |
| translate | `prep/translate.py` | traductions FR (qwen3:4b) et AR (llama3.1:8b) via Ollama, contrôlées ; cache `cache/translations.jsonl` |
| synthetic | `prep/synthetic.py` | D9 : 15 sujets × 3 tranches d'âge, générées en français (llama3.1:8b) puis traduites en arabe |
| build | `prep/build.py` | `processed/kidai_dataset.parquet` |
| stats | `prep/stats.py` | `processed/kidai_stats.md` (rapport) et `kidai_stats.json` (métriques DVC) |

Chaque étape se lance aussi seule : `.venv\Scripts\python data\prepare.py <étape>`.
Les paramètres (tailles d'échantillon, modèles, taille du test, graine) sont dans
`params.yaml` à la racine. Les appels au LLM sont mis en cache : une relance ne refait que ce
qui manque, et `dvc repro` ne relance que les étapes dont une dépendance a changé.

## Format de `kidai_dataset.parquet` (section 9.2)

| Colonne | Valeurs |
|---|---|
| `id` | `{qid}_{lang}_{age}`, ex. `kb_00123c_fr_09` (`c` = variante KIDBench avec indices) |
| `question` | texte |
| `lang` | `en` / `fr` / `ar` (`derja` prévu, pas encore produit) |
| `age`, `grade` | 6-14 ; `1re_annee` … `9e_annee` (6 ans = 1re année) |
| `topic` | 17 sujets : `curiosite`, `sciences`, `maths`, `culture`, `sante`, `emotions`, `relations`, `ecole`, `numerique`, `morale`, `sexualite`, `violence`, `discrimination`, `danger`, `substances`, `illegal`, `langage` |
| `source` | `kidbench` / `minorbench` / `orbench` / `safechild` / `synthetic` |
| `ground_truth_harm` | `safe` / `borderline` / `unsafe`, dérivé de la source (ci-dessous) |
| `expected_action` | seulement pour le test annoté : `ALLOW` / `REWRITE` / `REDIRECT` / `ASK_ADULT` / `BLOCK` |
| `split` | `train` / `val` / `test` |
| en plus | `base_id` (question d'origine, clé anti-fuite), `qid` (variante), `category` (catégorie d'origine), `variant`, `translated` |

**Risque dérivé de la source.** KIDBench : `benign_information_seeking` → safe, les 9 autres
catégories et les questions « wild » → borderline. MinorBench → unsafe. OR-Bench hard →
borderline, toxic → unsafe. Safe-Child : crise de santé mentale et « chatbot traité comme un
humain » → borderline, le reste → unsafe. Synthétiques : sujets scolaires → safe, sujets
sensibles (émotions, puberté, mort, disputes, écrans) → borderline.

**Âges.** Chaque question (et chacune de ses traductions) apparaît trois fois, une par tranche
6-8 / 9-11 / 12-14, à un âge tiré au hasard (reproductible) dans la tranche. Une question
synthétique, écrite pour une tranche, n'apparaît qu'à celle-ci.

**Splits sans fuite.** Le découpage se fait par `base_id` : variantes, traductions et âges
d'une même question restent dans le même split. Les doublons exacts entre sources sont retirés
avant. Le test compte 120 questions de base, stratifiées par source et risque, chacune dans une
seule langue (FR, AR, EN en alternance) et à deux âges (6-8 et 12-14), soit ≈ 240 lignes à
annoter. Validation : 10 % du reste, par source.

**Fichiers à part** (rôles différents dans le cahier) : `pku_preferences.parquet` (D5) et
`thsab_derja.parquet` (D6, split 80/10/10 stratifié par label).

## Limites connues

- Pas de derja dans le dataset principal : les modèles locaux la traduisent mal (essais
  qwen3:4b et llama3.1:8b, même avec exemples). La derja n'est couverte que par T-HSAB.
- Le risque est dérivé de la source, pas annoté question par question (sauf le test).
- Traductions automatiques : 10 % sont relues à la main (`annotation/translation_review.csv`).
