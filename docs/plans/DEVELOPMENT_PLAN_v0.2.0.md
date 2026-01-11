# Plan: Gracefully Handle Workflow Recursion Limit Errors

## Problem Statement

The Agentic RAG workflow hits LangGraph's default recursion limit of 25 steps and crashes with:
```
ERROR: Recursion limit of 25 reached without hitting a stop condition.
```

This happens because:
1. **No explicit recursion limit** is configured in workflow compilation
2. **Infinite hallucination correction loops** - regenerations have no counter or exit condition
3. **Incomplete routing logic** - some paths don't handle exhausted retries properly
4. **No graceful degradation** - errors crash the system instead of returning a fallback response

## Root Causes (Detailed Analysis)

### Issue 1: No Recursion Limit Configuration
**File:** [src/graph/workflow.py:161](src/graph/workflow.py#L161)

The workflow compiles without recursion limit:
```python
app = workflow.compile()  # Uses default limit of 25
```

### Issue 2: Unlimited Regeneration Loop
**Files:**
- [src/graph/routers.py:153-222](src/graph/routers.py#L153-L222) - `check_hallucination_and_usefulness` router
- [src/graph/nodes.py:126-179](src/graph/nodes.py#L126-L179) - `generate` node

**Problem:** When hallucination is detected (line 213 in routers.py):
```python
if state.get("hallucination_check") == "not_grounded":
    return "generate"  # Regenerate - NO COUNTER, NO LIMIT
```

This can loop infinitely:
```
generate → check_hallucination → check_usefulness
→ [hallucinated] → generate → [repeat until crash]
```

**Missing:**
- No `regeneration_count` in state to track attempts
- No check against max regenerations in router
- No fallback when max regenerations exceeded

### Issue 3: Incomplete Retry Handling
**File:** [src/graph/routers.py:101-150](src/graph/routers.py#L101-L150) - `decide_to_web_search` router

The router handles relevance but **never checks retry_count**:
```python
relevance_ratio = relevant_docs / total_docs if total_docs > 0 else 0

if relevance_ratio < 0.5:
    return "web_search"  # Low relevance → web search
else:
    return "generate"  # Sufficient relevance → generate
```

**Missing path:** What if web search also fails or retries are exhausted?

### Issue 4: Poor Error Handling
**File:** [src/graph/workflow.py:207-218](src/graph/workflow.py#L207-L218)

Current error handling just re-raises:
```python
try:
    result = self.workflow.invoke(initial_state)
    return result
except Exception as e:
    logger.error(f"Workflow execution failed: {e}")
    raise Exception(f"Workflow failed: {e}")  # Crashes
```

**Missing:**
- No detection of recursion limit errors
- No fallback response generation
- No partial result extraction

## Recommended Solution

Implement a **multi-layered approach** to gracefully handle recursion limits:

### Layer 1: Increase Recursion Limit (Quick Fix)
Set a reasonable recursion limit in workflow compilation.

### Layer 2: Add Regeneration Counter (Core Fix)
Track and limit hallucination correction attempts.

### Layer 3: Improve Router Logic (Structural Fix)
Add fallback paths for exhausted retries.

### Layer 4: Graceful Error Recovery (User Experience Fix)
Catch recursion errors and return a helpful fallback response.

---

## Implementation Plan

### Change 1: Add Regeneration Tracking to State

**File:** [src/graph/state.py](src/graph/state.py)

Add new state field:
```python
class GraphState(TypedDict):
    question: str
    generation: str
    web_search_needed: str
    documents: List[Document]
    retry_count: int  # Existing: for query rewrites
    regeneration_count: int  # NEW: for hallucination corrections
    relevance_scores: List[str]
    hallucination_check: str
    usefulness_check: str
    prompt_variant: str
```

**Justification:** Need to track regeneration attempts separately from query rewrites.

---

### Change 2: Add Configuration Settings

**File:** [config/settings.py](config/settings.py)

Add new settings:
```python
# After MAX_RETRIES (around line 124)
MAX_REGENERATIONS: int = Field(
    default=3,
    ge=1,
    le=10,
    description="Maximum answer regeneration attempts for hallucination correction"
)

WORKFLOW_RECURSION_LIMIT: int = Field(
    default=50,
    ge=25,
    le=200,
    description="Maximum workflow steps before stopping (LangGraph recursion limit)"
)
```

**Justification:**
- `MAX_REGENERATIONS=3` allows up to 3 regeneration attempts
- `WORKFLOW_RECURSION_LIMIT=50` doubles the default limit
- With max 3 query rewrites + 3 regenerations = 6 major loops × ~7 nodes = ~42 steps (under 50)

---

### Change 3: Update Generate Node to Track Regenerations

**File:** [src/graph/nodes.py](src/graph/nodes.py)

Modify `generate` node (around line 126-179):
```python
def generate(state: GraphState) -> GraphState:
    """Generate answer from documents using RAG."""
    logger.info(">>> generate")

    question = state["question"]
    documents = state["documents"]
    prompt_variant = state.get("prompt_variant", "baseline")

    # Increment regeneration count if this is a retry
    regeneration_count = state.get("regeneration_count", 0)
    hallucination_check = state.get("hallucination_check", "")

    # If we detected hallucination in previous attempt, this is a regeneration
    if hallucination_check == "not_grounded":
        regeneration_count += 1
        logger.warning(f"Regenerating answer (attempt {regeneration_count})")

    # Generate answer
    generator = AnswerGenerator(variant=prompt_variant)
    generation = generator.generate(question, documents)

    # Log result
    logger.info(f"Generated answer: {generation[:100]}...")

    return {
        "generation": generation,
        "regeneration_count": regeneration_count
    }
```

**Justification:** Track when we're regenerating vs. first generation.

---

### Change 4: Update Router to Check Regeneration Limit

**File:** [src/graph/routers.py](src/graph/routers.py)

Modify `check_hallucination_and_usefulness` router (lines 153-222):
```python
def check_hallucination_and_usefulness(state: GraphState) -> str:
    """
    Determine next step based on hallucination and usefulness checks.

    Routes to:
    - "generate": If hallucinated and regenerations remaining
    - "transform_query": If not useful and retries remaining
    - "end": If answer is good OR limits exhausted
    """
    hallucination_check = state.get("hallucination_check", "")
    usefulness_check = state.get("usefulness_check", "")
    retry_count = state.get("retry_count", 0)
    regeneration_count = state.get("regeneration_count", 0)

    logger.info(
        f"Final checks - Hallucination: {hallucination_check}, "
        f"Usefulness: {usefulness_check}, "
        f"Retries: {retry_count}, "
        f"Regenerations: {regeneration_count}"
    )

    # Check if hallucinated
    if hallucination_check == "not_grounded":
        # Check if we can regenerate
        if regeneration_count < settings.MAX_REGENERATIONS:
            logger.warning(
                f"Answer hallucinated, regenerating "
                f"(attempt {regeneration_count + 1}/{settings.MAX_REGENERATIONS})"
            )
            return "generate"
        else:
            logger.error(
                f"Max regenerations ({settings.MAX_REGENERATIONS}) exceeded. "
                f"Returning best attempt despite hallucination."
            )
            return "end"  # Stop even if hallucinated

    # Check if useful
    if usefulness_check == "not_useful":
        # Check if we can retry with better query
        if retry_count < settings.MAX_RETRIES:
            logger.warning(
                f"Answer not useful, rewriting query "
                f"(attempt {retry_count + 1}/{settings.MAX_RETRIES})"
            )
            return "transform_query"
        else:
            logger.error(
                f"Max retries ({settings.MAX_RETRIES}) exceeded. "
                f"Returning best attempt despite low usefulness."
            )
            return "end"  # Stop even if not useful

    # Success case
    logger.info("✓ Answer is grounded and useful")
    return "end"
```

**Key changes:**
1. Check `regeneration_count < MAX_REGENERATIONS` before regenerating
2. Check `retry_count < MAX_RETRIES` before rewriting (already exists but add logging)
3. Return `"end"` when limits exhausted (graceful degradation)
4. Add detailed logging for troubleshooting

---

### Change 5: Configure Recursion Limit in Workflow Compilation

**File:** [src/graph/workflow.py](src/graph/workflow.py)

Modify `_build_workflow` method (line 161):
```python
def _build_workflow(self) -> StateGraph:
    """Build the complete LangGraph StateGraph with all agentic features."""
    logger.info("Building complete agentic RAG workflow graph")

    # Create the StateGraph
    workflow = StateGraph(GraphState)

    # ... [add all nodes and edges - no changes] ...

    # Compile the graph with recursion limit
    app = workflow.compile(
        config={
            "recursion_limit": settings.WORKFLOW_RECURSION_LIMIT
        }
    )

    logger.info(
        f"Complete agentic RAG workflow graph built and compiled "
        f"(recursion_limit={settings.WORKFLOW_RECURSION_LIMIT})"
    )

    return app
```

**Justification:**
- Sets explicit recursion limit from configuration
- Default 50 steps handles complex scenarios
- Still protects against true infinite loops

---

### Change 6: Add Graceful Error Recovery

**File:** [src/graph/workflow.py](src/graph/workflow.py)

Enhance `run()` method error handling (lines 207-218):
```python
def run(self, question: str) -> Dict[str, Any]:
    """Run the workflow with a question."""
    if not question:
        raise ValueError("Question cannot be empty")

    logger.info(f"Running workflow for question: {question[:100]}...")

    # Initialize state
    initial_state: GraphState = {
        "question": question,
        "generation": "",
        "web_search_needed": "No",
        "documents": [],
        "retry_count": 0,
        "regeneration_count": 0,  # NEW
        "relevance_scores": [],
        "hallucination_check": "",
        "usefulness_check": "",
        "prompt_variant": self.prompt_variant
    }

    try:
        # Run the workflow
        result = self.workflow.invoke(initial_state)

        logger.info("Workflow completed successfully")
        logger.debug(f"Final state keys: {list(result.keys())}")

        return result

    except Exception as e:
        error_message = str(e)

        # Check if this is a recursion limit error
        if "recursion" in error_message.lower() or "Recursion limit" in error_message:
            logger.error(
                f"Workflow hit recursion limit after {settings.WORKFLOW_RECURSION_LIMIT} steps. "
                f"Question may be too complex or system is stuck in a loop."
            )

            # Return a graceful fallback response
            return {
                "question": question,
                "generation": (
                    "I apologize, but I'm having difficulty answering this question. "
                    "The system exhausted its maximum processing steps while trying to "
                    "generate a reliable answer. This could mean:\n\n"
                    "1. The question requires information not available in the knowledge base\n"
                    "2. The retrieval system is struggling to find relevant documents\n"
                    "3. The answer generation is stuck in a correction loop\n\n"
                    "Please try:\n"
                    "- Rephrasing your question more specifically\n"
                    "- Breaking complex questions into simpler parts\n"
                    "- Checking if the knowledge base contains relevant information"
                ),
                "documents": [],
                "retry_count": initial_state["retry_count"],
                "regeneration_count": initial_state["regeneration_count"],
                "relevance_scores": [],
                "hallucination_check": "error",
                "usefulness_check": "error",
                "web_search_needed": "No",
                "prompt_variant": self.prompt_variant,
                "error": "recursion_limit_exceeded"
            }
        else:
            # Other errors - log and re-raise
            logger.error(f"Workflow execution failed: {e}")
            raise Exception(f"Workflow failed: {e}")
```

**Key changes:**
1. Initialize `regeneration_count: 0` in initial state
2. Detect recursion limit errors specifically
3. Return a **helpful fallback response** instead of crashing
4. Include troubleshooting suggestions for users
5. Mark error in response metadata for debugging

---

### Change 7: Initialize Regeneration Count in Stream Method

**File:** [src/graph/workflow.py](src/graph/workflow.py)

Update `stream()` method (around line 245):
```python
# Initialize state
initial_state: GraphState = {
    "question": question,
    "generation": "",
    "web_search_needed": "No",
    "documents": [],
    "retry_count": 0,
    "regeneration_count": 0,  # NEW
    "relevance_scores": [],
    "hallucination_check": "",
    "usefulness_check": "",
    "prompt_variant": self.prompt_variant
}
```

---

### Change 8: Update Documentation

**File:** [README.md](README.md) or [CLAUDE.md](CLAUDE.md)

Add section explaining error recovery:
```markdown
### Error Recovery

The system includes graceful error handling for workflow recursion limits:

- **Max Query Rewrites**: 3 attempts (configurable via `MAX_RETRIES`)
- **Max Regenerations**: 3 attempts for hallucination correction (configurable via `MAX_REGENERATIONS`)
- **Workflow Recursion Limit**: 50 steps maximum (configurable via `WORKFLOW_RECURSION_LIMIT`)

If the workflow exhausts these limits, it will:
1. Log detailed error information
2. Return the best available answer with a disclaimer
3. Provide troubleshooting suggestions to the user

Configure these limits in `.env`:
```env
MAX_RETRIES=3
MAX_REGENERATIONS=3
WORKFLOW_RECURSION_LIMIT=50
```
```

---

## Critical Files to Modify

1. **[src/graph/state.py](src/graph/state.py)** - Add `regeneration_count` field
2. **[config/settings.py](config/settings.py)** - Add `MAX_REGENERATIONS` and `WORKFLOW_RECURSION_LIMIT`
3. **[src/graph/nodes.py](src/graph/nodes.py)** - Update `generate` node to track regenerations
4. **[src/graph/routers.py](src/graph/routers.py)** - Update `check_hallucination_and_usefulness` with limits
5. **[src/graph/workflow.py](src/graph/workflow.py)** - Configure recursion limit and add error recovery
6. **[README.md](README.md)** or **[CLAUDE.md](CLAUDE.md)** - Document error recovery

---

## Testing Strategy

### Test 1: Verify Configuration
```bash
# Check settings load correctly
python config/settings.py
# Should show: MAX_REGENERATIONS=3, WORKFLOW_RECURSION_LIMIT=50
```

### Test 2: Test Hallucination Loop Protection
Create a test that intentionally triggers hallucination:
```python
# Mock the hallucination grader to always return "not_grounded"
# Verify workflow stops after 3 regenerations and returns fallback
```

### Test 3: Test Query Rewrite Loop Protection
```python
# Mock document retrieval to always return irrelevant docs
# Verify workflow stops after 3 retries and either uses web search or returns fallback
```

### Test 4: Test Recursion Limit Error Recovery
```python
# Set WORKFLOW_RECURSION_LIMIT=10 (very low)
# Ask a complex question
# Verify graceful fallback response is returned instead of crash
```

### Test 5: End-to-End Happy Path
```python
# Normal question with good documents
# Verify counts are tracked correctly: regeneration_count=0, retry_count=0
```

### Test 6: Verify State Persistence
```python
# Use workflow.stream() to monitor state changes
# Check that regeneration_count increments correctly on hallucination
```

---

## Expected Behavior After Implementation

### Scenario 1: Normal Operation (No Errors)
```
Question → Retrieve → Grade → Generate → Check → ✓ Success
regeneration_count=0, retry_count=0
```

### Scenario 2: Hallucination Correction (1-3 Attempts)
```
Question → Retrieve → Grade → Generate → Check → Hallucinated
→ Regenerate (count=1) → Check → Still hallucinated
→ Regenerate (count=2) → Check → Still hallucinated
→ Regenerate (count=3) → Check → Still hallucinated
→ STOP → Return best attempt with disclaimer
```

**Fallback message:**
"I generated an answer but I'm not fully confident it's grounded in the provided sources..."

### Scenario 3: Query Rewriting (1-3 Attempts)
```
Question → Retrieve → Grade → No relevant docs
→ Rewrite query (retry=1) → Retrieve → Grade → No relevant
→ Rewrite query (retry=2) → Retrieve → Grade → No relevant
→ Rewrite query (retry=3) → Retrieve → Grade → No relevant
→ Web search fallback OR return "I don't know"
```

### Scenario 4: Recursion Limit Hit (System Protection)
```
[Complex looping scenario beyond 50 steps]
→ LangGraph raises RecursionError
→ Workflow catches error
→ Returns graceful fallback with troubleshooting tips
```

---

## Benefits of This Approach

1. **Graceful Degradation** - Never crashes, always returns something
2. **Transparent Limits** - Users understand why the system stopped
3. **Configurable** - Limits can be tuned per deployment
4. **Debuggable** - Detailed logging shows exactly where loops occur
5. **User-Friendly** - Fallback responses include helpful suggestions
6. **Safe** - Multiple layers prevent infinite loops

---

## Alternative Approaches Considered

### Alternative 1: Only Increase Recursion Limit
**Pros:** Simple one-line change
**Cons:** Doesn't fix root cause; just postpones the error

### Alternative 2: Remove Hallucination Checking
**Pros:** Eliminates one loop source
**Cons:** Degrades answer quality; hallucinations will slip through

### Alternative 3: Force Exit After Fixed Steps
**Pros:** Guaranteed termination
**Cons:** May cut off valid long-running queries

**Selected Approach (Multi-Layered)** combines all benefits:
- Increases limit for legitimate complex queries
- Adds counters to prevent infinite loops
- Gracefully degrades when limits hit
- Maintains quality checks (hallucination, usefulness)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Fallback messages confuse users | Medium | Low | Clear, helpful messaging with troubleshooting steps |
| Limits too restrictive for valid queries | Low | Medium | Make configurable; default values tested to be reasonable |
| Regeneration counter breaks existing workflows | Low | High | Thoroughly test all workflow paths |
| Settings not loaded correctly | Low | High | Add validation and tests for settings |
| State size increases (new field) | Low | Low | One integer field is negligible |

---

## Implementation Checklist

- [ ] Add `regeneration_count` to GraphState in state.py
- [ ] Add `MAX_REGENERATIONS` and `WORKFLOW_RECURSION_LIMIT` to settings.py
- [ ] Update `generate` node to increment regeneration_count
- [ ] Update `check_hallucination_and_usefulness` router with limit checks
- [ ] Add recursion_limit config to workflow.compile()
- [ ] Enhance error handling in workflow.run() method
- [ ] Initialize regeneration_count=0 in run() and stream() methods
- [ ] Update documentation (README.md or CLAUDE.md)
- [ ] Write unit tests for router limit logic
- [ ] Write integration test for recursion limit error recovery
- [ ] Test with intentionally failing scenarios
- [ ] Verify logging shows helpful troubleshooting info

---

## Estimated Impact

- **Code Changes:** ~150 lines modified across 5 files
- **Breaking Changes:** None (only additive changes)
- **Performance Impact:** Negligible (one integer counter)
- **User Experience:** Significantly improved (no crashes)
