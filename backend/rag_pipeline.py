"""
rag_pipeline.py  (version v4 — correctif embedding + auto-index)
─────────────────────────────────────────────────────────────────
RAG agentique GED — LlamaIndex + ChromaDB + SentenceTransformers

CORRECTIFS v4 (par rapport à v3) :
  1. Nouvelle stratégie d'embedding PRIORITAIRE : SentenceTransformersEmbedding
     via llama_index.embeddings.huggingface — fonctionne même sans HF_TOKEN
     si le modèle est en cache local (ce qui est votre cas : "Loading weights" visible).
  2. Détection cache améliorée : cherche dans TOUS les chemins possibles
     (HF_HOME, SENTENCE_TRANSFORMERS_HOME, ~/.cache/torch/sentence_transformers).
  3. Flag _EMBED_MODEL_ATTEMPTED réinitialisable via reset_embed_singleton().
  4. Logging verbose du chemin cache trouvé pour faciliter le diagnostic.
  5. Warning "embeddings.position_ids UNEXPECTED" supprimé via sentence_transformers logger.

VARIABLES .env utilisées :
  RAG_EMBED_MODEL             = BAAI/bge-small-en-v1.5   (défaut)
  HF_TOKEN                    = hf_...                    (optionnel)
  RAG_DISABLED                = true                      (désactive le RAG)
  CHROMA_PATH                 = /chemin/vers/chroma        (optionnel)
  SENTENCE_TRANSFORMERS_HOME  = /chemin/cache/st           (optionnel)
"""
from __future__ import annotations

import os
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# ── Silence les warnings parasites ───────────────────────────────────────────
logging.getLogger("llama_index.core.llms.mock").setLevel(logging.ERROR)
logging.getLogger("llama_index.core.settings").setLevel(logging.ERROR)
logging.getLogger("fastembed").setLevel(logging.ERROR)
logging.getLogger("onnxruntime").setLevel(logging.ERROR)
logging.getLogger("llama_index.core").setLevel(logging.WARNING)
# Supprime le "embeddings.position_ids UNEXPECTED" de sentence_transformers
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)

