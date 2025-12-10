# Plan: Parallelizing Classification Steps in Pipeline

## Executive Summary
This plan details the approach to parallelize `classify_non_islamic_query()` and `classify_fiqh_query()` in `chat_pipeline_streaming()` to reduce latency, with proper cancellation handling when one classification returns early.

---

## 1. Current State Analysis

### 1.1 Current Implementation
- **Location**: `core/pipeline.py:53-62`
- **Functions**: 
  - `classify_non_islamic_query()` - synchronous, blocking
  - `classify_fiqh_query()` - synchronous, blocking
- **Dependencies**:
  - Both use `chat_models.get_classifier_model()` (LangChain model)
  - Both call `context.get_recent_context()` (Redis access, potentially blocking)
  - Both use `chat_model.invoke()` (synchronous API call)
- **Execution**: Sequential - second call waits for first to complete
- **Return Behavior**: Boolean values, early return with StreamingResponse if True

### 1.2 Performance Characteristics
- **Current Latency**: `time(classify_non_islamic) + time(classify_fiqh)`
- **Potential Latency**: `max(time(classify_non_islamic), time(classify_fiqh))`
- **Expected Improvement**: ~50% reduction in classification time (if both take similar time)

---

## 2. Technical Approach

### 2.1 Recommended: Async/Await Pattern
**Rationale**: 
- FastAPI is async-native
- Better cancellation support with `asyncio`
- Cleaner code structure
- Better resource management

### 2.2 Alternative: Threading Pattern
**Rationale**:
- Minimal code changes if LangChain doesn't support async well
- Can use `concurrent.futures.ThreadPoolExecutor`
- More complex cancellation handling

---

## 3. Implementation Strategy

### 3.1 Phase 1: Make Classifier Functions Async

#### 3.1.1 Convert `classify_non_islamic_query()` to async
**File**: `modules/classification/classifier.py`

**Changes Required**:
- Change function signature: `async def classify_non_islamic_query(...)`
- Check if LangChain model supports `ainvoke()` (async invoke)
- If not, wrap sync call in `asyncio.to_thread()` or use `run_in_executor()`
- Make `context.get_recent_context()` async or wrap in thread executor

**Considerations**:
- LangChain's `init_chat_model()` may return sync-only models
- Need to verify async support in LangChain version
- May need to use `asyncio.to_thread()` as fallback

#### 3.1.2 Convert `classify_fiqh_query()` to async
**Same approach as above**

#### 3.1.3 Context Fetching Parallelization
**File**: `modules/context/context.py`

**Current**: `get_recent_context()` is synchronous, accesses Redis
**Options**:
- Option A: Make `get_recent_context()` async (requires Redis async client)
- Option B: Wrap in `asyncio.to_thread()` when calling from async context
- Option C: Fetch context once and pass to both classifiers (if same parameters)

**Recommendation**: Option C if both use same `session_id` and similar `max_messages`, otherwise Option B

### 3.2 Phase 2: Parallel Execution with Cancellation

#### 3.2.1 Implementation Pattern
```python
async def chat_pipeline_streaming(...):
    # ... translation step ...
    
    # Fetch context once (if both need it)
    context_task = asyncio.create_task(
        asyncio.to_thread(context.get_recent_context, session_id)
    )
    
    # Create both classification tasks
    non_islamic_task = asyncio.create_task(
        classifier.classify_non_islamic_query(user_query, session_id)
    )
    fiqh_task = asyncio.create_task(
        classifier.classify_fiqh_query(user_query, session_id)
    )
    
    # Wait for first to complete
    done, pending = await asyncio.wait(
        [non_islamic_task, fiqh_task],
        return_when=asyncio.FIRST_COMPLETED
    )
    
    # Check results and cancel pending
    for task in done:
        result = await task
        if result:  # If classification is True
            # Cancel other task
            for pending_task in pending:
                pending_task.cancel()
                try:
                    await pending_task
                except asyncio.CancelledError:
                    pass
            
            # Return early response
            message = get_message_for_classification(task)
            return StreamingResponse(...)
    
    # If neither returned True, await both and continue
    # (Handle case where both completed but returned False)
```

