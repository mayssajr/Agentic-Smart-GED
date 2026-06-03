# 🧠 Agentic Smart GED

> **Système de Gestion Électronique de Documents Agentique** — Mémoire de fin d'études d'ingénieur 2026  
> Intégrant intelligence artificielle multi-agents, pipeline de recrutement autonome et apprentissage adaptatif continu (ACE).

---

## 📋 Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Structure du projet](#structure-du-projet)
- [Architecture technique](#architecture-technique)
- [Agents IA](#agents-ia)
- [Module ACE — Apprentissage adaptatif](#module-ace--apprentissage-adaptatif)
- [Pipeline de recrutement](#pipeline-de-recrutement)
- [Installation & lancement](#installation--lancement)
- [Variables d'environnement](#variables-denvironnement)
- [Endpoints principaux](#endpoints-principaux)
- [Technologies utilisées](#technologies-utilisées)

---

## Vue d'ensemble

**Agentic Smart GED** est un système de gestion documentaire intelligent qui combine :

- **Classification et résumé automatique** de documents via LLM (Groq / LLaMA 3.3 70B)
- **Pipeline RAG** (Retrieval-Augmented Generation) avec indexation ChromaDB
- **Architecture multi-agents** orchestrée par un pattern ReAct (Thought → Action → Observe)
- **Pipeline de recrutement autonome** avec phases d'autonomie progressives (ACE)
- **Intégrations MCP** : Google Calendar, Gmail, MiniGED local
- **Interface Vue.js** en français avec tableau de bord temps réel

Le système est développé dans le cadre d'un projet de fin d'études d'ingénieur (PFE 2026), appliqué à un cas d'usage réel de recrutement pour un poste d'ingénieur systèmes embarqués chez la société fictive **AeroTech**.

---

## Structure du projet

```
smart-ged/
│
├── backend/                          # Orchestrateur Python / FastAPI
│   ├── app.py                        # Point d'entrée FastAPI, routes HTTP
│   ├── orchestrator.py               # Chef d'orchestre ReAct
│   ├── constants.py                  # Constantes globales (types, seuils)
│   ├── schemas.py                    # Modèles Pydantic (requêtes/réponses)
│   │
│   ├── agents/                       # Agents IA spécialisés
│   │   ├── base_agent.py             # Classe abstraite commune à tous les agents
│   │   ├── classifier_agent.py       # Classification de documents (LLM + fallback)
│   │   ├── summarizer_agent.py       # Génération de résumés
│   │   ├── score_agent.py            # Scoring CV vs offre d'emploi
│   │   ├── task_agent.py             # Création de tâches MiniGED + Calendar
│   │   ├── email_agent.py            # Envoi d'emails (Gmail OAuth)
│   │   ├── assistant_agent.py        # Assistant conversationnel RAG
│   │   ├── ace_decision_agent.py     # Logique de décision par phases ACE
│   │   └── signature_agent.py        # Détection et signature automatique
│   │
│   ├── ace/                          # Module ACE (Adaptive Continuous Evolution)
│   │   ├── ace_router.py             # Endpoints FastAPI ACE + middleware
│   │   ├── generator.py              # Observation des overrides RH
│   │   ├── reflector.py              # Raffinement des insights (LLM)
│   │   ├── curator.py                # Curation et déduplication du playbook
│   │   └── playbook_store.py         # Persistance du playbook JSON
│   │
│   ├── core/
│   │   ├── llm_client.py             # Client Groq (rotation multi-clés, rate limit)
│   │   ├── rag_pipeline.py           # Pipeline RAG (LlamaIndex + ChromaDB)
│   │   ├── miniged_client.py         # Client HTTP MiniGED .NET
│   │   └── mcp_client.py             # Client MCP local
│   │
│   └── memory/
│       ├── short_term.py             # Mémoire de session (résultats courants)
│       └── long_term.py              # Mémoire persistante SQLite (conversations)
│
├── ged-smart-assistant-core/         # Backend .NET / ASP.NET Core (MiniGED)
│   ├── Controllers/
│   │   ├── DocumentController.cs     # CRUD documents
│   │   ├── DocumentFileController.cs # Gestion des fichiers joints
│   │   ├── RecruitmentController.cs  # Gestion des candidatures
│   │   ├── DashboardController.cs    # Statistiques tableau de bord
│   │   └── ChatController.cs         # Proxy conversation IA
│   │
│   ├── Models/
│   │   ├── Document.cs               # Entité document
│   │   ├── DocumentFile.cs           # Fichier joint
│   │   ├── CandidateApplication.cs   # Candidature RH
│   │   └── FileProcessingJob.cs      # Job de traitement asynchrone
│   │
│   └── MCP/
│       ├── MiniGedMcpTools.cs        # Outils MCP exposés (search, retrieve, tasks)
│       └── McpExtensions.cs          # Extensions MCP pour ASP.NET
│
├── ged-smart-assistant-mini-GED/     # Mini-GED .NET (API REST stockage docs)
│
└── ged-smart-assistant-ui/           # Frontend Vue.js
    ├── views/
    │   ├── HomeView.vue              # Tableau de bord temps réel
    │   ├── RecruitmentView.vue       # Pipeline de recrutement (kanban/funnel)
    │   ├── DashboardView.vue         # Statistiques avancées
    │   └── ChatPage.vue              # Interface conversationnelle assistante
    │
    ├── components/
    │   ├── DocumentDetails.vue       # Détail d'un document avec analyse IA
    │   ├── DocumentSummary.vue       # Panneau de synthèse
    │   ├── ScoreValidationBanner.vue # Bannière décision ACE (suggestion RH)
    │   ├── AiTracePanel.vue          # Trace ReAct (Thought/Action/Observe)
    │   ├── SignatureBanner.vue       # Bannière signature électronique
    │   ├── TaskModal.vue             # Création / gestion de tâches
    │   ├── ConversationPanel.vue     # Panel de conversation IA
    │   └── MessageBubble.vue         # Bulle de message
    │
    └── services/
        ├── documentService.js        # Appels API documents
        ├── recruitmentService.js     # Appels API recrutement
        └── assistantApi.js           # Appels API assistante IA
```

---

## Architecture technique

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Vue.js (port 5173)               │
│   HomeView · RecruitmentView · ChatPage · DocumentDetails   │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP REST
┌─────────────────────▼───────────────────────────────────────┐
│              Backend Python FastAPI (port 8000)              │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │               OrchestratorAgent (ReAct)             │   │
│   │  Thought → Action → Observe → ... → Résultat final  │   │
│   └──┬──────────┬──────────┬──────────┬────────────────┘   │
│      │          │          │          │                      │
│  Classifier  Summarizer  Score    TaskAgent                  │
│  Agent       Agent       Agent    EmailAgent                 │
│      │          │          │      AceDecisionAgent           │
│      └──────────┴──────────┴──────────┘                      │
│                      │                                       │
│   ┌──────────────────▼──────────────────────────────────┐   │
│   │  RAG Pipeline : LlamaIndex + ChromaDB + BGE-small   │   │
│   └─────────────────────────────────────────────────────┘   │
│                      │                                       │
│   ┌──────────────────▼──────────────────────────────────┐   │
│   │       ACE Module (Adaptive Continuous Evolution)     │   │
│   │  Generator → Reflector → Curator → playbook.json    │   │
│   └─────────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP REST / MCP
┌─────────────────────▼───────────────────────────────────────┐
│           Backend .NET ASP.NET Core (MiniGED)                │
│   DocumentController · RecruitmentController · MCP Tools    │
│                      │                                       │
│              SQL Server / SQLite                             │
└─────────────────────────────────────────────────────────────┘
                      │
           ┌──────────┴──────────┐
           │                     │
    Google Calendar           Gmail OAuth
    (planification             (envoi emails
     entretiens)                candidats)
```

### Flux d'analyse d'un document

```
Document uploadé → MiniGED .NET
        ↓
  [1] ClassifierAgent    → type de document (CV, Contrat, Facture…)
  [2] SummarizerAgent    → résumé structuré par fichier
  [3] RAG indexation     → chunks dans ChromaDB
  [4] TaskAgent          → tâches MiniGED créées, statut "ATraiter"
  [5] ScoreAgent         → score CV/offre si document RH
  [6] AceDecisionAgent   → phase ACE + suggestion + flag auto_act
  [7] Orchestrateur      → exécution auto si Phase 4 (Calendar + Email)
  [8] Persistance .NET   → AiScore + résumé sauvegardés
  [9] SignatureAgent     → détection et signature si contrat
```

---

## Agents IA

| Agent | Rôle | LLM |
|-------|------|-----|
| `OrchestratorAgent` | Chef d'orchestre — boucle ReAct, coordination | ✓ |
| `ClassifierAgent` | Classification du type de document (LLM + fallback par mots-clés) | ✓ |
| `SummarizerAgent` | Génération de résumés contextualisés par type | ✓ |
| `ScoreAgent` | Scoring CV vs offre d'emploi (0–100), recommandation | ✓ |
| `TaskAgent` | Création de tâches MiniGED, mise à jour statut, Google Calendar | ✓ |
| `EmailAgent` | Envoi d'emails candidats via Gmail OAuth | ✓ |
| `AceDecisionAgent` | Logique de décision par phases ACE (1–4) | ✗ |
| `AssistantAgent` | Assistante conversationnelle avec contexte RAG | ✓ |
| `SignatureAgent` | Détection de besoin de signature et signature automatique | ✓ |

Tous les agents héritent de `BaseAgent` qui expose :
- `_step(type, message)` — trace ReAct (thought / action / observe)
- `_reset()` — réinitialisation de la trace
- Accès unifié au `LLMClient` (Groq, multi-clés, rate-limit)

---

## Module ACE — Apprentissage adaptatif

Le module **ACE (Adaptive Continuous Evolution)** permet au système d'apprendre des décisions RH et de gagner progressivement en autonomie.

### Phases d'autonomie

| Phase | Déclencheur | Comportement |
|-------|-------------|--------------|
| **Phase 1** | 0–9 overrides | ACE observe silencieusement. RH décide tout. |
| **Phase 2** | 10–19 overrides | ACE suggère avec justifications. RH valide. |
| **Phase 3** | 20–29 overrides | ACE recommande fortement (confiance affichée). RH obligatoire. |
| **Phase 4** | 30+ overrides | ACE autonome sur cas clairs (score >85 ou <40, confiance ≥60%). |

### Pipeline ACE

```
Override RH enregistré
        ↓
  Generator  → observe la trajectoire (score IA vs décision RH)
        ↓
  Reflector  → raffine les insights via LLM (1 round)
        ↓
  Curator    → déduplique, priorise, nettoie le playbook
        ↓
  playbook.json → injecté dans ScoreAgent pour affiner les scores futurs
```

### Endpoints ACE

```
POST /ace/override              → Enregistre un override RH (déclenche le pipeline)
GET  /ace/playbook              → Consulte le playbook actuel
GET  /ace/stats                 → Dashboard avant/après ACE
GET  /ace/suggest/{cand_id}     → Suggestion proactive pour un candidat
PATCH /ace/suggest/{id}/outcome → Feedback RH sur une suggestion
GET  /ace/overrides             → Historique des overrides
```

---

## Pipeline de recrutement

Le pipeline traite les candidatures (CV + lettre de motivation) de manière autonome :

```
Statuts candidature :
  NouveauCV → ATraiter → Entretien / ListeAttente / Refus
```

**Interface RH** avec :
- Entonnoir de recrutement visuel
- Bannière `ScoreValidationBanner` affichant la suggestion ACE
- Boutons d'action : Planifier entretien / Refuser / Mettre en liste d'attente
- Création automatique d'événement Google Calendar pour les entretiens
- Envoi automatique d'emails de convocation ou de refus via Gmail

---

## Installation & lancement

### Prérequis

- Python 3.11+
- .NET 8 SDK
- Node.js 18+
- Compte Groq API (clé gratuite sur [console.groq.com](https://console.groq.com))

### 1. Backend Python

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # Configurer les variables (voir ci-dessous)
uvicorn app:app --reload --port 8000
```

### 2. Backend .NET (MiniGED)

```bash
cd ged-smart-assistant-core
dotnet restore
dotnet run
# API disponible sur https://localhost:7xxx
```

### 3. Frontend Vue.js

```bash
cd ged-smart-assistant-ui
npm install
npm run dev
# Interface sur http://localhost:5173
```

---

## Variables d'environnement

Créer un fichier `.env` dans `backend/` :

```env
# LLM — Groq API (rotation multi-clés pour les limites de débit)
GROQ_API_KEY=gsk_...


# Modèle principal
LLM_MODEL=llama-3.3-70b-versatile

# Paramètres rate-limiting
LLM_MAX_RETRIES=3
LLM_MAX_CONCURRENT=2
DAILY_QUOTA_THRESHOLD=429       # Code HTTP signalant quota journalier épuisé

# MiniGED .NET
MINIGED_BASE_URL=https://localhost:7xxx
MINIGED_API_KEY=your_api_key

# Gmail OAuth (pour l'envoi d'emails candidats)
GMAIL_CLIENT_ID=...
GMAIL_CLIENT_SECRET=...
GMAIL_REFRESH_TOKEN=...

# Google Calendar (pour la planification d'entretiens)
GOOGLE_CALENDAR_ID=primary

# RAG — ChromaDB
CHROMA_PERSIST_DIR=./chroma_db

# Whisper STT (transcription audio, optionnel)
OPENAI_API_KEY=...              # Optionnel — fallback cloud Whisper
```

---

## Endpoints principaux

### Orchestrateur (Python FastAPI — port 8000)

```
POST /analyze/{document_id}          → Analyse complète d'un document
POST /summarize/{document_id}        → Résumé uniquement
POST /chat                           → Conversation avec l'assistante IA
POST /sign                           → Signature électronique
GET  /pending-actions                → Actions en attente de confirmation RH
POST /confirm-action                 → Confirmer / annuler une action en attente
POST /schedule-interview             → Planifier un entretien (Calendar + email)
POST /execute-refusal                → Envoyer un email de refus
POST /transcribe                     → Transcription audio Whisper
GET  /health                         → État du système (agents, LLM, RAG, Gmail)
```

### ACE (préfixe `/ace`)
Voir section [Endpoints ACE](#endpoints-ace) ci-dessus.

### MiniGED .NET

```
GET/POST /api/documents              → CRUD documents
GET/POST /api/documents/{id}/files   → Fichiers joints
GET/POST /api/recruitment            → Candidatures RH
GET      /api/dashboard              → Statistiques
```

---

## Technologies utilisées

| Couche | Technologie |
|--------|------------|
| LLM | Groq API — `llama-3.3-70b-versatile` |
| RAG | LlamaIndex · ChromaDB · SentenceTransformers (`BAAI/bge-small-en-v1.5`) |
| Orchestration | Python · FastAPI · Pattern ReAct |
| Backend GED | ASP.NET Core 8 · C# · Entity Framework |
| Frontend | Vue.js 3 · Composition API |
| MCP | Protocol MCP local · Google Calendar MCP · Gmail MCP |
| Mémoire | SQLite (long terme) · In-process (court terme) |
| STT | faster-whisper / openai-whisper (optionnel) |
| Auth | Gmail OAuth 2.0 |
| Diagrammes | Mermaid |

---

## Auteur

**Eng. MAYSSA JARRAY** — Projet de fin d'études d'ingénieur 2026  
*Système GED agentique avec apprentissage adaptatif et pipeline de recrutement autonome*

---


