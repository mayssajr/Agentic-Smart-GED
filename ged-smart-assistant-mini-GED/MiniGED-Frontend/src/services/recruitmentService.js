const MINIGED_API = 'http://localhost:5092'
const AI_BACKEND  = import.meta.env.VITE_AI_BACKEND_URL || 'http://localhost:8000'

// ─────────────────────────────────────────────────────────────────────────────
// getCandidateByDocument
// ─────────────────────────────────────────────────────────────────────────────
export async function getCandidateByDocument(documentId, token) {
  try {
    const res = await fetch(
      `${MINIGED_API}/api/recruitment/applications?pageSize=100`,
      {
        headers: {
          Authorization:  `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      }
    )
    if (!res.ok) return null
    const data = await res.json()
    return data.candidates?.find(
      c => String(c.documentId) === String(documentId)
    ) || null
  } catch {
    return null
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// updateCandidateStatus
//
// Utilisé pour : ListeAttente, Accepte, Refuse post-entretien
// NON utilisé pour Entretien ni Refuse simple (scheduleInterview /
// sendSimpleRefusal gèrent tout en une seule fois).
// ─────────────────────────────────────────────────────────────────────────────
export async function updateCandidateStatus(
  candidateId,
  newStatus,
  token,
  rhNotes   = [],
  notesText = ''
) {
  const res = await fetch(
    `${MINIGED_API}/api/recruitment/application/${candidateId}/status`,
    {
      method:  'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization:  `Bearer ${token}`,
      },
      body: JSON.stringify({
        status:  newStatus,
        notes:   notesText,
        rhNotes: rhNotes,
      }),
    }
  )
  if (!res.ok) throw new Error(`Erreur ${res.status}`)
  return await res.json()
}

// ─────────────────────────────────────────────────────────────────────────────
// scheduleInterview
//
// Gère en UNE SEULE fois :
//   1. Statut → Entretien   (Python → MCP → .NET)
//   2. Notes RH sauvegardées (Python → MCP → .NET, une seule écriture)
//   3. ACE notifié avec rh_notes structurés
//   4. Google Calendar créé
//   5. Email invitation envoyé
//
// Ne jamais appeler updateCandidateStatus avant ou après pour Entretien
// → évite la double écriture des notes dans candidate.Notes
// ─────────────────────────────────────────────────────────────────────────────
export async function scheduleInterview(
  candidateId,
  documentId,
  token,
  rhNotes   = [],
  notesText = ''
) {
  const res = await fetch(
    `${AI_BACKEND}/recruitment/schedule-interview`,
    {
      method:  'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization:  `Bearer ${token}`,
      },
      body: JSON.stringify({
        candidate_id: candidateId,
        document_id:  String(documentId),
        notes:        notesText,
        rh_notes:     rhNotes,
      }),
    }
  )
  if (!res.ok) throw new Error(`Erreur ${res.status}`)
  return await res.json()
}

// ─────────────────────────────────────────────────────────────────────────────
// sendSimpleRefusal
//
// Gère en UNE SEULE fois :
//   1. Statut → Refuse      (Python → MCP → .NET)
//   2. Notes RH sauvegardées (Python → MCP → .NET, une seule écriture)
//   3. ACE notifié avec rh_notes structurés
//   4. Email "candidature non retenue" envoyé
//
// Ne jamais appeler updateCandidateStatus avant ou après pour Refuse simple
// ─────────────────────────────────────────────────────────────────────────────
export async function sendSimpleRefusal(
  candidateId,
  documentId,
  token,
  rhNotes   = [],
  notesText = ''
) {
  const res = await fetch(
    `${AI_BACKEND}/recruitment/simple-refusal`,
    {
      method:  'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization:  `Bearer ${token}`,
      },
      body: JSON.stringify({
        candidate_id: candidateId,
        document_id:  String(documentId),
        notes:        notesText,
        rh_notes:     rhNotes,
      }),
    }
  )
  if (!res.ok) throw new Error(`Erreur ${res.status}`)
  return await res.json()
}

// ─────────────────────────────────────────────────────────────────────────────
// sendRecruitmentDecision  (Accepte ou Refuse post-entretien réel)
// ─────────────────────────────────────────────────────────────────────────────
export async function sendRecruitmentDecision(candidateId, documentId, decision, token) {
  const res = await fetch(
    `${AI_BACKEND}/recruitment/decision`,
    {
      method:  'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization:  `Bearer ${token}`,
      },
      body: JSON.stringify({
        candidate_id: candidateId,
        document_id:  String(documentId),
        decision,
      }),
    }
  )
  if (!res.ok) throw new Error(`Erreur ${res.status}`)
  return await res.json()
}

// ─────────────────────────────────────────────────────────────────────────────
// getCandidateStatuses  (pour DocumentsList.vue — map documentId → status)
// ─────────────────────────────────────────────────────────────────────────────
export async function getCandidateStatuses(token) {
  try {
    const res = await fetch(
      `${MINIGED_API}/api/recruitment/applications?pageSize=100`,
      { headers: { Authorization: `Bearer ${token}` } }
    )
    if (!res.ok) return {}
    const data = await res.json()
    const map  = {}
    data.candidates?.forEach(c => {
      if (c.documentId) map[c.documentId] = c.status
    })
    return map
  } catch {
    return {}
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// getCandidates
// ─────────────────────────────────────────────────────────────────────────────
export async function getCandidates(token, pageSize = 200) {
  try {
    const res = await fetch(
      `${MINIGED_API}/api/recruitment/applications?pageSize=${pageSize}`,
      { headers: { Authorization: `Bearer ${token}` } }
    )
    if (!res.ok) return []
    const data = await res.json()
    return data.candidates ?? data ?? []
  } catch {
    return []
  }
}