#### 3.2.2 Race Condition Handling

**Scenario**: Both classifications complete simultaneously, both return True

**Priority Rules** (choose one):
1. **Priority-based**: Non-Islamic takes precedence (more restrictive)
2. **First-completed**: Return whichever completed first
3. **Both-checked**: Check both, return non-Islamic if either is True

**Recommendation**: Priority-based (Option 1) - Non-Islamic classification is more restrictive

**Implementation**:
```python
# After asyncio.wait()
results = {}
for task in done:
    task_name = "non_islamic" if task == non_islamic_task else "fiqh"
    results[task_name] = await task

# Check non_islamic first (priority)
if results.get("non_islamic", False):
    # Cancel fiqh if still pending
    # Return non-islamic message
elif results.get("fiqh", False):
    # Return fiqh message
```

### 3.3 Phase 3: Error Handling

#### 3.3.1 Individual Task Errors
**Scenario**: One classification fails, other succeeds

**Strategy**:
- If one task raises exception, log it but don't fail the pipeline
- If the successful task returns True, proceed with that classification
- If the successful task returns False, check if we can trust it alone
- **Decision**: If non-islamic check fails but fiqh succeeds and returns False, should we proceed?

**Recommendation**: 
- If non-islamic check fails → treat as False (allow query to proceed)
- If fiqh check fails → treat as False (allow query to proceed)
- Log all exceptions for monitoring

**Implementation**:
```python
async def safe_classify(task, name):
    try:
        return await task
    except Exception as e:
        print(f"[ERROR] {name} classification failed: {e}")
        return False  # Fail open - allow query to proceed

# Use wrapper for both tasks
non_islamic_result = await safe_classify(non_islamic_task, "non_islamic")
fiqh_result = await safe_classify(fiqh_task, "fiqh")
```

#### 3.3.2 Both Tasks Fail
**Scenario**: Both classifications raise exceptions

**Strategy**: 
- Log both errors
- Proceed with pipeline (fail open) OR return error response
- **Recommendation**: Proceed with pipeline (fail open) - better UX than blocking all queries

#### 3.3.3 Cancellation Errors
**Scenario**: Task is cancelled but raises exception during cancellation

**Strategy**:
- Catch `asyncio.CancelledError` explicitly
- Don't log as errors (expected behavior)
- Ensure cleanup happens

### 3.4 Phase 4: Context Optimization

#### 3.4.1 Context Fetching Analysis
**Current**: 
- `classify_non_islamic_query()` calls `context.get_recent_context(session_id)` (default max_messages=6)
- `classify_fiqh_query()` calls `context.get_recent_context(session_id, 2)` (max_messages=2)

**Optimization Options**:
1. **Fetch once, reuse**: Fetch with max_messages=6, pass to both (fiqh uses subset)
2. **Fetch in parallel**: Both fetch independently (if different parameters needed)
3. **Cache in pipeline**: Fetch once at pipeline start, pass to both classifiers

**Recommendation**: Option 1 - Fetch once with max_messages=6, both classifiers can use it

**Implementation**:
```python
# Fetch context once
chat_context = await asyncio.to_thread(
    context.get_recent_context, session_id, max_messages=6
)

# Pass to both classifiers (modify signatures to accept context)
non_islamic_task = classifier.classify_non_islamic_query(
    user_query, session_id=session_id, chat_context=chat_context
)
fiqh_task = classifier.classify_fiqh_query(
    user_query, session_id=session_id, chat_context=chat_context[:2]  # or pass full and let classifier slice
)
```

---

## 4. Critical Considerations

### 4.1 LangChain Async Support
**Risk**: LangChain models may not support `ainvoke()` natively

**Mitigation**:
- Check LangChain version and async capabilities
- Use `asyncio.to_thread()` to wrap sync `invoke()` calls
- Test with actual LangChain version in use

**Verification**:
```python
# Test if model supports async
if hasattr(chat_model, 'ainvoke'):
    response = await chat_model.ainvoke(messages)
else:
    # Fallback to thread executor
    response = await asyncio.to_thread(chat_model.invoke, messages)
```

