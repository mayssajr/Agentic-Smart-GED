import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("legifrance-server")

# ── Configuration PISTE ───────────────────────────────────────────────────────

PISTE_CLIENT_ID     = os.getenv("PISTE_CLIENT_ID",     "")
PISTE_CLIENT_SECRET = os.getenv("PISTE_CLIENT_SECRET", "")

# Utiliser sandbox en l'absence de credentials prod
_SANDBOX = not (PISTE_CLIENT_ID and PISTE_CLIENT_SECRET)

OAUTH_URL = (
    "https://sandbox-oauth.piste.gouv.fr/api/oauth/token"
    if _SANDBOX else
    "https://oauth.piste.gouv.fr/api/oauth/token"
)
API_BASE = (
    "https://sandbox-api.piste.gouv.fr/dila/legifrance/lf-engine-app"
    if _SANDBOX else
    "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app"
)

# Cache du token OAuth (expire toutes les heures)
_token_cache: dict = {"token": "", "expires_at": 0}


def _get_token() -> str:
    """
    Obtient un token OAuth2 PISTE (Client Credentials).
    Met en cache le token pour éviter des appels répétés.
    """
    now = time.time()
    if _token_cache["token"] and _token_cache["expires_at"] > now + 60:
        return _token_cache["token"]

    if not PISTE_CLIENT_ID or not PISTE_CLIENT_SECRET:
        raise RuntimeError(
            "[LegifranceServer] PISTE_CLIENT_ID ou PISTE_CLIENT_SECRET manquant. "
            "Inscrivez-vous sur https://piste.gouv.fr pour obtenir des credentials."
        )

    resp = requests.post(
        OAUTH_URL,
        data={
            "grant_type":    "client_credentials",
            "client_id":     PISTE_CLIENT_ID,
            "client_secret": PISTE_CLIENT_SECRET,
            "scope":         "openid",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache["token"]      = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 3600)
    return _token_cache["token"]


def _api_post(endpoint: str, payload: dict) -> dict:
    """Appel POST authentifié vers l'API PISTE Légifrance."""
    token = _get_token()
    resp  = requests.post(
        f"{API_BASE}{endpoint}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        },
        json=payload,
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


# ── Outils MCP ────────────────────────────────────────────────────────────────

@mcp.tool()
def search_legifrance(query: str, max_results: int = 5) -> str:
    """
    Recherche textuelle dans tous les fonds Légifrance.
    
    Fonds couverts : lois, codes, JORF, conventions collectives, circulaires.
    
    Paramètres :
      query       : texte à rechercher (ex: "clause de non-concurrence contrat travail")
      max_results : nombre maximum de résultats (1-10)
    
    Retourne JSON : {results: [{title, id, date, nature, url, extrait}]}
    """
    print(f"[LegifranceServer] search_legifrance: '{query}'", file=sys.stderr)
    try:
        payload = {
            "recherche": {
                "champs":     [{"typeChamp": "ALL", "criteres": [{"typeRecherche": "TOUS_LES_MOTS", "valeur": query}], "operateur": "ET"}],
                "filtres":    [],
                "pageNumber": 1,
                "pageSize":   min(max_results, 10),
                "operateur":  "ET",
                "sort":       "PERTINENCE",
                "typePagination": "DEFAUT",
            },
            "fond": "ALL",
        }
        data    = _api_post("/search", payload)
        results = []
        for item in data.get("results", [])[:max_results]:
            titles = item.get("titles", [{}])
            title  = titles[0].get("title", "Sans titre") if titles else "Sans titre"
            cid    = item.get("id", "")
            results.append({
                "title":   title,
                "id":      cid,
                "date":    item.get("dateTexte", ""),
                "nature":  item.get("nature", ""),
                "url":     f"https://www.legifrance.gouv.fr/loda/id/{cid}" if cid else "",
                "extrait": item.get("resume", "")[:300],
            })
        print(f"[LegifranceServer] {len(results)} résultat(s) pour '{query}'", file=sys.stderr)
        return json.dumps({"results": results, "query": query, "total": len(results)},
                          ensure_ascii=False)
    except Exception as e:
        print(f"[LegifranceServer] search error: {e}", file=sys.stderr)
        return json.dumps({"results": [], "query": query, "error": str(e)})


@mcp.tool()
def get_article(article_id: str) -> str:
    """
    Récupère le texte intégral d'un article Légifrance par son identifiant.
    
    L'identifiant peut être :
      - Un CID Légifrance (ex: LEGIARTI000006900846)
      - Un numéro d'article de code (ex: L1234-5 du Code du travail)
    
    Retourne JSON : {id, title, texte, date_debut, date_fin, url}
    """
    print(f"[LegifranceServer] get_article: '{article_id}'", file=sys.stderr)
    try:
        payload = {"id": article_id}
        data    = _api_post("/consult/getArticle", payload)
        article = data.get("article", data)
        return json.dumps({
            "id":         article.get("id", article_id),
            "title":      article.get("titre", ""),
            "texte":      article.get("texte", article.get("texteHtml", ""))[:2000],
            "date_debut": article.get("dateDebut", ""),
            "date_fin":   article.get("dateFin", ""),
            "url":        f"https://www.legifrance.gouv.fr/codes/article_lc/{article_id}",
        }, ensure_ascii=False)
    except Exception as e:
        print(f"[LegifranceServer] get_article error: {e}", file=sys.stderr)
        return json.dumps({"id": article_id, "error": str(e)})


@mcp.tool()
def search_code(code_name: str, query: str, max_results: int = 5) -> str:
    """
    Recherche dans un code juridique spécifique.
    
    Codes disponibles (exemples) :
      LEGITEXT000006070721 → Code civil
      LEGITEXT000006072050 → Code du travail
      LEGITEXT000006069565 → Code de commerce
      LEGITEXT000006071154 → Code pénal
    
    Ou utiliser le nom : "Code du travail", "Code civil", etc.
    
    Retourne JSON : {articles: [{numero, titre, texte, url}]}
    """
    print(f"[LegifranceServer] search_code: '{code_name}' / '{query}'", file=sys.stderr)

    # Mapping noms communs → IDs Légifrance
    CODE_IDS = {
        "code civil":         "LEGITEXT000006070721",
        "code du travail":    "LEGITEXT000006072050",
        "code de commerce":   "LEGITEXT000006069565",
        "code pénal":         "LEGITEXT000006071154",
        "code de procédure":  "LEGITEXT000006071469",
        "code de la sécurité sociale": "LEGITEXT000006073189",
        "code général des impôts":     "LEGITEXT000006069577",
    }
    code_id = CODE_IDS.get(code_name.lower(), code_name)

    try:
        payload = {
            "recherche": {
                "champs": [{"typeChamp": "ALL", "criteres": [{"typeRecherche": "TOUS_LES_MOTS", "valeur": query}], "operateur": "ET"}],
                "filtres": [{"facette": "TEXT_LEGAL_STATUS", "valeur": "VIGUEUR"}],
                "pageNumber": 1,
                "pageSize":   min(max_results, 10),
                "operateur":  "ET",
                "sort":       "PERTINENCE",
                "typePagination": "DEFAUT",
            },
            "fond": "CODE_DATE",
            "textId": code_id,
        }
        data     = _api_post("/search", payload)
        articles = []
        for item in data.get("results", [])[:max_results]:
            titles  = item.get("titles", [{}])
            title   = titles[0].get("title", "") if titles else ""
            cid     = item.get("id", "")
            articles.append({
                "numero": item.get("num", ""),
                "titre":  title,
                "texte":  item.get("resume", "")[:300],
                "url":    f"https://www.legifrance.gouv.fr/codes/article_lc/{cid}",
            })
        return json.dumps({
            "code":     code_name,
            "query":    query,
            "articles": articles,
            "total":    len(articles),
        }, ensure_ascii=False)
    except Exception as e:
        print(f"[LegifranceServer] search_code error: {e}", file=sys.stderr)
        return json.dumps({"code": code_name, "query": query, "articles": [], "error": str(e)})


@mcp.tool()
def search_jurisprudence(query: str, juridiction: str = "", max_results: int = 5) -> str:
    """
    Recherche dans la jurisprudence (Judilibre — Cour de cassation + cours d'appel).
    
    Paramètres :
      query       : termes juridiques (ex: "licenciement pour faute grave")
      juridiction : "CC" (Cour de cassation), "CA" (Cour d'appel), "" (toutes)
      max_results : 1-10
    
    Retourne JSON : {decisions: [{titre, numero, date, juridiction, resume, url}]}
    """
    print(f"[LegifranceServer] search_jurisprudence: '{query}'", file=sys.stderr)
    try:
        payload = {
            "recherche": {
                "champs": [{"typeChamp": "ALL", "criteres": [{"typeRecherche": "TOUS_LES_MOTS", "valeur": query}], "operateur": "ET"}],
                "filtres":        ([{"facette": "JURIDICTION", "valeur": juridiction}] if juridiction else []),
                "pageNumber":     1,
                "pageSize":       min(max_results, 10),
                "operateur":      "ET",
                "sort":           "DATE_DESC",
                "typePagination": "DEFAUT",
            },
            "fond": "JURI",
        }
        data      = _api_post("/search", payload)
        decisions = []
        for item in data.get("results", [])[:max_results]:
            titles = item.get("titles", [{}])
            title  = titles[0].get("title", "Décision") if titles else "Décision"
            cid    = item.get("id", "")
            decisions.append({
                "titre":       title,
                "numero":      item.get("numero", ""),
                "date":        item.get("dateDecision", ""),
                "juridiction": item.get("jurisdiction", ""),
                "resume":      item.get("resume", "")[:300],
                "url":         f"https://www.legifrance.gouv.fr/juri/id/{cid}" if cid else "",
            })
        return json.dumps({
            "query":     query,
            "decisions": decisions,
            "total":     len(decisions),
        }, ensure_ascii=False)
    except Exception as e:
        print(f"[LegifranceServer] search_jurisprudence error: {e}", file=sys.stderr)
        return json.dumps({"query": query, "decisions": [], "error": str(e)})


@mcp.tool()
def check_credentials() -> str:
    """
    Vérifie que les credentials PISTE sont configurés et fonctionnels.
    Utile pour diagnostiquer les problèmes de connexion.
    """
    if not PISTE_CLIENT_ID or not PISTE_CLIENT_SECRET:
        return json.dumps({
            "configured": False,
            "message":    "PISTE_CLIENT_ID et PISTE_CLIENT_SECRET manquants. "
                          "Inscrivez-vous sur https://piste.gouv.fr",
            "sandbox":    _SANDBOX,
        })
    try:
        _get_token()
        return json.dumps({
            "configured": True,
            "message":    "Connexion PISTE OK — token obtenu avec succès.",
            "sandbox":    _SANDBOX,
            "api_base":   API_BASE,
        })
    except Exception as e:
        return json.dumps({
            "configured": False,
            "message":    f"Erreur connexion PISTE : {e}",
            "sandbox":    _SANDBOX,
        })


if __name__ == "__main__":
    try:
        mcp.run(transport="stdio")
    except Exception as e:
        print(f"[LegifranceServer] erreur : {e}", file=sys.stderr)
        sys.exit(1)