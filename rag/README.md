# RAG — manuels du CNP

Index vectoriel des manuels scolaires tunisiens (cycle de base, élève + guide de l'enseignant),
pour ancrer les réponses de Kotty dans le programme (cahier des charges, section 12).

> Usage académique uniquement. Les PDF (`data/raw/`), le texte extrait (`data/processed/cnp/`) et
> l'index (`data/qdrant/`) ne sont **jamais** commités.

## Pipeline

```
data/raw/cnp/*.pdf ──extract──> data/processed/cnp/pages/<doc>.jsonl   (texte page par page)
                   ──chunk────> data/processed/cnp/chunks/<doc>.jsonl  (fragments + métadonnées)
                   ──index────> data/qdrant/  collection « cnp_manuels » (bge-m3, cosinus)
```

| Étape | Module | Ce qu'elle fait |
|---|---|---|
| extract | `rag/extract.py` | `pdftotext` si le texte est propre ; sinon rendu 300 dpi (`pdftoppm`) + OCR Tesseract (`ara`, `fra` ou `eng` selon la matière). Pages en parallèle. |
| chunk | `rag/chunk.py` | Nettoyage (NFKC, sans voyelles brèves), sections par unité (« الوحدة », « المحور », Module…) et leçon (« الموضوع », « الدرس », Leçon…), fenêtres de ≈ 400 tokens bge-m3, chevauchement 50. |
| index | `rag/index.py` | Embeddings `BAAI/bge-m3` (GPU fp16 si disponible), ajout dans Qdrant en mode local. |
| search | `rag/search.py` | Filtre niveau ≤ niveau de l'enfant (+ langue, matière), top-k = 4, seuil 0,45. |

Pourquoi l'OCR : presque tous les manuels en arabe utilisent une police non Unicode ou des
formes de présentation ; `pdftotext` en sort du texte illisible. Les manuels de français et
d'anglais, eux, ont un texte propre.

Chaque étape reprend là où elle s'est arrêtée (pages déjà extraites, fragments déjà indexés).

## Installation

Outils externes : Poppler et Tesseract 5 avec la langue arabe.

```powershell
winget install oschwartz10612.Poppler
winget install UB-Mannheim.TesseractOCR      # cocher « Arabic » dans les langues
```

Environnement Python (`.venv` à la racine) :

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124
.\.venv\Scripts\python -m pip install -r rag\requirements.txt
```

(sans GPU NVIDIA : `--index-url https://download.pytorch.org/whl/cpu`). Le modèle bge-m3
(≈ 2,3 Go) est téléchargé au premier lancement.

## Utilisation

```powershell
# Tout le corpus (≈ 25 000 pages : ~1 h 30 d'OCR sur un i7 à 12 processus)
.\.venv\Scripts\python -m rag.ingest

# Un sous-ensemble, ex. éveil scientifique 4e–6e
.\.venv\Scripts\python -m rag.ingest --niveau 4 --niveau 5 --niveau 6 --matiere 03

# Refaire le découpage et l'index sans refaire l'OCR
.\.venv\Scripts\python -m rag.ingest --etapes chunk,index --reconstruire

# Chercher
.\.venv\Scripts\python -m rag.search "لماذا لا تطير النعامة؟" --niveau 5 --langue ar
```

## Tests

```powershell
.\.venv\Scripts\python -m pytest rag\tests
```

## Limites connues

- L'OCR fait quelques erreurs de lettres (« الحيوانم ») et manque souvent les titres en police
  décorative.
- La détection des leçons repose sur des mots-clés : dans les guides de l'enseignant, le
  sommaire peut fausser l'étiquette `chapter` d'un fragment (le texte retrouvé reste juste).
- Qdrant en mode local est prévu pour ≲ 20 000 fragments ; au-delà, passer à un serveur Qdrant.
- Reste à faire (étape 6) : l'évaluation recall@4 sur 50 questions et le branchement dans la
  génération des réponses.
