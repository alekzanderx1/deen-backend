from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional
import json

from db.session import get_db
from db.repositories.memory_profile_repository import MemoryProfileRepository
from db.repositories.memory_event_repository import MemoryEventRepository
from db.repositories.memory_consolidation_repository import MemoryConsolidationRepository
from agents.models.user_memory_models import UserMemoryProfile, MemoryEvent

router = APIRouter(prefix="/admin/memory", tags=["Admin-Memory"])

profile_repo = MemoryProfileRepository()
event_repo = MemoryEventRepository()
consolidation_repo = MemoryConsolidationRepository()


def _serialize_notes(notes):
    return [
        {
            "id": n.get("id"),
            "content": n.get("content"),
            "note_type": n.get("note_type"),
            "category": n.get("category"),
            "confidence": n.get("confidence"),
            "created_at": n.get("created_at"),
            "tags": n.get("tags"),
            "evidence": n.get("evidence"),
        }
        for n in notes or []
    ]


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    """
    Lightweight dev dashboard for inspecting memory data by user.
    Uses HTMX-style fetches against JSON endpoints below.
    """
    html = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Memory Admin</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; background: #f6f8fb; color: #1b1f23; }
    .container { max-width: 1200px; margin: 0 auto; }
    .card { background: #fff; border: 1px solid #e1e4e8; border-radius: 8px; padding: 16px; margin-bottom: 16px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }
    .label { font-size: 12px; text-transform: uppercase; color: #586069; letter-spacing: 0.02em; }
    .value { font-size: 20px; font-weight: 600; color: #111; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 8px; border-bottom: 1px solid #e1e4e8; text-align: left; }
    th { background: #f0f2f5; font-size: 13px; }
    .pill { display: inline-block; padding: 2px 8px; border-radius: 999px; background: #e6f3ff; color: #0366d6; font-size: 12px; }
    .pill.warn { background: #fff5e6; color: #b26a00; }
    .pill.error { background: #ffe6e6; color: #b20000; }
    input[type=text] { padding: 8px; width: 220px; border: 1px solid #d1d5da; border-radius: 4px; }
    button { padding: 8px 12px; border: none; background: #0366d6; color: #fff; border-radius: 4px; cursor: pointer; }
    button:hover { background: #0256b7; }
    .small { font-size: 12px; color: #586069; }
    pre { white-space: pre-wrap; word-break: break-word; background: #f6f8fa; padding: 8px; border-radius: 6px; }
    .tab-btn { flex: 1; padding: 12px; background: #fff; border: none; border-right: 1px solid #e1e4e8; cursor: pointer; font-weight: 600; color: #000; }
    .tab-btn:last-child { border-right: none; }
    .tab-btn:hover { background: #f6f8fb; }
    .tab-content { min-height: 200px; }
  </style>
</head>
<body>
  <div class="container">
    <h2>Memory Admin Dashboard</h2>
    <div style="margin-bottom: 12px;">
      <input id="userIdInput" type="text" placeholder="Enter user_id" />
      <button onclick="loadAll()">Load</button>
      <span class="small" id="status"></span>
    </div>

    <div id="summary"></div>

    <div class="card" style="padding: 0;">
      <div style="display:flex; border-bottom:1px solid #e1e4e8;">
        <button class="tab-btn" data-tab="notes" onclick="showTab('notes')">Notes</button>
        <button class="tab-btn" data-tab="events" onclick="showTab('events')">Events</button>
        <button class="tab-btn" data-tab="consolidations" onclick="showTab('consolidations')">Consolidations</button>
      </div>
      <div id="tab-notes" class="tab-content"></div>
      <div id="tab-events" class="tab-content" style="display:none;"></div>
      <div id="tab-consolidations" class="tab-content" style="display:none;"></div>
    </div>
  </div>

<script>
let activeTab = 'notes';

function showTab(name) {
  activeTab = name;
  document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.style.background = '#fff';
    btn.style.border = 'none';
    btn.style.borderBottom = '1px solid #e1e4e8';
  });
  const btn = document.querySelector(`.tab-btn[data-tab="${name}"]`);
  if (btn) {
    btn.style.background = '#f6f8fb';
    btn.style.borderBottom = '2px solid #0366d6';
  }
  const pane = document.getElementById(`tab-${name}`);
  if (pane) pane.style.display = 'block';
}

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function setStatus(msg) {
  document.getElementById('status').textContent = msg;
}

function fmtDate(value) {
  if (!value) return '';
  const d = new Date(value);
  return isNaN(d) ? value : d.toLocaleString();
}

async function loadSummary(userId) {
  const data = await fetchJson(`/admin/memory/${userId}/profile`);
  const cat = data.note_counts || {};
  document.getElementById('summary').innerHTML = `
    <div class="card">
      <div class="grid">
        <div><div class="label">User</div><div class="value">${data.user_id}</div></div>
        <div><div class="label">Total Additions</div><div class="value">${data.total_notes}</div></div>
        <div><div class="label">Memory Version</div><div class="value">${data.memory_version}</div></div>
        <div><div class="label">Last Update</div><div class="value">${fmtDate(data.last_significant_update) || '—'}</div></div>
      </div>
      <div style="margin-top:12px;" class="grid">
        ${Object.keys(cat).map(k => `
          <div>
            <div class="label">${k}</div>
            <div class="value">${cat[k]}</div>
          </div>
        `).join('')}
      </div>
    </div>`;
}

function renderNotesSection(groups) {
  const descriptions = {
    learning_notes: "What the user has studied, learned, or is currently learning (progress and current focus).",
    knowledge_notes: "What the user knows well vs. where they have knowledge gaps (mastery and struggles).",
    interest_notes: "Topics, themes, or aspects of Islam that particularly engage the user (curiosity hotspots).",
    behavior_notes: "Learning patterns, interaction styles, and behaviors (how they study and interact).",
    preference_notes: "User preferences for learning style, content depth, language, and format (how they like material presented)."
  };
  const sections = Object.entries(groups).map(([name, notes]) => {
    const rows = notes.map(n => `
      <tr>
        <td>${n.content || ''}</td>
        <td><span class="pill">${n.category || ''}</span></td>
        <td>${n.confidence ?? ''}</td>
        <td>${(n.tags || []).join(', ')}</td>
        <td class="small">${fmtDate(n.created_at) || ''}</td>
      </tr>
    `).join('');
    return `
      <div class="card">
        <h4>${name} (${notes.length})</h4>
        <div class="small" style="margin-bottom:8px;">${descriptions[name] || ''}</div>
        <table>
          <thead><tr><th>Content</th><th>Category</th><th>Conf.</th><th>Tags</th><th>Created</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="5">No notes</td></tr>'}</tbody>
        </table>
      </div>
    `;
  }).join('');
  const container = document.getElementById('tab-notes');
  if (container) {
    container.innerHTML = `<div style="padding:16px;">${sections}</div>`;
  }
}

async function loadNotes(userId) {
  const data = await fetchJson(`/admin/memory/${userId}/notes`);
  renderNotesSection(data);
}

async function loadEvents(userId) {
  const data = await fetchJson(`/admin/memory/${userId}/events?limit=50`);
  const rows = data.map(e => `
    <tr>
      <td>${e.event_type}</td>
      <td><span class="pill ${e.processing_status === 'failed' ? 'error' : e.processing_status === 'pending' ? 'warn' : ''}">${e.processing_status}</span></td>
      <td>${fmtDate(e.processed_at) || ''}</td>
      <td>${e.notes_added || 0}</td>
      <td class="small">${e.reasoning || ''}</td>
    </tr>
  `).join('');
  document.getElementById('tab-events').innerHTML = `
    <div style="padding:16px;">
      <h4>Recent Events</h4>
      <table>
        <thead><tr><th>Type</th><th>Status</th><th>Processed At</th><th>Notes Added</th><th>Reasoning</th></tr></thead>
        <tbody>${rows || '<tr><td colspan="5">No events</td></tr>'}</tbody>
      </table>
    </div>
  `;
}

async function loadConsolidations(userId) {
  const data = await fetchJson(`/admin/memory/${userId}/consolidations?limit=20`);
  const rows = data.map(c => `
    <tr>
      <td>${fmtDate(c.created_at)}</td>
      <td>${c.consolidation_type}</td>
      <td>${c.notes_before} → ${c.notes_after}</td>
      <td>${c.notes_removed}</td>
      <td class="small">${c.reasoning || ''}</td>
    </tr>
  `).join('');
  document.getElementById('tab-consolidations').innerHTML = `
    <div style="padding:16px;">
      <h4>Consolidations</h4>
      <table>
        <thead><tr><th>Date</th><th>Type</th><th>Notes (before→after)</th><th>Removed</th><th>Reasoning</th></tr></thead>
        <tbody>${rows || '<tr><td colspan="5">No consolidations</td></tr>'}</tbody>
      </table>
    </div>
  `;
}

async function loadAll() {
  const userId = document.getElementById('userIdInput').value.trim();
  if (!userId) { setStatus('Enter a user_id'); return; }
  setStatus('Loading...');
  try {
    await loadSummary(userId);
    await loadNotes(userId);
    await loadEvents(userId);
    await loadConsolidations(userId);
    setStatus('Loaded');
    showTab(activeTab);
  } catch (e) {
    console.error(e);
    setStatus('Error: ' + e.message);
  }
}
</script>
</body>
</html>
    """
    return HTMLResponse(content=html)


@router.get("/{user_id}/profile")
def profile(user_id: str, db: Session = Depends(get_db)):
    profile: Optional[UserMemoryProfile] = profile_repo.get_by_user_id(db, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    note_counts = {
        "learning_notes": len(profile.learning_notes or []),
        "knowledge_notes": len(profile.knowledge_notes or []),
        "interest_notes": len(profile.interest_notes or []),
        "behavior_notes": len(profile.behavior_notes or []),
        "preference_notes": len(profile.preference_notes or []),
    }

    def recent(notes):
        return sorted(notes or [], key=lambda x: x.get("created_at", ""), reverse=True)[:3]

    return {
        "user_id": profile.user_id,
        "memory_version": profile.memory_version,
        "total_interactions": profile.total_interactions,
        "total_notes": sum(note_counts.values()),
        "last_significant_update": profile.last_significant_update.isoformat() if profile.last_significant_update else None,
        "note_counts": note_counts,
        "recent": {
            "learning": _serialize_notes(recent(profile.learning_notes)),
            "knowledge": _serialize_notes(recent(profile.knowledge_notes)),
            "interest": _serialize_notes(recent(profile.interest_notes)),
            "behavior": _serialize_notes(recent(profile.behavior_notes)),
            "preference": _serialize_notes(recent(profile.preference_notes)),
        },
    }


@router.get("/{user_id}/notes")
def notes(user_id: str, db: Session = Depends(get_db)):
    profile: Optional[UserMemoryProfile] = profile_repo.get_by_user_id(db, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "learning_notes": _serialize_notes(profile.learning_notes or []),
        "knowledge_notes": _serialize_notes(profile.knowledge_notes or []),
        "interest_notes": _serialize_notes(profile.interest_notes or []),
        "behavior_notes": _serialize_notes(profile.behavior_notes or []),
        "preference_notes": _serialize_notes(profile.preference_notes or []),
    }


@router.get("/{user_id}/events")
def events(user_id: str, limit: int = 50, db: Session = Depends(get_db)):
    profile: Optional[UserMemoryProfile] = profile_repo.get_by_user_id(db, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    events = (
        db.query(MemoryEvent)
        .filter(MemoryEvent.user_memory_profile_id == profile.id)
        .order_by(MemoryEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "processing_status": e.processing_status,
            "processed_at": e.processed_at.isoformat() if e.processed_at else None,
            "reasoning": e.processing_reasoning,
            "notes_added": len(e.notes_added or []),
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]


@router.get("/{user_id}/consolidations")
def consolidations(user_id: str, limit: int = 20, db: Session = Depends(get_db)):
    profile: Optional[UserMemoryProfile] = profile_repo.get_by_user_id(db, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    consolidations = consolidation_repo.list_recent(db, profile.id, limit)
    return [
        {
            "id": c.id,
            "consolidation_type": c.consolidation_type,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "notes_before": c.notes_before_count,
            "notes_after": c.notes_after_count,
            "notes_removed": (c.notes_before_count - c.notes_after_count) if c.notes_before_count and c.notes_after_count else None,
            "reasoning": c.consolidation_reasoning,
        }
        for c in consolidations
    ]
