import os
import sys

POSSIBLE_CRED_PATHS = [
    os.getenv("GOOGLE_CREDENTIALS_PATH", ""),
    "./credentials.json",
    "../credentials.json",
    os.path.join(os.path.dirname(__file__), "credentials.json"),
    os.path.join(os.path.dirname(__file__), "..", "credentials.json"),
]

CREDENTIALS_PATH = next(
    (p for p in POSSIBLE_CRED_PATHS if p and os.path.exists(p)),
    None
)

TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH", "./token.json")
# Si token.json doit être à la racine du backend
if not os.path.isabs(TOKEN_PATH):
    TOKEN_PATH = os.path.join(os.path.dirname(__file__), TOKEN_PATH.lstrip("./"))

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def main():
    print("=" * 60)
    print("  Configuration Google Calendar — Authentification OAuth")
    print("=" * 60)

    # ── Vérifier les dépendances ────────────────────────────────────────
    try:
        from google.oauth2.credentials      import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow      import InstalledAppFlow
        from googleapiclient.discovery      import build
        print("✓ Dépendances Google installées")
    except ImportError:
        print("✗ Dépendances manquantes. Exécutez :")
        print("  pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        sys.exit(1)

    # ── Vérifier credentials.json ───────────────────────────────────────
    if not CREDENTIALS_PATH:
        print("\n✗ Fichier credentials.json introuvable.")
        print("  Téléchargez-le depuis Google Cloud Console :")
        print("  APIs & Services → Credentials → OAuth 2.0 Client IDs → Download JSON")
        print(f"  Puis placez-le ici : {os.path.abspath('./credentials.json')}")
        sys.exit(1)

    print(f"✓ credentials.json trouvé : {os.path.abspath(CREDENTIALS_PATH)}")

    # ── Vérifier token.json existant ────────────────────────────────────
    creds = None
    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
            if creds and creds.valid:
                print(f"✓ token.json déjà valide : {TOKEN_PATH}")
                print("  Rien à faire — l'authentification est déjà active.")
                _test_connection(build, creds)
                return
            elif creds and creds.expired and creds.refresh_token:
                print("  Token expiré — rafraîchissement en cours...")
                creds.refresh(Request())
                _save_token(creds, TOKEN_PATH)
                print(f"✓ Token rafraîchi : {TOKEN_PATH}")
                _test_connection(build, creds)
                return
        except Exception as e:
            print(f"  Token existant invalide ({e}) — nouvel token requis")
            creds = None

    # ── Lancement du flux OAuth (ouvre le navigateur) ───────────────────
    print("\n Le navigateur va s'ouvrir pour l'autorisation Google...")
    print("   Connectez-vous et cliquez 'Autoriser'.\n")

    try:
        flow  = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
        creds = flow.run_local_server(
            port=0,
            prompt="consent",
            authorization_prompt_message="En attente d'autorisation dans le navigateur...",
            success_message="✓ Autorisation accordée. Vous pouvez fermer cet onglet.",
        )
    except Exception as e:
        print(f"\n✗ Erreur lors de l'authentification : {e}")
        print("\n  Si le navigateur ne s'ouvre pas automatiquement :")
        print("  Vérifiez que vous n'êtes pas en SSH sans interface graphique.")
        sys.exit(1)

    # ── Sauvegarder le token ─────────────────────────────────────────────
    _save_token(creds, TOKEN_PATH)
    print(f"\n✓ token.json généré : {os.path.abspath(TOKEN_PATH)}")

    # ── Test de connexion ────────────────────────────────────────────────
    _test_connection(build, creds)

    print("\n" + "=" * 60)
    print("  Configuration terminée !")
    print("  Vous pouvez maintenant lancer l'application normalement.")
    print("  Les agents MCP utiliseront token.json automatiquement.")
    print("=" * 60)


def _save_token(creds, path: str):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        f.write(creds.to_json())


def _test_connection(build, creds):
    """Teste la connexion en listant les calendriers disponibles."""
    print("\n  Test de connexion Google Calendar...")
    try:
        service   = build("calendar", "v3", credentials=creds)
        calendars = service.calendarList().list().execute()
        items     = calendars.get("items", [])
        print(f"  ✓ Connexion réussie — {len(items)} calendrier(s) accessible(s) :")
        for cal in items[:5]:
            primary = " ← calendrier principal" if cal.get("primary") else ""
            print(f"    • {cal.get('summary', '?')} (ID: {cal.get('id', '?')}){primary}")
    except Exception as e:
        print(f"  ✗ Test échoué : {e}")


if __name__ == "__main__":
    # Charger .env si présent
    try:
        from dotenv import load_dotenv
        # Chercher .env dans le dossier courant et le parent
        for env_path in [".env", "../.env"]:
            if os.path.exists(env_path):
                load_dotenv(env_path)
                print(f"  .env chargé depuis : {os.path.abspath(env_path)}")
                break
    except ImportError:
        pass

    main()
