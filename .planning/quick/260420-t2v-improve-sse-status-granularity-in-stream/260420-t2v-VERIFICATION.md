---
phase: 260420-t2v
verified: 2026-04-20T00:00:00Z
status: passed
score: 6/6 truths verified
re_verification: false
human_verification:
  - test: "Hit POST /chat/stream/agentic with a fiqh query (e.g. 'Is it halal to eat shrimp?') via curl or the frontend"
    expected: "SSE stream starts with a 'status' event {step:'starting', message:'Checking query classification...'} within ~100ms, followed by 'fiqh_classification', then 'fiqh_subgraph' ('Processing fiqh query (this may take 10-15 seconds)...'), then a retrospective rapid-fire batch of fiqh_decompose/fiqh_retrieve/fiqh_filter/fiqh_assess (and optional fiqh_refine + iter 2), then 'generate_fiqh_response', response_chunk*N, response_end, fiqh_references, done. No silent window before the first status event."
    why_human: "End-to-end ordering assertion requires a live OpenAI + Pinecone environment. The automated pytest (Task 3) already guards structural ordering but skips gracefully in the current bootstrap env (pre-existing LARGE_LLM=claude-sonnet-4-6 Anthropic ValidationError), so only a live run can confirm user-perceived latency reduction."
  - test: "Hit POST /chat/stream/agentic with a non-fiqh query (e.g. 'Tell me about Imam Ali')"
    expected: "Pre-flight 'starting' status appears first. Then fiqh_classification, agent, per-tool status events (enhance_query_tool, retrieve_shia_documents_tool, retrieve_quran_tafsir_tool, etc.) BEFORE any retrieval latency. NO generic 'tools' node status emission (node_msg is None). Then generate_response ('Preparing answer...') and the response_chunk stream, hadith_references/quran_references, done."
    why_human: "Same rationale — requires live services. Automated tests verify structural preservation and the new per-tool emission intent; only a live run confirms UX improvement."
  - test: "Send a streaming agentic request with a valid JWT and confirm a ChatMessage(role='assistant') row lands in Postgres with the generated text unchanged"
    expected: "wrap_streaming_response_for_persistence still extracts and persists the assistant text correctly. Proves response_chunk payload shape is unchanged in practice."
    why_human: "Requires authenticated request + live DB; cannot be verified statically beyond confirming response_chunk shape/extractor contract (which this verification did confirm)."
---

# Quick Task 260420-t2v: Improve SSE Status Granularity — Verification Report

**Task Goal:** The frontend should receive MORE GRANULAR and MORE FREQUENT `status` events during the agentic flow on `/chat/stream/agentic`. Specifically, eliminate the user-reported "stuck on Classifying fiqh query" silent gap, preserve the existing SSE event contract, and cover both fiqh and non-fiqh paths.