### 4.2 Redis Connection Thread Safety
**Risk**: Redis client may not be thread-safe for concurrent access

**Mitigation**:
- Verify Redis client thread safety
- Use connection pooling if needed
- Consider async Redis client (aioredis) if making context async

**Current**: Using `redis.from_url()` - check if this is thread-safe

### 4.3 API Rate Limiting
**Risk**: Parallel calls may hit OpenAI rate limits faster

**Mitigation**:
- Monitor API usage
- Consider rate limiting if needed
- Both use same model (`SMALL_LLM`), so should be fine for parallel calls

### 4.4 Backward Compatibility
**Risk**: Other code may call classifier functions synchronously

**Mitigation**:
- Keep sync versions as wrappers
- Or create separate async versions
- Update all call sites

**Options**:
1. **Breaking change**: Make both async (update all callers)
2. **Dual support**: Keep sync versions, add async versions with `_async` suffix
3. **Auto-detect**: Make functions work in both sync and async contexts

**Recommendation**: Option 2 - Add async versions, keep sync for backward compatibility

### 4.5 Pipeline Function Signature
**Current**: `chat_pipeline_streaming()` is synchronous

**Change Required**: Make it async

**Impact**: 
- Update `api/chat.py` to await the call
- Verify FastAPI handles async StreamingResponse correctly

**Implementation**:
```python
# In api/chat.py
async def chat_pipeline_stream_ep(request: ChatRequest):
    # ...
    return await pipeline.chat_pipeline_streaming(...)  # Now async
```

### 4.6 Testing Considerations

#### 4.6.1 Test Cases Needed
1. **Both return False**: Pipeline continues normally
2. **Non-Islamic returns True first**: Fiqh task cancelled, non-Islamic response returned
3. **Fiqh returns True first**: Non-Islamic task cancelled, fiqh response returned
4. **Both return True**: Non-Islamic takes priority
5. **One task fails**: Other succeeds, pipeline continues or returns based on success
6. **Both tasks fail**: Pipeline continues (fail open)
7. **Cancellation timing**: Verify cancelled task doesn't cause errors
8. **Performance**: Measure latency improvement

#### 4.6.2 Mocking Strategy
- Mock OpenAI API calls to control timing
- Simulate different completion orders
- Test error scenarios

### 4.7 Resource Management

#### 4.7.1 Memory
**Consideration**: Parallel tasks may use more memory temporarily

**Impact**: Minimal - both use same small model, responses are small

#### 4.7.2 Connection Pooling
**Consideration**: Two concurrent OpenAI API calls

**Impact**: Should be fine, but monitor connection usage

#### 4.7.3 Timeout Handling
**Consideration**: What if one task hangs?

**Strategy**: 
- Add timeout to `asyncio.wait()`
- Use `asyncio.wait_for()` with timeout
- If timeout, treat as False and proceed

**Implementation**:
```python
try:
    done, pending = await asyncio.wait_for(
        asyncio.wait([non_islamic_task, fiqh_task], return_when=asyncio.FIRST_COMPLETED),
        timeout=10.0  # 10 second timeout
    )
except asyncio.TimeoutError:
    # Cancel both, proceed with pipeline (fail open)
    non_islamic_task.cancel()
    fiqh_task.cancel()
    # Continue pipeline
```

---

## 5. Implementation Steps

### Step 1: Research & Verification
- [ ] Check LangChain version and async support
- [ ] Verify Redis client thread safety
- [ ] Test `asyncio.to_thread()` with LangChain models
- [ ] Measure current classification latency

### Step 2: Create Async Classifier Functions
- [ ] Create `classify_non_islamic_query_async()` (or modify existing)
- [ ] Create `classify_fiqh_query_async()` (or modify existing)
- [ ] Handle LangChain async/sync compatibility
- [ ] Update context fetching to be async or wrapped

### Step 3: Optimize Context Fetching
- [ ] Modify classifiers to accept pre-fetched context
- [ ] Fetch context once in pipeline
- [ ] Pass context to both classifiers

