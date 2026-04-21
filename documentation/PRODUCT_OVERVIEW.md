# Deen — AI-Powered Shia Islamic Education Platform

## What is Deen?

Deen is an AI-powered Islamic education platform purpose-built for Twelver Shia Muslims. It combines a curated library of structured lessons, hadith, Quranic tafsir, and Islamic jurisprudence (fiqh) with a conversational AI assistant grounded in authenticated Islamic sources. Every answer the AI gives is traceable back to real hadith, Quranic verses, or Ayatollah Sistani's published rulings — the system refuses to speculate or fabricate religious guidance.

The platform is built for learners at every stage, from beginners asking "What is Imamate?" to advanced students diving into nuanced fiqh rulings and Quranic exegesis.

---

## Core Mission

> Ground every Islamic answer in verified, attributed sources — never hallucinate, never issue a fatwa, always educate.

Deen exists to make authentic Shia Islamic scholarship accessible to anyone, anywhere, in any language. It bridges the gap between traditional Islamic learning and the modern learner's expectation of instant, personalized, and reliable knowledge.

---

## Key Features

### 1. Agentic AI Chat Assistant

The heart of Deen is a conversational AI assistant powered by a **LangGraph agentic pipeline**. Unlike simple chatbots, this agent:

- **Autonomously decides** which knowledge sources to consult based on the question.
- **Searches multiple knowledge bases** in a single turn — Shia hadith, Sunni hadith (for comparative context), and Quranic tafsir.
- **Enhances and rewrites** queries before retrieval to maximize search accuracy.
- **Classifies intent** before answering — determining whether the question is Islamic in nature, and whether it is asking for a legal (fiqh) ruling.
- **Streams responses in real time** using Server-Sent Events (SSE), so users see the answer as it is generated.
- **Maintains conversation memory** across sessions using Redis-backed history, enabling natural follow-up questions without losing context.
- **Refuses off-topic questions** gracefully — if a question falls outside Islamic education, the AI politely declines rather than generating irrelevant content.

**What users can ask:**
- Questions about theology, belief, and Shia doctrine (Tawhid, Imamate, prophethood)
- Life and legacy of the 14 Infallibles (the Prophet, Fatima al-Zahra, and the 12 Imams)
- Hadith and narrations from Shia and Sunni collections
- Quranic verses and scholarly Tafsir commentary
- Islamic history, ethics, and spirituality
- Daily practice: prayer, fasting, Zakat, Hajj, purity, and more

---

### 2. Fiqh (Islamic Jurisprudence) Engine

Deen includes a specialized **Fiqh RAG (Retrieval-Augmented Generation)** pipeline grounded exclusively in **Ayatollah Sistani's "Islamic Laws" (4th edition)**. This is a critical safety feature:

- The AI **detects fiqh questions** (e.g., "Is it permissible to...?", "What is the ruling on...?") and routes them through a dedicated retrieval pipeline.
- All rulings are sourced from Sistani's published book — the AI **never derives its own conclusions**.
- Responses always include disclaimers clarifying these are informational summaries, not personal fatwas.
- If sufficient evidence cannot be found, the system **refuses to answer** rather than speculating.
- Up to **3 iterative retrieval rounds** are performed per query, ensuring comprehensive coverage of relevant rulings.

---

### 3. Dual Knowledge Base: Shia + Sunni + Quran

Deen's retrieval system searches across **three separate vector databases**:

| Knowledge Base | Contents | Search Method |
|---|---|---|
| Shia hadith index | Hadith and narrations from Twelver Shia collections | Hybrid (dense + sparse) |
| Sunni hadith index | Hadith from major Sunni collections | Hybrid (dense + sparse) |
| Quran & Tafsir index | Quranic verses + scholarly Tafsir commentary | Dense vector search |

- **Hybrid search** (combining semantic and keyword search) ensures the most relevant results are surfaced.
- A **reranking layer** re-scores and merges results from dense and sparse retrieval for optimal relevance.
- Each retrieved document includes full metadata: book name, chapter, hadith number, author, volume, and source.
- Arabic and English text are both preserved for hadith results.

---

### 4. Hikam Tree Lessons

Deen's structured learning content is organized into **Hikam Trees** — curated lesson collections inspired by the Hikam (wisdom aphorisms) tradition in Islamic scholarship. Key capabilities:

- **Lesson trees** group thematically related lessons (e.g., lessons on justice, on the Imamate, on Quranic ethics).
- Each lesson tree has a title, summary, topic tags, and a skill level rating (1–10), allowing learners to find content appropriate for their level.
- **Lessons** contain structured content pages with rich text, estimated reading times, topic tags, and ordered page sequences.
- Lessons are authored and published on the platform, with status tracking, language codes, and timestamps.

---

### 5. Hikmah Elaboration — AI Deep Dives on Lesson Content

While reading a lesson, users can **select any passage** and request an AI elaboration. The system:

- Takes the **selected text** and its full lesson context.
- Generates a scholarly, streaming explanation drawing on the Islamic knowledge base.
- Optionally integrates with the user's **memory profile** to tailor the explanation to what the user already knows.

This creates an interactive reading experience — learners are never stuck on a difficult concept.

---

### 6. Adaptive Personalized Primers

Before starting a lesson, Deen prepares the learner with a **primer** — a brief set of prerequisite concepts and a glossary. There are two types:

**Baseline Primer:**
- A set of 2–3 prerequisite bullet points shown to all users.
- A mini-glossary of key terms introduced in the lesson.
- Authored and updated by the content team.

**Personalized "For You" Primer:**
- Dynamically generated by the AI based on the user's **memory profile** (what they've studied before, their knowledge gaps, their interests).
- Uses **embedding-based filtering** to match lesson prerequisites against the user's learning history.
- Streamed in real time as the AI generates it.
- Cached per user per lesson to avoid regeneration costs; cache can be force-refreshed.
- Falls back gracefully if no personalization data is available.