**Verified:** 2026-04-20
**Status:** passed
**Re-verification:** No — initial verification.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Frontend receives a status SSE event within ~1s of any long-running stage starting (classification, per-tool, each fiqh sub-graph stage, pre-generation). | VERIFIED | Pre-flight `sse_event("status", {"step": "starting", "message": "Checking query classification..."})` at `core/pipeline_langgraph.py:109-112`, emitted BEFORE `async for event in agent.astream(...)` at line 114. Per-tool status emission on the `agent` node event at lines 135-157 (before `tools` node runs, since `_agent_node` appends the AIMessage with tool_calls before returning). Keep-alive fiqh_subgraph status at node-arrival (via `NODE_STATUS_MESSAGES["fiqh_subgraph"]` line 32, emitted at line 128-129). Pre-generation status at lines 229 (fiqh) and 308 (non-fiqh). |
| 2 | For a fiqh query, the frontend sees distinct status messages: classification → decompose → retrieval (per iteration) → filter → assess → (optional refine) → generation preamble → token stream. | VERIFIED | `_call_fiqh_subgraph_node` (agents/core/chat_agent.py:333-340) returns `fiqh_status_events=list(status_events)` in node delta on success; `fiqh_status_events=[]` on exception (lines 342-348). `agents/fiqh/fiqh_graph.py` accumulates status_events in _decompose, _retrieve, _filter, _assess, _refine (10 matches on `status_events` across lines 29-167). Pipeline drains them in order at `core/pipeline_langgraph.py:164-177`. `generate_fiqh_response` preamble at line 229 before `chain.stream()` at line 250. Canned stage fallback at lines 219-227 gated on `fiqh_trail_emitted` (error path only). |
| 3 | For a non-fiqh query, per-tool status events appear BEFORE tool begins executing. | VERIFIED | Per-tool emission scoped to `node_name == "agent"` (line 135) — the `_agent_node` in chat_agent.py appends AIMessage with `tool_calls` BEFORE returning, so LangGraph astream surfaces it on the `agent` event before the `tools` node runs. Redundant scan on the `tools` node removed. `NODE_STATUS_MESSAGES["tools"] = None` (line 28) naturally suppresses a generic emission via the `if node_msg:` guard (line 128). |
| 4 | Existing SSE events (response_chunk, response_end, hadith_references, quran_references, fiqh_references, error, done) are still emitted with identical payload shapes. | VERIFIED | grep confirms `response_chunk` shape is always `{"token": ...}` at 10 call sites in pipeline_langgraph.py (lines 189, 243, 257, 264, 267, 270, 302, 328, 340). `response_end`, `hadith_references`, `quran_references`, `fiqh_references`, `error`, `done` shapes all preserved (lines 190, 244, 276, 291, 303, 331, 341, 355, 359, 361, 378, 379, 199). |
| 5 | Assistant text is still correctly collected and persisted. | VERIFIED | `services/chat_persistence_service.py::_extract_agentic_sse_answer_text` (line 51) reads ONLY `response_chunk` event type (line 69: `if event_type != "response_chunk" or not data_lines`). Since `response_chunk` payload (`{"token": str}`) is unchanged, extractor still works. `append_turn_to_runtime_history` calls preserved in both fiqh (lines 281-286) and non-fiqh (lines 346-351) branches. |
| 6 | tests/test_agentic_streaming_sse.py still has both original + new granular test. | VERIFIED | AST parse confirms both `test_agentic_streaming_sse_to_markdown_file` (line 186) and `test_agentic_streaming_emits_granular_status_events` (line 209) exist. Dual-path detection via `is_fiqh_path` (line 257) and `is_nonfiqh_path` (line 258). Skip-gracefully guards via `pytest.skip` at lines 237, 239, 243, 262, 266. Per-path assertions at lines 279-308. |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Level 1 (Exists) | Level 2 (Substantive) | Level 3 (Wired) | Level 4 (Data Flows) | Status |
|---|---|---|---|---|---|---|
| `core/pipeline_langgraph.py` | Granular SSE status emission (pre-flight, per-tool-on-agent-event, fiqh keep-alive + retrospective, pre-generation) | Yes | Yes (431 lines; contains `sse_event("status"` — 7+ occurrences) | Yes (imported by `api/chat.py` as the primary streaming path per CLAUDE.md) | Yes (pre-flight emission uses literal string; fiqh_status_events consumed from node_state; response_chunk shape preserved) | VERIFIED |
| `agents/state/chat_state.py` | New `fiqh_status_events` field + init in `create_initial_state` | Yes | Yes (field declared line 131-134; initialized `fiqh_status_events=[]` line 197) | Yes (ChatState consumed by chat_agent.py and pipeline_langgraph.py) | Yes (runtime check: `create_initial_state(...)` returns dict with `fiqh_status_events=[]`) | VERIFIED |
| `agents/core/chat_agent.py` | `_call_fiqh_subgraph_node` returns `fiqh_status_events` in node delta (success + failure) | Yes | Yes (success path returns `"fiqh_status_events": list(status_events)` line 339; exception path returns `"fiqh_status_events": []` line 346) | Yes (node added to workflow at line 71; reached via `_route_after_fiqh_check`) | Yes (`result.get("status_events", [])` line 326 reads real data from sub-graph return; sub-graph confirmed to append in every node) | VERIFIED |
| `agents/fiqh/fiqh_graph.py` | Sub-graph accumulates status_events and returns them in each node's delta | Yes | Yes (10 grep hits on `status_events` across _decompose, _retrieve, _filter, _assess, _refine nodes; each appends and returns `list(state["status_events"])`) | Yes (sub-graph invoked by chat_agent.py::_call_fiqh_subgraph_node line 315) | Yes (append pattern mutates state; list copy returned in each node delta) | VERIFIED |
| `tests/test_agentic_streaming_sse.py` | New granular dual-path assertion test | Yes | Yes (351 lines; contains the new test at line 209, dual-path detection, per-path assertions, skip guards) | Yes (pytest-discoverable; `@_maybe_mark_asyncio` applied) | N/A (test file, not a data-producing artifact) | VERIFIED |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `core/pipeline_langgraph.py::response_generator` | Pre-flight SSE status emission | Emit `status` with `step="starting"` BEFORE `async for event in agent.astream(...)` | WIRED | Pre-flight emission at lines 109-112. regex match `sse_event\("status".*starting` confirmed in preamble before `astream(` at line 114. |
| `core/pipeline_langgraph.py::chat_pipeline_streaming_agentic` | tool_calls iteration on `agent` node event only | Per-tool `status` emitted via `node_state["messages"]` scan scoped to `node_name == "agent"` | WIRED | Line 135: `if node_name == "agent":` guards the tool_calls scan. `emitted_tool_call_ids` dedup preserved (line 101, 149-150). |
| `agents/core/chat_agent.py::_call_fiqh_subgraph_node` | pipeline_langgraph.py sub-graph event handling | Return `fiqh_status_events` in node delta so LangGraph surfaces them | WIRED | Returned in success (line 339) AND exception (line 346) branches. Consumed at pipeline_langgraph.py lines 164-177. Name matches ChatState field. |
| `core/pipeline_langgraph.py` | fiqh sub-graph keep-alive status | Emit `fiqh_subgraph` status with latency expectation on node-arrival | WIRED | `NODE_STATUS_MESSAGES["fiqh_subgraph"] = "Processing fiqh query (this may take 10-15 seconds)..."` (line 32). Emitted via standard node-arrival path at line 128-129 since `if node_msg:` is truthy. String contains "10-15" and "may take". |
| `core/pipeline_langgraph.py` | `services/chat_persistence_service.wrap_streaming_response_for_persistence` | `response_chunk` payload shape `{"token": str}` unchanged | WIRED | 10 call sites of `sse_event("response_chunk", {"token": ...})` confirmed; extractor in chat_persistence_service.py line 69 filters only on `response_chunk`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| `pipeline_langgraph.py` (pre-flight status) | literal "Checking query classification..." | Hardcoded string | Yes (advisory status message, by design not dynamic) | FLOWING |
| `pipeline_langgraph.py` (fiqh trail) | `fiqh_status_events` | Populated by `_call_fiqh_subgraph_node` node delta → `node_state.get("fiqh_status_events")` at line 165 | Yes — real per-iteration events from fiqh sub-graph (append pattern verified in `fiqh_graph.py`); empty list only on exception path | FLOWING |
| `pipeline_langgraph.py` (per-tool status) | `node_state["messages"]` → latest AIMessage.tool_calls | Real LLM output from `_agent_node` in chat_agent.py (line 168 `self.llm.invoke(...)`); tool_calls are a genuine LLM response attribute | Yes — unchanged from pre-plan behavior; refactor just scopes the scan, does not alter source | FLOWING |
| `pipeline_langgraph.py` (response_chunk) | `chain.stream()` token iterator | `fiqh_prompt | model` (line 248) or `prompt | chat_model` (line 313); both are real LangChain chain streams | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| `ChatState.fiqh_status_events` is initialized on every call to `create_initial_state` | `python -c "from agents.state.chat_state import create_initial_state; s = create_initial_state(user_query='test', session_id='x'); assert 'fiqh_status_events' in s and s['fiqh_status_events'] == []; print('OK')"` | `OK: fiqh_status_events initialized` | PASS |
| `pipeline_langgraph` module imports cleanly | `python -c "from core import pipeline_langgraph; print('OK')"` | `USING REDIS, MEMORY PERSISTENCE ENABLED` + `pipeline_langgraph imports OK` | PASS |
| Pre-flight 'starting' sse_event is emitted BEFORE `agent.astream` in source | AST + regex scan of `core/pipeline_langgraph.py` | Found `sse_event("status", {"step": "starting", ...})` in preamble before `async for event in agent.astream(` | PASS |
| `NODE_STATUS_MESSAGES["fiqh_subgraph"]` contains "10-15" latency expectation | grep `10-15` on source | Matched at line 32: `"Processing fiqh query (this may take 10-15 seconds)..."` | PASS |
| `NODE_STATUS_MESSAGES["tools"]` set to None | regex `"tools":\s*None` | Matched at line 28 | PASS |
| `response_chunk` payload shape is `{"token": ...}` everywhere | regex scan | 10 call sites, all match `sse_event("response_chunk", {"token": ...})` | PASS |
| Both tests present in test file | AST scan | Both `test_agentic_streaming_sse_to_markdown_file` and `test_agentic_streaming_emits_granular_status_events` found | PASS |
| Full pytest run on the file | `pytest tests/test_agentic_streaming_sse.py` | Per SUMMARY test evidence: 1 pre-existing failure (env: ChatAnthropic max_tokens), 1 skip (new test, graceful) — not a regression; pre-existing failure documented in deferred-items.md | SKIP (env-dependent — runs skipped gracefully in current bootstrap env, behavior verified statically) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| SSE-GRAN-01 | 260420-t2v-PLAN.md | Stream fine-grained status events during fiqh sub-graph stages | SATISFIED | `fiqh_status_events` field added to ChatState; `_call_fiqh_subgraph_node` surfaces sub-graph status_events via node delta; pipeline_langgraph.py lines 164-177 emits one SSE status event per entry in order. Truth 2 verified. |
| SSE-GRAN-02 | 260420-t2v-PLAN.md | Emit tool-start status events BEFORE tool execution | SATISFIED | Per-tool emission scoped to `agent` node event (line 135); LangGraph astream surfaces AIMessage with tool_calls on the `agent` event BEFORE the `tools` node runs because `_agent_node` appends it synchronously before returning. Redundant scan on `tools` event removed. Truth 3 verified. |
| SSE-GRAN-03 | 260420-t2v-PLAN.md | Emit pre-generation / waypoint status events to cover silent gaps | SATISFIED | Pre-flight `starting` event BEFORE `agent.astream` (lines 109-112) covers the classify_fiqh_query silent gap. `fiqh_subgraph` keep-alive at node-arrival with explicit "10-15 seconds" latency expectation (line 32). `generate_fiqh_response` and `generate_response` ("Preparing answer...") waypoints at lines 229 and 308. Truth 1 verified. |
| SSE-GRAN-04 | 260420-t2v-PLAN.md | Preserve existing SSE contract (event names, payload shapes) | SATISFIED | All non-status event shapes preserved (response_chunk, response_end, hadith_references, quran_references, fiqh_references, error, done) — verified by grep on 10+ call sites. `_extract_agentic_sse_answer_text` still reads only `response_chunk` — chat persistence unaffected. Truth 4 + Truth 5 verified. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| (none) | — | — | — | No TODO/FIXME/placeholder/stub patterns introduced by the three scoped commits. The `fiqh_status_events: []` default is a legitimate empty initial state that is populated by the fiqh sub-graph when the fiqh path runs (and correctly empty on non-fiqh paths, as documented in the field docstring). |

