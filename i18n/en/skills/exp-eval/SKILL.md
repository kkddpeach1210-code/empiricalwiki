---
description: Experiment verdict gate — Review LLM independently judges results → 4 verdict paths → auto-update claims confidence, ideas status, graph edges
argument-hint: <experiment-slug> [--auto]
---

# /exp-eval

> Convert completed experiment results into wiki knowledge updates.
> Review LLM acts as an impartial judge (following cross-model-review), independently evaluating how experimental results affect the target claim.
> Four verdict paths: supported → claim↑ + idea validated / partially_supported → supplementary experiments /
> not_supported → claim↓ + idea failed / inconclusive → debug.
> Auto-updates claims confidence and evidence, ideas status, and graph edges.

## Inputs

- `experiment`: slug from wiki/experiments/ (status must be `completed`)
- `--auto` (optional): automatic mode — do not pause for user confirmation before wiki updates (used when called by /research)

## Outputs

- `wiki/claims/{slug}.md` — updated confidence, status, evidence list
- `wiki/ideas/{slug}.md` — updated status (validated/failed), pilot_result, failure_reason
- `wiki/experiments/{slug}.md` — `## Claim updates` section filled in
- `wiki/graph/edges.jsonl` — new supports/invalidates edges added
- `wiki/graph/context_brief.md` — rebuilt
- `wiki/graph/open_questions.md` — rebuilt
- `wiki/log.md` — appended log entry
- **VERDICT_REPORT** (printed to terminal) — verdict result, wiki change summary, next step suggestions

## Wiki Interaction

### Reads
- `wiki/experiments/{slug}.md` — experiment results: outcome, key_result, metrics, full Results section
- `wiki/claims/{target-claim}.md` — target claim current state: status, confidence, evidence list
- `wiki/ideas/{linked-idea}.md` — linked idea current state
- `wiki/experiments/*.md` — other experiments on the same claim (aggregate assessment)
- `wiki/graph/context_brief.md` — global context
- `.claude/skills/shared-references/cross-model-review.md` — reviewer independence principle

### Writes
- `wiki/claims/{target-claim}.md` — update status, confidence, evidence, date_updated
- `wiki/ideas/{linked-idea}.md` — update status, pilot_result, failure_reason, date_resolved
- `wiki/experiments/{slug}.md` — fill in `## Claim updates` section
- `wiki/graph/edges.jsonl` — add supports or invalidates edges
- `wiki/graph/context_brief.md` — rebuild
- `wiki/graph/open_questions.md` — rebuild
- `wiki/log.md` — append operation log

### Graph edges created
- `supports`: experiment → claim (experiment supports the claim) — verdict = supported or partially_supported
- `invalidates`: experiment → claim (experiment refutes the claim) — verdict = not_supported

## Workflow

**Precondition**:
1. Confirm working directory is the wiki project root (directory containing `wiki/`, `raw/`, `tools/`)
2. Confirm experiment status == `completed` (incomplete experiments cannot be evaluated)

### Step 1: Load Context

1. **Read experiment page** `wiki/experiments/{slug}.md`:
   - outcome (succeeded/failed/inconclusive)
   - key_result
   - target_claim slug
   - linked_idea slug
   - metrics and full Results section
   - hypothesis

2. **Read target claim** `wiki/claims/{target-claim}.md`:
   - Current status and confidence
   - Existing evidence list
   - Conditions and scope

3. **Read linked idea** `wiki/ideas/{linked-idea}.md` (if it exists):
   - Current status
   - Hypothesis

4. **Load other experiments on the same claim**:
   - Glob: `wiki/experiments/*.md`, filter target_claim == same claim
   - Summarize existing experiment results (for aggregate claim confidence assessment)

5. **Read global context**:
   - `wiki/graph/context_brief.md`

6. **Read cross-model-review.md**: confirm Review LLM independence principle

### Step 2: Review LLM Verdict (Cross-Model Verdict)

**Follow cross-model-review.md**: do not send Claude's pre-judgment to Review LLM.

```
mcp__llm-review__chat:
  system: "You are an impartial scientific judge evaluating whether experimental
           results support or refute a research claim. Be rigorous and objective.
           Consider: statistical significance, effect size, experimental validity,
           potential confounds, and whether the results generalize beyond the
           specific setup tested."
  message: |
    ## Claim Under Test
    Title: {claim title}
    Statement: {claim statement from ## Statement section}
    Current status: {status}
    Current confidence: {confidence}
    Conditions: {conditions and scope}

    ## Experiment
    Title: {experiment title}
    Hypothesis: {hypothesis}
    Setup: {model, dataset, hardware, framework}
    Metrics: {metrics list}

    ## Results
    {full Results section from experiment page}

    ## Key Finding
    {key_result}

    ## Other Experiments on This Claim
    {summary of other experiments' outcomes on the same claim, if any}

    ## Your Task
    Provide your verdict:
    1. **Verdict**: One of: supported / partially_supported / not_supported / inconclusive
    2. **Confidence adjustment**: Suggest new confidence value (0.0-1.0) with reasoning
    3. **Evidence strength**: weak / moderate / strong
    4. **Key reasoning**: 2-3 sentences explaining your verdict
    5. **Concerns**: Any methodological concerns or limitations
    6. **Suggested next steps**: What would strengthen or clarify this result?
```

