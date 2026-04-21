# Deferred Items — 260420-t2v

Items discovered during execution that are OUT OF SCOPE for this quick task
(pre-existing failures in unrelated code paths). Logged here per the executor
scope boundary rule.

## 1. `test_agentic_streaming_sse_to_markdown_file` fails on env bootstrap

**Discovered during:** Task 3 pytest run.

**Symptom:**

```
pydantic_core._pydantic_core.ValidationError: 1 validation error for ChatAnthropic
max_tokens
  Input should be a valid integer [type=int_type, input_value=None, input_type=NoneType]
```

**Root cause:** The project's `.env` sets `LARGE_LLM=claude-sonnet-4-6`, which
causes `langchain.init_chat_model(...)` (in `agents/core/chat_agent.py::_create_llm_with_tools`)
to instantiate `ChatAnthropic` instead of `ChatOpenAI`. The pre-existing test
passes `max_tokens=None` via `AgentConfig.model.max_tokens`, but `ChatAnthropic`
(pydantic v2) rejects `None` for `max_tokens`.

**Why deferred:** Failure is pre-existing and unrelated to this plan's SSE
granularity changes. Verified by running the test against HEAD before my
Task 1-3 edits (same failure). The granular-events test I added in Task 3
skips gracefully when pipeline bootstrap fails — so the pytest command exits
with the same pre-existing failure count (1 failed, 1 skipped) rather than a
new regression.

**Suggested fix (separate task):** Either (a) pin `LARGE_LLM` to an OpenAI
model in the test env, (b) default `AgentConfig.model.max_tokens` to an int
(e.g. 4096) instead of `None`, or (c) teach `_create_llm_with_tools` to only
pass `max_tokens` when non-None.

**Does NOT affect SUMMARY self-check.** All files and commits claimed in the
SUMMARY exist.