Note: A minor SUMMARY discrepancy — the SUMMARY.md lists commit hashes `a3651d4`, `1de7e23`, `e4cea20`, but the actual git log shows `58db0c0`, `a2a85ec`, `2958ce1` (plus `54c8418` for the docs commit). This is likely due to a rebase/amend after the SUMMARY was written. The code changes themselves are present in HEAD and the commit SUBJECTS match. Classification: INFO (non-blocking, cosmetic inconsistency in SUMMARY only).

### Human Verification Required

While automated checks pass, three items benefit from live-service verification:

1. **Live fiqh-path stream**
   - **Test:** `curl -N -X POST http://127.0.0.1:8000/chat/stream/agentic -H "Content-Type: application/json" -d '{"query":"Is it halal to eat shrimp?","session_id":"vf-fiqh"}'`
   - **Expected:** `starting` event fires within ~100ms (no silent window). Subsequent ordering: `fiqh_classification` → `fiqh_subgraph` (with "10-15 seconds" message) → retrospective batch of `fiqh_decompose`, `fiqh_retrieve` (with iteration markers), `fiqh_filter`, `fiqh_assess` (optional `fiqh_refine` + iter 2) → `generate_fiqh_response` → `response_chunk` × N → `response_end` → `fiqh_references` → `done`.
   - **Why human:** Requires a live OpenAI + Pinecone env. The current `.env` has a `LARGE_LLM=claude-sonnet-4-6` mismatch that causes pipeline bootstrap to fail (documented in `deferred-items.md`, pre-existing).

