"""Index vectoriel Qdrant (mode local, sans serveur) des fragments de manuels.

Embeddings : BAAI/bge-m3 (multilingue FR/AR), vecteurs denses normalisés, distance cosinus.
Reprise : les fragments déjà présents dans la collection ne sont pas recalculés.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from functools import lru_cache

from qdrant_client import QdrantClient, models

from rag import config
from rag.chunk import Chunk

Embedder = Callable[[Sequence[str]], list[list[float]]]

BATCH = 64


def point_id(chunk_id: str) -> str:
    """Identifiant stable : relancer l'indexation remplace le point au lieu de le dupliquer."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"kidai/cnp/{chunk_id}"))


@lru_cache
def client() -> QdrantClient:
    config.QDRANT_DIR.mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=str(config.QDRANT_DIR))


def ensure_collection(qc: QdrantClient, recreate: bool = False) -> None:
    exists = qc.collection_exists(config.COLLECTION)
    if exists and recreate:
        qc.delete_collection(config.COLLECTION)
        exists = False
    if not exists:
        qc.create_collection(
            config.COLLECTION,
            vectors_config=models.VectorParams(
                size=config.EMBEDDING_DIM, distance=models.Distance.COSINE
            ),
        )


@lru_cache
def bge_embedder() -> Embedder:
    """bge-m3 sur GPU si disponible (fp16 pour tenir dans 4 Go), sinon sur CPU."""
    import torch
    from sentence_transformers import SentenceTransformer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer(config.EMBEDDING_MODEL, device=device)
    if device == "cuda":
        model.half()
    model.max_seq_length = 512

    def embed(texts: Sequence[str]) -> list[list[float]]:
        vectors = model.encode(
            list(texts), batch_size=16, normalize_embeddings=True, show_progress_bar=False
        )
        return vectors.tolist()

    return embed


def index_chunks(
    chunks: list[Chunk],
    embed: Embedder,
    qc: QdrantClient,
    progress: Callable[[str], None] = print,
) -> int:
    """Ajoute les fragments absents de la collection. Renvoie le nombre de fragments ajoutés."""
    added = 0
    for start in range(0, len(chunks), BATCH):
        batch = chunks[start : start + BATCH]
        ids = [point_id(c.chunk_id) for c in batch]
        existing = {str(p.id) for p in qc.retrieve(config.COLLECTION, ids, with_payload=False)}
        todo = [(c, i) for c, i in zip(batch, ids, strict=True) if i not in existing]
        if todo:
            vectors = embed([c.text for c, _ in todo])
            qc.upsert(
                config.COLLECTION,
                points=[
                    models.PointStruct(id=i, vector=v, payload=c.payload())
                    for (c, i), v in zip(todo, vectors, strict=True)
                ],
            )
            added += len(todo)
        progress(f"    {min(start + BATCH, len(chunks))}/{len(chunks)} fragments")
    return added