Record Review LLM's verdict.

### Step 3: Claude Synthesis

1. **Form Claude's independent verdict** (after reading Review LLM's verdict, Claude also analyzes independently):
   - Based on experimental results, claim context, and aggregate evidence from other experiments
   - Form Claude's own verdict and confidence suggestion

2. **Synthesize both verdicts** (follow cross-model-review.md composing rules):
   - **Both agree** (same verdict): use that verdict, average the confidence, high certainty
   - **Both disagree**:
     - Explicitly flag the disagreement
     - Take the more conservative verdict (supported > partially_supported > not_supported)
     - Use the lower confidence value
     - Detail the disagreement reason in the report
   - **Fatal findings take priority**: if either party finds a methodological issue (data leakage, unfair comparison), that finding takes precedence

3. **Determine final verdict**: verdict + new_confidence + evidence_strength

### Step 4: Update Wiki Based on Verdict

**If `--auto` is not set**: display verdict and planned changes first, wait for user confirmation.

#### Path A: SUPPORTED (experiment supports claim)

1. **Update claim**:
   - confidence: ↑ adjust to new value (typically +0.1~0.3)
   - status: adjust based on new confidence
     - confidence >= 0.7 → `supported`
     - confidence 0.4–0.7 → `weakly_supported`
   - evidence: append new entry `{source: experiment-slug, type: supports, strength: strong/moderate, detail: key_result}`
   - date_updated: today's date

2. **Update idea** (if it exists and status is in_progress/tested):
   - If all linked claims are supported/weakly_supported:
     - status: `validated`
     - pilot_result: key_result summary
     - date_resolved: today's date

3. **Add graph edge**:
   ```bash
   python3 tools/research_wiki.py add-edge wiki/ \
     --from "experiments/{slug}" --to "claims/{target-claim}" \
     --type supports --evidence "{key_result}"
   ```

4. **Suggest next steps**: `/paper-plan` or continue ablation/robustness experiments

#### Path B: PARTIALLY_SUPPORTED (partial support)

1. **Update claim**:
   - confidence: minor adjustment (+0.05~0.15)
   - evidence: append `{type: supports, strength: weak, detail: ...}`
   - date_updated: today's date

2. **Add graph edge**:
   ```bash
   python3 tools/research_wiki.py add-edge wiki/ \
     --from "experiments/{slug}" --to "claims/{target-claim}" \
     --type supports --evidence "Partially supported: {limitation}"
   ```

3. **Suggest supplementary experiments**:
   - Specify what evidence is missing
   - Suggest using `/exp-design` to design supplementary experiments
   - If Review LLM-flagged concerns are addressable by experiment, suggest concrete experiment direction

4. **Idea status unchanged**: keep in_progress, wait for more evidence

#### Path C: NOT_SUPPORTED (experiment does not support claim)

1. **Update claim**:
   - confidence: ↓ significantly lower (typically -0.2~0.4)
   - status: if confidence < 0.3 → `challenged`
   - evidence: append `{type: invalidates, strength: strong/moderate, detail: ...}`
   - date_updated: today's date

2. **Update idea** (if it exists):
   - status: `failed`
   - failure_reason: specific reason for failure (extracted from experiment results and Review LLM analysis)
   - date_resolved: today's date
   - Note: failure_reason is anti-repetition memory — must be written clearly, explaining why it failed

3. **Add graph edge**:
   ```bash
   python3 tools/research_wiki.py add-edge wiki/ \
     --from "experiments/{slug}" --to "claims/{target-claim}" \
     --type invalidates --evidence "{failure_reason}"
   ```

4. **Suggest next steps**:
   - Analyze the failure reason
   - Consider pivoting (new idea addressing the same gap while avoiding the known failure)
   - Suggest `/ideate` to generate alternatives

#### Path D: INCONCLUSIVE (results are uncertain)

1. **Do not modify claim status/confidence**: insufficient evidence to make a judgment

2. **Update experiment page**: outcome is already inconclusive (set by /exp-run)

3. **Suggest debugging**:
   - Data issue? Implementation bug? Wrong metric?
   - Too much variance? More seeds needed?
   - Experiment setup not aligned with claim?

4. **Idea status unchanged**: keep current status

#### All Paths (common steps)