# ── Paths & config ────────────────────────────────────────────────────────────
_BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR    = os.path.abspath(os.getenv("GED_DATA_DIR", os.path.join(_BASE_DIR, "data")))
CHROMA_PATH  = os.path.abspath(os.getenv("CHROMA_PATH", os.path.join(_DATA_DIR, "chroma")))
EMBED_MODEL  = os.getenv("RAG_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
HF_TOKEN     = os.getenv("HF_TOKEN", "")
RAG_DISABLED = os.getenv("RAG_DISABLED", "").lower() in ("1", "true", "yes")

os.makedirs(CHROMA_PATH, exist_ok=True)


# ── Singleton embedding MODULE-LEVEL ─────────────────────────────────────────
_EMBED_MODEL_SINGLETON = None
_EMBED_MODEL_ATTEMPTED = False


def reset_embed_singleton() -> None:
    """Permet de forcer une nouvelle tentative (utile en cas de hot-reload)."""
    global _EMBED_MODEL_SINGLETON, _EMBED_MODEL_ATTEMPTED
    _EMBED_MODEL_SINGLETON = None
    _EMBED_MODEL_ATTEMPTED = False


# ── Détection cache améliorée ─────────────────────────────────────────────────

def _find_model_in_cache(model_name: str) -> Optional[str]:
    """
    Cherche le modèle dans TOUS les caches connus.
    Retourne le chemin trouvé ou None.

    Caches inspectés (par ordre de priorité) :
      1. HF Hub cache  (~/.cache/huggingface/hub/models--BAAI--bge-small-en-v1.5)
      2. SentenceTransformers cache  (~/.cache/torch/sentence_transformers/BAAI_bge-small-en-v1.5)
      3. SENTENCE_TRANSFORMERS_HOME si défini
    """
    model_name_safe = model_name.replace("/", "_")
    model_hf_folder = "models--" + model_name.replace("/", "--")

    candidates = []

    # 1. HuggingFace Hub cache
    hf_home   = os.getenv("HF_HOME", os.path.join(os.path.expanduser("~"), ".cache", "huggingface"))
    hub_cache = os.path.join(hf_home, "hub")
    candidates.append(("HF Hub", os.path.join(hub_cache, model_hf_folder)))

    # 2. SentenceTransformers cache (torch)
    st_home_torch = os.path.join(os.path.expanduser("~"), ".cache", "torch", "sentence_transformers")
    candidates.append(("ST/torch", os.path.join(st_home_torch, model_name_safe)))
    candidates.append(("ST/torch", os.path.join(st_home_torch, model_name.replace("/", "_"))))

    # 3. SENTENCE_TRANSFORMERS_HOME env var
    st_home_env = os.getenv("SENTENCE_TRANSFORMERS_HOME", "")
    if st_home_env:
        candidates.append(("ST env", os.path.join(st_home_env, model_name_safe)))

    # 4. HF datasets cache (parfois utilisé par certaines versions)
    candidates.append(("HF datasets", os.path.join(hf_home, "datasets", model_hf_folder)))

    for label, path in candidates:
        if os.path.isdir(path):
            logger.info(f"[RAG] Modèle trouvé en cache [{label}] : {path}")
            return path

    logger.debug(f"[RAG] Modèle '{model_name}' non trouvé dans les caches :")
    for label, path in candidates:
        logger.debug(f"  [{label}] {path} → absent")
    return None


# ── Construction du modèle d'embedding ───────────────────────────────────────

def _build_embed_model():
    """
    Construit le modèle d'embedding (appelé une seule fois).

    Ordre des stratégies :
      S1. HuggingFaceEmbedding depuis cache local (local_files_only=True)
      S2. HuggingFaceEmbedding avec téléchargement (si HF_TOKEN présent)
      S3. FastEmbedEmbedding (ONNX, sans compte HF)
      S4. Dégradation gracieuse → None (RAG désactivé)
    """
    cached_path = _find_model_in_cache(EMBED_MODEL)

    # ── Stratégie 1 : cache local (prioritaire si modèle trouvé) ─────────────
    if cached_path:
        logger.info(f"[RAG] S1 — Chargement depuis cache local : {EMBED_MODEL}")
        try:
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
            embed = HuggingFaceEmbedding(
                model_name       = EMBED_MODEL,
                token            = HF_TOKEN or None,
                local_files_only = True,
                trust_remote_code= False,
            )
            # Test rapide pour vérifier que l'embedding fonctionne
            _ = embed.get_text_embedding("test")
            logger.info(f"[RAG] S1 OK — {EMBED_MODEL} chargé depuis cache")
            return embed
        except Exception as e:
            logger.warning(f"[RAG] S1 échoué (HuggingFaceEmbedding cache) : {e}")

    # ── Stratégie 2 : téléchargement HuggingFace Hub ─────────────────────────
    if HF_TOKEN:
        logger.info(f"[RAG] S2 — Téléchargement {EMBED_MODEL} via HuggingFace Hub …")
        try:
            import huggingface_hub
            huggingface_hub.login(token=HF_TOKEN, add_to_git_credential=False)
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
            embed = HuggingFaceEmbedding(
                model_name       = EMBED_MODEL,
                token            = HF_TOKEN,
                local_files_only = False,
                trust_remote_code= False,
            )
            _ = embed.get_text_embedding("test")
            logger.info(f"[RAG] S2 OK — {EMBED_MODEL} téléchargé et chargé")
            return embed
        except Exception as e:
            logger.warning(f"[RAG] S2 échoué (HuggingFace Hub) : {e}")
    else:
        logger.info("[RAG] S2 skipped — HF_TOKEN absent")

    # ── Stratégie 3 : FastEmbed ONNX (sans compte HF) ────────────────────────
    logger.info("[RAG] S3 — Tentative FastEmbedEmbedding (ONNX) …")
    try:
        from llama_index.embeddings.fastembed import FastEmbedEmbedding
        embed = FastEmbedEmbedding(model_name="BAAI/bge-small-en-v1.5")
        _ = embed.get_text_embedding("test")
        logger.info("[RAG] S3 OK — FastEmbed BAAI/bge-small-en-v1.5 actif")
        return embed
    except ImportError:
        logger.warning(
            "[RAG] S3 échoué — llama-index-embeddings-fastembed non installé\n"
            "  → pip install llama-index-embeddings-fastembed fastembed"
        )
    except Exception as e:
        logger.warning(f"[RAG] S3 échoué (FastEmbed) : {e}")

    # ── Stratégie 4 : dégradation gracieuse ──────────────────────────────────
    logger.error(
        "[RAG] ✗ Aucun modèle d'embedding disponible. RAG désactivé.\n"
        "\n"
        "  DIAGNOSTIC : le modèle charge ('Loading weights: 100%') mais échoue\n"
        "  à l'instanciation Python. Vérifiez :\n"
        "\n"
        "  Option A — Forcer le cache HF (recommandé, 0 réseau) :\n"
        "    python -c \"from sentence_transformers import SentenceTransformer; "
        "SentenceTransformer('BAAI/bge-small-en-v1.5')\"\n"
        "\n"
        "  Option B — Ajouter HF_TOKEN dans .env :\n"
        "    HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx\n"
        "\n"
        "  Option C — FastEmbed (ONNX, sans compte HF) :\n"
        "    pip install llama-index-embeddings-fastembed fastembed\n"
        "\n"
        "  Option D — Packages manquants :\n"
        "    pip install llama-index-embeddings-huggingface sentence-transformers\n"
    )
    return None


def _get_embed_model_singleton():
    """Retourne le singleton, en le créant si besoin (une seule fois par process)."""
    global _EMBED_MODEL_SINGLETON, _EMBED_MODEL_ATTEMPTED
    if _EMBED_MODEL_ATTEMPTED:
        return _EMBED_MODEL_SINGLETON
    _EMBED_MODEL_ATTEMPTED = True
    _EMBED_MODEL_SINGLETON = _build_embed_model()
    return _EMBED_MODEL_SINGLETON


# ── MockLLM silencieux ────────────────────────────────────────────────────────

def _make_silent_mock_llm():
    try:
        from llama_index.core.llms import MockLLM
        return MockLLM()
    except Exception:
        return None


# ── RagPipeline ───────────────────────────────────────────────────────────────

class RagPipeline:
    """
    Pipeline RAG complet — LlamaIndex + ChromaDB.
    Singleton applicatif ; l'embedding est un singleton module-level,
    donc le modèle n'est chargé qu'une seule fois.
    """

    def __init__(self) -> None:
        self._index             = None
        self._chroma_collection = None
        self._initialized       = False
        self._disabled          = RAG_DISABLED

        if self._disabled:
            logger.info("[RAG] RAG_DISABLED=true — RAG skippé.")

    # ── Initialisation paresseuse ─────────────────────────────────────────────

    def _ensure_initialized(self) -> bool:
        if self._disabled:
            return False
        if self._initialized:
            return True
        try:
            self._init()
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"[RAG] Initialisation échouée : {e}")
            self._disabled = True
            return False

    def _init(self) -> None:
        import chromadb
        from llama_index.core import VectorStoreIndex, StorageContext, Settings
        from llama_index.vector_stores.chroma import ChromaVectorStore

        # ── Embedding singleton ───────────────────────────────────────────────
        embed_model = _get_embed_model_singleton()
        if embed_model is None:
            raise RuntimeError(
                "Aucun modèle d'embedding disponible. "
                "Consultez les logs pour les options de résolution."
            )

        # ── Settings LlamaIndex ───────────────────────────────────────────────
        Settings.embed_model = embed_model
        mock_llm = _make_silent_mock_llm()
        if mock_llm is not None:
            Settings.llm = mock_llm
        else:
            _ml = logging.getLogger("llama_index.core.llms.mock")
            _old = _ml.level
            _ml.setLevel(logging.CRITICAL)
            Settings.llm = None
            _ml.setLevel(_old)

        # ── ChromaDB persistant ───────────────────────────────────────────────
        chroma_client           = chromadb.PersistentClient(path=CHROMA_PATH)
        self._chroma_collection = chroma_client.get_or_create_collection(
            name="ged_documents",
            metadata={"hnsw:space": "cosine"},
        )

        vector_store    = ChromaVectorStore(chroma_collection=self._chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        try:
            self._index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store,
                embed_model=embed_model,
            )
            logger.info(
                f"[RAG] ✓ Index ChromaDB chargé : "
                f"{self._chroma_collection.count()} vecteurs | "
                f"modèle={EMBED_MODEL}"
            )
        except Exception:
            self._index = VectorStoreIndex(
                [],
                storage_context=storage_context,
                embed_model=embed_model,
            )
            logger.info(f"[RAG] ✓ Nouvel index ChromaDB créé | modèle={EMBED_MODEL}")

    # ── Indexation ────────────────────────────────────────────────────────────

    def index_document(
        self,
        doc_id:   str,
        user_id:  str,
        filename: str,
        text:     str,
        doc_type: str = "",
        file_id:  str = "",
    ) -> int:
        if not text or not text.strip():
            return 0
        if not self._ensure_initialized():
            return 0

        from llama_index.core import Document
        from llama_index.core.node_parser import SentenceSplitter

        splitter  = SentenceSplitter(chunk_size=512, chunk_overlap=50)
        llama_doc = Document(
            text=text,
            metadata={
                "doc_id":   doc_id,
                "user_id":  user_id,
                "filename": filename,
                "doc_type": doc_type,
                "file_id":  file_id or doc_id,
            },
            excluded_llm_metadata_keys=["user_id", "file_id"],
            excluded_embed_metadata_keys=["user_id", "file_id"],
        )

        nodes = splitter.get_nodes_from_documents([llama_doc])
        self._delete_document_chunks(doc_id)
        self._index.insert_nodes(nodes)

        logger.info(f"[RAG] Indexé doc_id={doc_id} '{filename}' : {len(nodes)} chunks")
        return len(nodes)

    def index_multiple_files(
        self,
        doc_id:   str,
        user_id:  str,
        files:    List[dict],
        doc_type: str = "",
    ) -> dict:
        total_chunks = 0
        results      = []
        for f in files:
            text = (f.get("textContent") or f.get("text") or "").strip()
            if not text:
                results.append({"file_id": f.get("file_id"), "status": "skipped"})
                continue
            n = self.index_document(
                doc_id=doc_id,
                user_id=user_id,
                filename=f.get("filename", "fichier"),
                text=text,
                doc_type=doc_type,
                file_id=str(f.get("file_id", "")),
            )
            total_chunks += n
            results.append({
                "file_id": f.get("file_id"),
                "chunks":  n,
                "status":  "ok" if n > 0 else "skipped (RAG désactivé ou texte vide)",
            })
        return {"doc_id": doc_id, "total_chunks": total_chunks, "files": results}

    def _delete_document_chunks(self, doc_id: str) -> None:
        try:
            if not self._chroma_collection:
                return
            existing = self._chroma_collection.get(
                where={"doc_id": {"$eq": doc_id}}
            )
            if existing and existing.get("ids"):
                self._chroma_collection.delete(ids=existing["ids"])
        except Exception as e:
            logger.warning(f"[RAG] _delete_document_chunks : {e}")

    # ── Recherche ─────────────────────────────────────────────────────────────

    def search(self, query: str, user_id: str, top_k: int = 5) -> List[dict]:
        if not query or not query.strip():
            return []
        if not self._ensure_initialized():
            return []
        try:
            from llama_index.core import QueryBundle
            retriever = self._index.as_retriever(
                similarity_top_k=top_k,
                filters=_build_metadata_filter(user_id),
            )
            nodes = retriever.retrieve(QueryBundle(query_str=query))
            return [
                {
                    "text":     node.node.get_content(),
                    "score":    float(node.score or 0),
                    "doc_id":   node.node.metadata.get("doc_id", ""),
                    "filename": node.node.metadata.get("filename", ""),
                    "doc_type": node.node.metadata.get("doc_type", ""),
                    "file_id":  node.node.metadata.get("file_id", ""),
                    "user_id":  node.node.metadata.get("user_id", ""),
                }
                for node in nodes
            ]
        except Exception as e:
            logger.error(f"[RAG] search error : {e}")
            return []

    def search_formatted(self, query: str, user_id: str, top_k: int = 5) -> str:
        results = self.search(query=query, user_id=user_id, top_k=top_k)
        if not results:
            return ""
        parts     = ["=== RECHERCHE SÉMANTIQUE (RAG) ==="]
        seen_docs = set()
        for r in results:
            doc_key    = r["doc_id"]
            doc_header = f"[{r['filename']}]" if r["filename"] else f"[Doc {r['doc_id']}]"
            if r.get("doc_type"):
                doc_header += f" ({r['doc_type']})"
            if doc_key not in seen_docs:
                parts.append(f"\n{doc_header}")
                seen_docs.add(doc_key)
            parts.append(r["text"][:500])
        return "\n".join(parts)

    def get_document_chunks(self, doc_id: str, user_id: str) -> List[dict]:
        if not self._ensure_initialized():
            return []
        try:
            results = self._chroma_collection.get(
                where={"$and": [
                    {"doc_id":  {"$eq": doc_id}},
                    {"user_id": {"$eq": user_id}},
                ]},
                include=["documents", "metadatas"],
            )
            if not results or not results.get("ids"):
                return []
            return [
                {"chunk_id": cid, "text": doc, "metadata": meta}
                for cid, doc, meta in zip(
                    results["ids"], results["documents"], results["metadatas"]
                )
            ]
        except Exception as e:
            logger.error(f"[RAG] get_document_chunks error : {e}")
            return []

    def get_stats(self) -> dict:
        if not self._ensure_initialized():
            return {
                "total_chunks": 0,
                "embed_model":  EMBED_MODEL,
                "status":       "disabled — voir logs pour la raison",
            }
        try:
            return {
                "total_chunks": self._chroma_collection.count(),
                "chroma_path":  CHROMA_PATH,
                "embed_model":  EMBED_MODEL,
                "status":       "ok",
            }
        except Exception as e:
            return {"total_chunks": 0, "status": f"error: {e}"}

    def delete_user_documents(self, user_id: str) -> int:
        if not self._ensure_initialized():
            return 0
        try:
            existing = self._chroma_collection.get(
                where={"user_id": {"$eq": user_id}}
            )
            if existing and existing.get("ids"):
                self._chroma_collection.delete(ids=existing["ids"])
                return len(existing["ids"])
        except Exception as e:
            logger.error(f"[RAG] delete_user_documents : {e}")
        return 0

    @property
    def is_available(self) -> bool:
        return self._ensure_initialized()


# ── Helper filtre métadonnées ─────────────────────────────────────────────────

def _build_metadata_filter(user_id: str):
    from llama_index.core.vector_stores.types import (
        MetadataFilter, MetadataFilters, FilterOperator,
    )
    return MetadataFilters(filters=[
        MetadataFilter(key="user_id", value=user_id, operator=FilterOperator.EQ)
    ])


# ── Singleton applicatif ──────────────────────────────────────────────────────

_rag_instance: Optional[RagPipeline] = None


def get_rag_pipeline() -> RagPipeline:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RagPipeline()
    return _rag_instance