---

### 7. Persistent User Memory System

Deen builds a **long-term memory profile** for each user that persists across sessions. This is not just chat history — it is a structured understanding of who the learner is:

| Memory Category | What it tracks |
|---|---|
| Learning notes | What the user has studied, their progress, current focus |
| Knowledge notes | What the user knows well vs. where they have gaps |
| Interest notes | Topics and themes that particularly engage the user |
| Behavior notes | Learning patterns and interaction styles |
| Preference notes | Preferred content depth, language, and format |

- Memory notes are extracted automatically from conversations and elaboration sessions.
- Notes are **deduplicated and consolidated** periodically to avoid redundancy and keep the profile clean.
- The memory system powers personalized primers, adaptive elaborations, and future personalization features.
- An admin dashboard provides visibility into every user's memory profile, notes, events, and consolidations.

---

### 8. Semantic Reference Lookup

A standalone **reference endpoint** allows direct semantic search across the hadith knowledge base:

- Accepts a free-text query and returns the most relevant hadith references.
- Filterable by sect (`shia`, `sunni`, or `both`).
- Configurable result count (1–50 references).
- Returns full hadith metadata: book, chapter, hadith number, author, volume, Arabic and English text.
- Useful for scholars, students, and developers building on top of Deen's knowledge base.

---

### 9. Quiz System

Deen includes an integrated **quiz system** for Hikmah lesson pages:

- Each lesson page can have one or more **multiple-choice quiz questions**.
- Questions are authored with a question body, multiple choice options, and a designated correct answer.
- Users submit answers asynchronously (fire-and-forget) — the system acknowledges receipt immediately and processes in the background.
- The quiz system tracks attempts, enabling future progress analytics and adaptive learning paths.
- Full admin API for creating, reading, updating, and deleting quiz questions per lesson page.

---

### 10. Multilingual Support

Deen is built for a global Muslim community:

- The AI assistant accepts queries in **any language**.
- A **translation pipeline** detects non-English input, translates it to English for retrieval, and then translates the response back to the user's language.
- The `language` parameter on every chat request allows explicit language targeting.
- Arabic text is preserved in hadith results alongside English translations.

---

### 11. Saved Chat History

Authenticated users can access their full conversation history:

- All chat sessions and messages are persisted to a PostgreSQL database.
- Users can list all their past chat sessions with pagination.
- Users can retrieve the full message history of any saved session.
- Sessions are scoped per user — users can only access their own history.

---

### 12. Account Management

Deen supports authenticated user accounts:

- User registration with email, password (hashed), display name, and avatar.
- Role-based access (user/admin) for content authoring and admin features.
- JWT-based authentication via AWS Cognito, with JWKS validation at startup.
- Session clearing — users can reset a chat session's memory at any time.

---

## AI Safety and Religious Integrity

Religious accuracy is a core design constraint, not an afterthought:

- **No speculative answers**: The AI cites sources or refuses — it never invents Islamic rulings.
- **Fiqh gate**: Jurisprudence questions are isolated to a dedicated pipeline grounded in a single authoritative source (Sistani's rulings). The system explicitly refuses to answer rather than risk issuing an unauthorized verdict.
- **Non-Islamic query rejection**: Off-topic questions (weather, recipes, sports) are gracefully declined with a clear explanation.
- **Always includes disclaimers**: Fiqh responses remind users these are informational summaries — not personal fatwas — and encourage consulting a qualified scholar for their specific situation.
- **Source attribution**: Every AI-generated answer surfaces the hadith and Quranic sources that informed it, allowing users to verify and deepen their study.

---

## Technology

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.11) |
| AI Orchestration | LangGraph (agentic graph) |
| LLMs | OpenAI GPT-4.1 (primary), GPT-4o-mini (lightweight tasks) |
| Vector Search | Pinecone (dense + sparse indices) |
| Embeddings | HuggingFace `all-mpnet-base-v2` (dense), TF-IDF (sparse) |
| Conversation Memory | Redis (TTL-capped message history) |
| Long-term Memory | PostgreSQL (structured user memory profiles) |
| Database | PostgreSQL + SQLAlchemy |
| Auth | AWS Cognito (JWT/JWKS) |
| Streaming | Server-Sent Events (SSE) |
| Infrastructure | Docker + Caddy reverse proxy |

---

## Who is Deen For?

- **Curious Muslims** who want reliable, source-grounded answers to Islamic questions without sifting through unreliable internet content.
- **Students of Islamic knowledge** who want a structured learning path with interactive AI support.
- **Converts and new Muslims** who need patient, contextual explanations of Shia beliefs and practices.
- **Diaspora communities** who want to engage with their faith in English while retaining access to original Arabic sources.
- **Scholars and researchers** who want fast, semantic access to a curated Islamic knowledge base.

---

## Summary of Capabilities

| Capability | Description |
|---|---|
| AI chat (streaming) | Real-time conversational AI with source citations |
| Fiqh rulings | Sistani-grounded jurisprudence engine |
| Hadith retrieval | Semantic search across Shia + Sunni collections |
| Quran & Tafsir | Verse lookup and scholarly commentary |
| Hikam lesson trees | Structured Islamic curriculum |
| AI elaboration | On-demand deep dives on any lesson passage |
| Personalized primers | AI-generated prerequisite summaries tailored to the learner |
| User memory | Long-term learning profile built from conversations |
| Quiz system | Multiple-choice comprehension checks per lesson page |
| Multilingual | Any-language input and output |
| Saved history | Persistent cross-session chat records |
| Reference search | Standalone hadith semantic search API |