### Step 4: Update Pipeline Function
- [ ] Make `chat_pipeline_streaming()` async
- [ ] Implement parallel execution with `asyncio.wait()`
- [ ] Implement cancellation logic
- [ ] Implement race condition handling
- [ ] Add error handling for individual tasks
- [ ] Add timeout handling

### Step 5: Update API Endpoint
- [ ] Update `api/chat.py` to await pipeline call
- [ ] Verify FastAPI async StreamingResponse works

### Step 6: Testing
- [ ] Unit tests for all scenarios
- [ ] Integration tests with real API calls
- [ ] Performance benchmarks
- [ ] Error scenario testing

### Step 7: Monitoring & Observability
- [ ] Add logging for parallel execution
- [ ] Add metrics for classification times
- [ ] Monitor cancellation frequency
- [ ] Track error rates

---

## 6. Rollback Plan

### 6.1 If Issues Arise
- Keep sync versions as fallback
- Feature flag to switch between sync/async
- Gradual rollout (percentage of traffic)

### 6.2 Rollback Triggers
- Error rate increase > X%
- Latency increase (unexpected)
- Resource exhaustion
- API rate limit issues

---

## 7. Success Metrics

### 7.1 Performance
- **Target**: 40-50% reduction in classification latency
- **Measurement**: P50, P95, P99 latencies before/after

### 7.2 Reliability
- **Target**: No increase in error rate
- **Measurement**: Error rate comparison

### 7.3 Resource Usage
- **Target**: No significant increase in API calls or memory
- **Measurement**: API usage, memory metrics

---

## 8. Alternative Approaches (If Async Doesn't Work)

### 8.1 Threading with Futures
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=2) as executor:
    non_islamic_future = executor.submit(
        classifier.classify_non_islamic_query, user_query, session_id
    )
    fiqh_future = executor.submit(
        classifier.classify_fiqh_query, user_query, session_id
    )
    
    for future in as_completed([non_islamic_future, fiqh_future]):
        result = future.result()
        if result:
            # Cancel other future (may not be fully cancellable)
            other_future.cancel()
            # Return response
```

**Limitations**:
- Thread cancellation is less reliable
- More complex error handling
- Thread overhead

### 8.2 Sequential with Early Exit Optimization
If parallelization proves too complex, optimize sequential execution:
- Make context fetching more efficient
- Cache model instances
- Optimize prompt templates

---

## 9. Open Questions

1. **LangChain Async Support**: Does current version support `ainvoke()`?
2. **Redis Async**: Should we migrate to async Redis client?
3. **Priority**: Which classification should take precedence if both return True?
4. **Fail Strategy**: Fail open (proceed) or fail closed (block) on errors?
5. **Timeout Value**: What's appropriate timeout for classification calls?
6. **Monitoring**: What metrics should we track?

---

## 10. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| LangChain doesn't support async | Medium | High | Use `asyncio.to_thread()` |
| Race condition bugs | Low | Medium | Thorough testing, priority rules |
| Cancellation issues | Low | Low | Proper exception handling |
| Increased API costs | Low | Low | Monitor usage |
| Backward compatibility | Medium | Medium | Keep sync versions |
| Redis thread safety | Low | Medium | Verify, use connection pooling |

---

## 11. Timeline Estimate

- **Research & Verification**: 2-4 hours
- **Implementation**: 4-6 hours
- **Testing**: 3-4 hours
- **Code Review & Refinement**: 2-3 hours
- **Total**: 11-17 hours

---

## 12. Dependencies

- Python 3.11+ (for asyncio features)
- LangChain version with async support (or use thread executor)
- FastAPI async support (already available)
- Redis client (verify thread safety or use async client)

---

## Conclusion

Parallelizing the classification steps is **feasible and recommended** for performance improvement. The async/await approach is preferred, with threading as a fallback. Key success factors:

1. Proper async support or thread executor fallback
2. Robust error handling and cancellation
3. Clear priority rules for race conditions
4. Comprehensive testing
5. Monitoring and observability

The implementation should be done incrementally with thorough testing at each step.


