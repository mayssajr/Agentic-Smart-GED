#!/usr/bin/env python3
"""
diagnose_rag.py — Lance ce script depuis la racine du projet pour diagnostiquer
                  pourquoi le RAG échoue à trouver le modèle d'embedding.

Usage :
    python diagnose_rag.py
"""
import os, sys

MODEL = "BAAI/bge-small-en-v1.5"
print(f"\n{'='*60}")
print(f"  DIAGNOSTIC RAG — modèle : {MODEL}")
print(f"{'='*60}\n")

# 1. Chemins de cache inspectés
print("1. CACHES INSPECTÉS")
print("-" * 40)
hf_home = os.getenv("HF_HOME", os.path.join(os.path.expanduser("~"), ".cache", "huggingface"))
candidates = {
    "HF Hub"       : os.path.join(hf_home, "hub", "models--" + MODEL.replace("/", "--")),
    "ST/torch"     : os.path.join(os.path.expanduser("~"), ".cache", "torch",
                                   "sentence_transformers", MODEL.replace("/", "_")),
    "ST/torch (2)" : os.path.join(os.path.expanduser("~"), ".cache", "torch",
                                   "sentence_transformers", MODEL.replace("/", "__")),
}
st_env = os.getenv("SENTENCE_TRANSFORMERS_HOME", "")
if st_env:
    candidates["ST env"] = os.path.join(st_env, MODEL.replace("/", "_"))

found = False
for label, path in candidates.items():
    exists = os.path.isdir(path)
    status = "✓ TROUVÉ" if exists else "✗ absent"
    print(f"  [{status}] {label:12s} : {path}")
    if exists:
        found = True

if not found:
    print("\n  ⚠️  Aucun cache trouvé. Lancez :")
    print("     python -c \"from sentence_transformers import SentenceTransformer; "
          f"SentenceTransformer('{MODEL}')\"")

# 2. Packages installés
print("\n2. PACKAGES PYTHON")
print("-" * 40)
packages = [
    ("llama-index-core",                    "llama_index.core"),
    ("llama-index-embeddings-huggingface",  "llama_index.embeddings.huggingface"),
    ("llama-index-embeddings-fastembed",    "llama_index.embeddings.fastembed"),
    ("llama-index-vector-stores-chroma",    "llama_index.vector_stores.chroma"),
    ("sentence-transformers",               "sentence_transformers"),
    ("chromadb",                            "chromadb"),
    ("fastembed",                           "fastembed"),
    ("huggingface-hub",                     "huggingface_hub"),
]
for pkg_name, import_path in packages:
    try:
        mod = __import__(import_path.split(".")[0])
        ver = getattr(mod, "__version__", "?")
        print(f"  ✓ {pkg_name:45s} v{ver}")
    except ImportError:
        print(f"  ✗ {pkg_name:45s} NON INSTALLÉ")

# 3. Variables d'env
print("\n3. VARIABLES D'ENVIRONNEMENT")
print("-" * 40)
env_vars = ["HF_TOKEN", "HF_HOME", "RAG_DISABLED", "RAG_EMBED_MODEL",
            "CHROMA_PATH", "SENTENCE_TRANSFORMERS_HOME"]
for v in env_vars:
    val = os.getenv(v, "")
    if v == "HF_TOKEN" and val:
        val = val[:8] + "..." + val[-4:]
    print(f"  {v:30s} = {val or '(non défini)'}")

# 4. Test embedding direct
print("\n4. TEST EMBEDDING DIRECT")
print("-" * 40)

# 4a. HuggingFaceEmbedding (local_files_only)
try:
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    emb = HuggingFaceEmbedding(model_name=MODEL, local_files_only=True)
    vec = emb.get_text_embedding("test rapide")
    print(f"  ✓ HuggingFaceEmbedding (local_files_only) → dim={len(vec)}")
except Exception as e:
    print(f"  ✗ HuggingFaceEmbedding (local_files_only) : {e}")

# 4b. HuggingFaceEmbedding (download)
try:
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    emb = HuggingFaceEmbedding(model_name=MODEL, local_files_only=False)
    vec = emb.get_text_embedding("test rapide")
    print(f"  ✓ HuggingFaceEmbedding (download OK)      → dim={len(vec)}")
except Exception as e:
    print(f"  ✗ HuggingFaceEmbedding (download) : {e}")

# 4c. FastEmbed
try:
    from llama_index.embeddings.fastembed import FastEmbedEmbedding
    emb = FastEmbedEmbedding(model_name=MODEL)
    vec = emb.get_text_embedding("test rapide")
    print(f"  ✓ FastEmbedEmbedding                      → dim={len(vec)}")
except Exception as e:
    print(f"  ✗ FastEmbedEmbedding : {e}")

# 4d. SentenceTransformer brut
try:
    from sentence_transformers import SentenceTransformer
    st = SentenceTransformer(MODEL)
    vec = st.encode("test rapide")
    print(f"  ✓ SentenceTransformer (brut)               → dim={len(vec)}")
except Exception as e:
    print(f"  ✗ SentenceTransformer (brut) : {e}")

print(f"\n{'='*60}")
print("  RÉSUMÉ")
print(f"{'='*60}")
print("  Copiez la sortie complète pour partager le diagnostic.\n")
