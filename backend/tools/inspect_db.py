# tools/inspect_db.py
"""
Outil de consultation de la base de données GED.
Lance depuis la racine du projet backend :
    python tools/inspect_db.py

Affiche TOUT le contenu actuel de toutes les tables ACE + mémoire.
Aucun LLM requis. Aucun serveur requis.
"""
import sys, os, sqlite3, json

# Trouver le chemin de la DB
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.abspath(
    os.getenv("GED_DB_PATH", os.path.join(BASE_DIR, "data", "ged.db"))
)

def sep(titre: str) -> None:
    print(f"\n{'━' * 60}")
    print(f"  {titre}")
    print('━' * 60)

def conn():
    if not os.path.exists(DB_PATH):
        print(f"\n[ERREUR] Base de données introuvable : {DB_PATH}")
        print("  → Le fichier ged.db n'existe pas encore.")
        print("  → Lance d'abord : python app.py (même 1 seconde) pour créer les tables.")
        sys.exit(1)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def lister_tables() -> list:
    with conn() as c:
        rows = c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    return [r["name"] for r in rows]

def compter(table: str) -> int:
    try:
        with conn() as c:
            return c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    except Exception:
        return -1

def afficher_learning_store():
    sep("LEARNING STORE (mémoire agents)")
    with conn() as c:
        rows = c.execute(
            "SELECT agent_name, key, value, updated_at FROM learning_store ORDER BY agent_name, key"
        ).fetchall()
    if not rows:
        print("  [vide]")
        return
    print(f"  {len(rows)} entrée(s)\n")
    for r in rows:
        val = r["value"]
        try:
            val = json.dumps(json.loads(val), ensure_ascii=False)[:80]
        except Exception:
            val = str(val)[:80]
        print(f"  [{r['agent_name']}] {r['key']}")
        print(f"    valeur    : {val}")
        print(f"    mis à jour: {r['updated_at']}")

def afficher_context_packs():
    sep("CONTEXT PACKS ACE (mémoire évolutive)")
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM context_packs ORDER BY doc_type, avg_quality DESC"
        ).fetchall()
    if not rows:
        print("  [vide] — Aucun Context Pack encore créé.")
        print("  → Les packs se créent automatiquement après le premier test ACE.")
        return
    print(f"  {len(rows)} pack(s) en base\n")
    for r in rows:
        validated_str = "✓ VALIDÉ" if r["validated"] else "⏳ en attente"
        print(f"  ┌─ [{r['doc_type']}] {validated_str}")
        print(f"  │  pack_id     : {r['pack_id']}")
        print(f"  │  source      : {r['source']}")
        print(f"  │  qualité moy.: {r['avg_quality']}")
        print(f"  │  utilisations: {r['usage_count']}")
        print(f"  │  créé le     : {r['created_at']}")
        print(f"  │  mis à jour  : {r['updated_at']}")
        try:
            content = json.loads(r["content"])
            vocab   = content.get("vocabulaire", [])
            regles  = content.get("regles", [])
            lecons  = content.get("lecons", [])
            pieges  = content.get("pieges_frequents", [])
            print(f"  │  vocabulaire : {', '.join(vocab[:4])}{'...' if len(vocab)>4 else ''}")
            print(f"  │  règles      : {len(regles)} règle(s)")
            if lecons:
                print(f"  │  leçons ({len(lecons)})  :")
                for l in lecons[:5]:
                    u = l.get("compteur_utile", 0)
                    n = l.get("compteur_nuisible", 0)
                    print(f"  │    ↑{u} ↓{n} | {l.get('texte','')[:55]}")
            else:
                print(f"  │  leçons      : [aucune encore]")
            if pieges:
                print(f"  │  pièges ({len(pieges)})  :")
                for p in pieges[:3]:
                    print(f"  │    ✗ {p[:55]}")
        except Exception as e:
            print(f"  │  [erreur parsing content: {e}]")
        print(f"  └{'─' * 50}")