2. **Live non-fiqh-path stream**
   - **Test:** `curl -N -X POST http://127.0.0.1:8000/chat/stream/agentic -H "Content-Type: application/json" -d '{"query":"Tell me about Imam Ali","session_id":"vf-nonfiqh"}'`
   - **Expected:** Pre-flight `starting` → `fiqh_classification` → `agent` → per-tool status events (`enhance_query_tool`, `retrieve_shia_documents_tool`, `retrieve_quran_tafsir_tool`, …) BEFORE retrieval latency → NO generic `tools` node emission → `generate_response` ("Preparing answer...") → `response_chunk` × N → `response_end` → `hadith_references`/`quran_references` → `done`.
   - **Why human:** Same env dependency.

3. **Chat persistence regression**
   - **Test:** Issue a JWT-authenticated agentic streaming request, then query Postgres: `SELECT role, content FROM chat_messages WHERE session_id = '<sid>' ORDER BY created_at DESC LIMIT 2;`
   - **Expected:** Latest row is `role='assistant'` with the full generated text intact. Proves `wrap_streaming_response_for_persistence` still extracts `response_chunk` tokens correctly after the granularity change.
   - **Why human:** Requires live Cognito JWT + Postgres. Static verification already confirmed `_extract_agentic_sse_answer_text` only reads `response_chunk` (unchanged), so this is a confirmation rather than a risk.

### Gaps Summary

No gaps. All six must-have truths are verified in source, all five artifacts pass levels 1-4 (where applicable), all five key links are wired, all four declared requirements (SSE-GRAN-01 through SSE-GRAN-04) are satisfied, and no anti-patterns or stubs were introduced.

Three items routed to human verification are due to the current bootstrap environment mismatch (pre-existing, documented in `deferred-items.md` as out-of-scope) preventing end-to-end pytest execution. The new test is correctly designed to skip gracefully in that env, which matches the plan's explicit `<done>` criterion that the test must "exit 0 (passing or gracefully skipping; never failing due to ... env issues)".

---

_Verified: 2026-04-20_
_Verifier: Claude (gsd-verifier)_
