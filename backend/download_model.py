"""
download_model.py
─────────────────
Télécharge BAAI/bge-small-en-v1.5 dans le cache HuggingFace local.
À exécuter UNE SEULE FOIS sur une machine avec accès internet.

Usage :
    python download_model.py
"""
import os
import sys

# ── 1. Charger le token depuis .env si présent ────────────────────────────────
def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        print(f"[OK] .env chargé : {env_path}")
    else:
        print("[INFO] Pas de .env trouvé — on continue avec les variables d'environnement existantes")

_load_env()

HF_TOKEN   = os.environ.get("HF_TOKEN", "")
MODEL_NAME = os.environ.get("RAG_EMBED_MODEL", "BAAI/bge-small-en-v1.5")

print(f"\n=== Téléchargement du modèle d'embedding ===")
print(f"Modèle  : {MODEL_NAME}")
print(f"Token   : {'présent (' + HF_TOKEN[:8] + '...)' if HF_TOKEN else 'ABSENT — risque de rate-limit'}")

# ── 2. Vérifier que huggingface_hub est installé ──────────────────────────────
try:
    from huggingface_hub import snapshot_download, login, whoami
except ImportError:
    print("\n[ERREUR] huggingface_hub non installé.")
    print("Lance : pip install huggingface-hub")
    sys.exit(1)

# ── 3. Vérifier le token ──────────────────────────────────────────────────────
if HF_TOKEN:
    try:
        login(token=HF_TOKEN, add_to_git_credential=False)
        info = whoami()
        print(f"[OK] Token valide — connecté en tant que : {info.get('name', '?')}")
    except Exception as e:
        print(f"[ERREUR] Token invalide ou HuggingFace inaccessible : {e}")
        print("         Génère un nouveau token sur : https://huggingface.co/settings/tokens")
        print("         Puis mets HF_TOKEN=hf_... dans ton .env")
        sys.exit(1)
else:
    print("[AVERTISSEMENT] HF_TOKEN absent — téléchargement possible mais limité en débit")

# ── 4. Télécharger le modèle ──────────────────────────────────────────────────
print(f"\nTéléchargement en cours... (environ 130 Mo, une seule fois)")
try:
    local_path = snapshot_download(
        repo_id        = MODEL_NAME,
        repo_type      = "model",
        token          = HF_TOKEN or None,
        ignore_patterns= ["*.msgpack", "*.h5", "flax_model*", "tf_model*"],
    )
    print(f"\n[OK] Modèle téléchargé dans : {local_path}")
except Exception as e:
    print(f"\n[ERREUR] Téléchargement échoué : {e}")
    sys.exit(1)

# ── 5. Vérification rapide du cache ──────────────────────────────────────────
hf_cache = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
folder   = "models--" + MODEL_NAME.replace("/", "--")
full     = os.path.join(hf_cache, folder)
if os.path.isdir(full):
    size_mb = sum(
        os.path.getsize(os.path.join(r, f))
        for r, _, files in os.walk(full) for f in files
    ) / (1024 * 1024)
    print(f"[OK] Cache vérifié : {full}")
    print(f"     Taille totale : {size_mb:.1f} Mo")
else:
    print(f"[AVERT] Dossier cache introuvable : {full}")

print("\n=== Prêt ! ===")
print("Le modèle est en cache local.")
print("L'application démarrera maintenant sans connexion internet pour le RAG.")
print("Assure-toi que HF_TOKEN est dans ton .env pour le correctif rag_pipeline.py.")