def afficher_reflections():
    sep("RÉFLEXIONS ACE (évaluations post-réponse)")
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM reflections ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
        total = c.execute("SELECT COUNT(*) FROM reflections").fetchone()[0]
        avg   = c.execute("SELECT AVG(quality) FROM reflections").fetchone()[0] or 0.0

    print(f"  Total : {total} réflexion(s) | Qualité moyenne : {avg:.2f}")

    if not rows:
        print("\n  [vide] — Aucune réflexion encore. Se remplit après les tests ACE.")
        return

    print(f"  (20 dernières)\n")
    for r in rows:
        issues = json.loads(r["issues"] or "[]")
        print(f"  • [{r['doc_type']}] doc_id={r['document_id']}")
        print(f"    qualité : {r['quality']:.2f} | {r['created_at']}")
        if r["notes"]:
            print(f"    leçon   : {r['notes'][:70]}")
        if issues:
            print(f"    issues  : {', '.join(issues[:2])}")

def afficher_interactions():
    sep("INTERACTIONS UTILISATEURS")
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM user_interactions ORDER BY created_at DESC LIMIT 15"
        ).fetchall()
        total = c.execute("SELECT COUNT(*) FROM user_interactions").fetchone()[0]
        by_action = c.execute(
            "SELECT action, COUNT(*) as n FROM user_interactions GROUP BY action ORDER BY n DESC"
        ).fetchall()
        by_type = c.execute(
            "SELECT doc_type, COUNT(*) as n FROM user_interactions GROUP BY doc_type ORDER BY n DESC"
        ).fetchall()

    print(f"  Total : {total} interaction(s)")
    if by_action:
        print(f"  Par action : " + " | ".join(f"{r['action']}={r['n']}" for r in by_action))
    if by_type:
        print(f"  Par type   : " + " | ".join(f"{r['doc_type']}={r['n']}" for r in by_type if r['doc_type']))

    if not rows:
        print("\n  [vide]")
        return

    print(f"\n  (15 dernières)\n")
    for r in rows:
        print(f"  • [{r['doc_type'] or '?'}] {r['action']} | doc={r['document_id']}")
        print(f"    result : {r['result'][:60]}")
        print(f"    date   : {r['created_at']}")

def afficher_signatures():
    sep("DOCUMENTS SIGNÉS")
    with conn() as c:
        rows = c.execute(
            "SELECT filename, signer_name, signed_at, pdf_size_bytes FROM signed_documents ORDER BY signed_at DESC LIMIT 10"
        ).fetchall()
    if not rows:
        print("  [vide]")
        return
    for r in rows:
        print(f"  • {r['filename']} | signé par: {r['signer_name']} | {r['signed_at']}")

def afficher_rappels():
    sep("RAPPELS CALENDRIER")
    with conn() as c:
        rows = c.execute(
            "SELECT filename, document_type, reminder_date, notes FROM calendar_reminders ORDER BY reminder_date ASC LIMIT 10"
        ).fetchall()
    if not rows:
        print("  [vide]")
        return
    for r in rows:
        print(f"  • {r['filename']} | {r['document_type']} | rappel: {r['reminder_date']}")
        if r["notes"]:
            print(f"    note: {r['notes'][:60]}")

def resume_global():
    sep("RÉSUMÉ GLOBAL")
    tables = lister_tables()
    print(f"  Tables détectées : {', '.join(tables)}\n")
    comptes = {t: compter(t) for t in tables}
    for table, nb in comptes.items():
        barre = "█" * min(nb, 30) if nb > 0 else "·"
        print(f"  {table:<25} {nb:>5} entrée(s)  {barre}")

def main():
    print(f"\n{'=' * 60}")
    print(f"  INSPECTION BASE DE DONNÉES GED")
    print(f"  Fichier : {DB_PATH}")
    print(f"{'=' * 60}")

    if not os.path.exists(DB_PATH):
        print(f"\n[ERREUR] {DB_PATH} introuvable.")
        print("  Lance d'abord app.py pour initialiser la DB.")
        return

    resume_global()
    afficher_context_packs()
    afficher_reflections()
    afficher_interactions()
    afficher_learning_store()
    afficher_signatures()
    afficher_rappels()

    sep("FIN DE L'INSPECTION")
    print(f"  DB : {DB_PATH}")
    print(f"  Pour lancer les tests ACE : python tests_ace/test_context_store.py")

if __name__ == "__main__":
    main()