1. **Fill in `## Claim updates` section of the experiment page**:
   ```markdown
   ## Claim updates
   - **Verdict**: {supported/partially_supported/not_supported/inconclusive}
   - **Claim**: [[{target-claim}]] confidence {old} → {new}
   - **Judge agreement**: {Claude and Review LLM agreed / disagreed on ...}
   - **Date**: YYYY-MM-DD
   ```

2. **Update index.md** (if claim status changed)

3. **Rebuild derived data**:
   ```bash
   python3 tools/research_wiki.py rebuild-context-brief wiki/
   python3 tools/research_wiki.py rebuild-open-questions wiki/
   ```

4. **Append log**:
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "exp-eval | {slug} → {target-claim} | verdict: {verdict} | confidence: {old}→{new}"
   ```

5. **Print VERDICT_REPORT to terminal**:
   ```markdown
   # Verdict Report: {experiment title}

   ## Verdict: {SUPPORTED / PARTIALLY_SUPPORTED / NOT_SUPPORTED / INCONCLUSIVE}

   ## Judge Assessment
   | | Claude | Review LLM | Final |
   |---|-------|------|-------|
   | Verdict | {verdict} | {verdict} | {verdict} |
   | Confidence | {value} | {value} | {value} |
   | Evidence strength | {strength} | {strength} | {strength} |

   ## Key Reasoning
   {2-3 sentences from Review LLM + Claude synthesis}

   ## Wiki Changes
   | Entity | Field | Before | After |
   |--------|-------|--------|-------|
   | claims/{slug} | confidence | {old} | {new} |
   | claims/{slug} | status | {old} | {new} |
   | ideas/{slug} | status | {old} | {new} |

   ## Graph Edges Added
   - experiments/{slug} → claims/{target} (supports/invalidates)

   ## Concerns
   {methodological concerns from Review LLM}

   ## Next Steps
   - {path-specific suggestions}

   ## Wiki Growth
   | Metric | Before | After | Delta |
   |--------|--------|-------|-------|
   | Claims updated | — | — | {N} |
   | Edges | {before} | {after} | +{delta} |
   | Maturity | {level} | {level} | {unchanged/upgraded} |
   (Data from comparing `python3 tools/research_wiki.py maturity wiki/ --json` calls at the start of Step 1 and end of Step 4.)
   ```

## Constraints

- **Only process completed experiments**: experiments with status != completed are refused; prompt user to use /exp-run first
- **Reviewer independence**: strictly follow cross-model-review.md — do not send Claude's pre-judgment to Review LLM
- **Confidence range 0.0–1.0**: updated confidence must not exceed this range
- **failure_reason must be specific**: the not_supported path's failure_reason cannot be vague (e.g. "experiment failed") — must state the concrete reason
- **Do not delete claims**: even when not_supported, only challenge or lower confidence; do not delete the claim page. In extreme cases (multiple consistent refutations, confidence → 0), set status to deprecated rather than deleting
- **Graph edges via tools/research_wiki.py**: do not manually edit edges.jsonl
- **Conservative principle**: when Claude and Review LLM verdicts disagree, use the more conservative verdict
- **Idea status advances only forward**: proposed → in_progress → tested → validated/failed, irreversible
- **Assess claim using all experiments**: consider not just the current experiment but also other experiments on the same claim

## Error Handling

- **Experiment not found**: prompt user to check slug, list candidates in wiki/experiments/ with status=completed
- **Experiment not completed**: report status, suggest running `/exp-run {slug}` or `/exp-run {slug} --check`
- **Target claim does not exist**: create new claim page (status: proposed, confidence: 0.3), note "auto-created by exp-eval"
- **Linked idea does not exist**: skip idea update, only update claim, note in report
- **Review LLM unavailable**: fall back to Claude single-model verdict, note "single-model verdict, cross-model verification unavailable" in report, suggest user confirm later
- **Claim was modified by another experiment**: read the latest state, make adjustments based on current confidence (do not overwrite other experiments' contributions)
- **Results data missing**: if the experiment page's Results section is empty, prompt user to run `/exp-run {slug} --check` first

## Dependencies

### Tools（via Bash）
- `python3 tools/research_wiki.py add-edge wiki/ ...` — add graph edge
- `python3 tools/research_wiki.py rebuild-context-brief wiki/` — rebuild query_pack
- `python3 tools/research_wiki.py rebuild-open-questions wiki/` — rebuild gap_map
- `python3 tools/research_wiki.py log wiki/ "<message>"` — append log

### MCP Servers
- `mcp__llm-review__chat` — Step 2 Review LLM independent verdict

### Claude Code Native
- `Read` — read wiki pages
- `Glob` — find other experiments on the same claim
- `Edit` — update wiki pages

### Shared References
- `.claude/skills/shared-references/cross-model-review.md` — Review LLM independence principle (required reading)

### Called by
- `/research` Stage 4 (verdict and iteration stage)
- User directly
