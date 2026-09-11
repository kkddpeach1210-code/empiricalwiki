---
description: Parse review comments → atomize concerns (Rvx-Cy) → map to wiki claims → check evidence → Review LLM stress-test → generate rebuttal
argument-hint: <review-file-or-path> [--paper-slug <slug>] [--venue <venue>] [--stress-test] [--format formal|rich]
---

# /rebuttal

> Parse review comments, atomize each concern (Rvx-Cy numbering) and map it to a wiki claim,
> check whether evidence is sufficient (tracing back to wiki experiments),
> simulate reviewer follow-up questions with Review LLM (stress-test, scored 1-5), and generate
> a formal plain-text rebuttal and a rich-text rebuttal.
> Safety checks ensure no fabrication, no overpromise, full coverage.

## Inputs

- `review`: source of review comments, one of:
  - file path (e.g. `raw/reviews/reviewer1.txt`, `raw/reviews/meta-review.md`)
  - multiple file paths (comma-separated: `raw/reviews/R1.txt,raw/reviews/R2.txt,raw/reviews/R3.txt`)
  - directly pasted review text
- `--paper-slug` (optional): slug of the associated paper in wiki/outputs/, used to locate PAPER_PLAN
- `--venue` (optional): target conference/journal (ICLR / NeurIPS / ICML / ACL / CVPR); affects rebuttal format and word limits
- `--stress-test` (optional, enabled by default): Review LLM simulates reviewer follow-up; disable with `--no-stress-test`
- `--format` (optional, default `formal`): output format
  - `formal`: formal plain-text rebuttal (suitable for pasting directly into submission system)
  - `rich`: rich-text version (with wiki [[links]], detailed analysis, improvement plan)

## Outputs

- **wiki/outputs/rebuttal-{slug}.md** — rich-text rebuttal (with [[wikilinks]], evidence tracing, analysis tables)
- **wiki/outputs/rebuttal-{slug}.txt** — formal rebuttal (plain text, suitable for pasting into submission system)
- **wiki/claims/*.md** — if a concern exposes an evidence gap, append a suggestion to `## Open questions`
- **wiki/log.md** — append log entry

## Wiki Interaction

### Reads
- `wiki/claims/*.md` — map concerns to claims, check evidence sufficiency
- `wiki/experiments/*.md` — find experiment results supporting claims
- `wiki/papers/*.md` — find citation context for referenced papers
- `wiki/concepts/*.md` — understand the conceptual background of method-related concerns
- `wiki/ideas/*.md` — find the motivation and pilot results for ideas
- `wiki/outputs/PAPER_PLAN.md` — understand paper structure (from /paper-plan, if --paper-slug provided)
- `wiki/graph/context_brief.md` — global context
- `wiki/graph/edges.jsonl` — claim-experiment-paper relationships
- `.claude/skills/shared-references/cross-model-review.md` — Review LLM stress-test independence

### Writes
- `wiki/outputs/rebuttal-{slug}.md` — rich-text version
- `wiki/outputs/rebuttal-{slug}.txt` — formal plain-text version
- `wiki/claims/*.md` — append reviewer-identified gaps to `## Open questions` (do not directly modify confidence/status; add suggestions only)
- `wiki/log.md` — append log entry

### Graph edges created
- None (rebuttal is a query operation; does not modify the knowledge graph)

## Workflow

**Precondition**:
1. Confirm working directory is the wiki project root (containing `wiki/`, `raw/`, `tools/`)
2. Read `cross-model-review.md` to confirm stress-test independence principle
3. Generate slug: `python3 tools/research_wiki.py slug "{paper-slug}-rebuttal"`

### Step 1: Parse Review Comments

1. **Read review text**:
   - If file path(s): read all specified files
   - If direct text: use directly
   - Merge multiple reviewers' comments, annotated by source (Reviewer 1/2/3/Meta)

2. **Identify structure**:
   - Extract each reviewer's: overall score (Accept/Reject/Borderline), confidence, summary, Strengths, Weaknesses, questions
   - If the format is non-standard (plain text), use LLM to parse into structured format

3. **Output**: structured comments for each reviewer

### Step 2: Atomize Concerns

Split each weakness and question into independent atomic concerns:

1. **Splitting rules**:
   - A single weakness may be a compound sentence containing multiple independent concerns ("the method lacks ablation experiments and also does not compare with X" → split into 2 concerns)
   - Assign each atomic concern an ID in `Rvx-Cy` format (Rv1-C1 = Reviewer 1, Concern 1; Rv1-C2 = Reviewer 1, Concern 2)
   - Retain reviewer number to ensure traceability back to the original comment

2. **Classify each concern**:
   - **evidence**: factual questions about experimental data or result interpretation
   - **method**: methodological questions about method design or algorithmic correctness
   - **missing**: missing experiments/analysis/comparisons/citations
   - **clarity**: unclear expression, symbol confusion, figure issues
   - **scope**: insufficient contribution, applicability questions
   - **novelty**: overlap with existing work, insufficient innovation
   - **minor**: formatting, typos, and other small issues

3. **Assess severity**: critical / major / minor

4. **Output**: atomized concern list, each containing {id (Rvx-Cy), reviewer, type, severity, text}

### Step 3: Map Concerns to Wiki Claims

For each concern:

1. **Find associated claim**:
   - Extract keywords from concern text
   - Search `wiki/claims/*.md` for matching claims
   - Read `wiki/graph/edges.jsonl` to find claim-experiment relationships
   - If no direct match is found: annotate as "unmapped" (no direct claim correspondence)

2. **Check Evidence Status**:
   - Read the claim's evidence list
   - Count strong/moderate/weak evidence
   - Find results of associated experiments
   - **Judgment**:
     - Sufficient: strong >= 1 or moderate >= 2
     - Partial: evidence exists but insufficient strength
     - Insufficient: no evidence or only weak evidence
     - Contradicted: evidence of invalidates type exists

3. **Output**:

| Concern ID | Reviewer | Type | Severity | Claim mapped | Evidence Status | Strategy |
|------------|----------|------|----------|--------------|-----------------|----------|
| Rv1-C1 | R1 | method | critical | [[claim-slug]] | sufficient | A |
| Rv1-C2 | R1 | missing | major | [[claim-slug]] | insufficient | B |
| Rv2-C1 | R2 | novelty | major | unmapped | — | D |

### Step 4: Draft Rebuttal Responses

Draft a response for each concern according to its strategy:

**Strategy A — Evidence sufficient (respond directly):**
- Cite specific experiment results and data (annotate source, ensure traceability to wiki/experiments/)
- Point to evidence in the wiki (convert to paper citations)
- If the concern is based on a misunderstanding: politely clarify, point to the relevant Section in the paper

**Strategy B — Evidence insufficient (acknowledge + concrete plan):**
- Honestly acknowledge that current evidence is not sufficient
- Propose a concrete supplementary experiment plan (can link to /exp-design)
- State a specific timeline and resource requirements
- Do not use vague commitments; only commit to concrete executable supplementary experiments

**Strategy C — Clarity issue (commit to revision):**
- Acknowledge the unclear expression
- Provide the improved description (show the revised text directly in the rebuttal)
- List specific Paper Edit plans

**Strategy D — Scope/Novelty challenge (argue):**
- Highlight essential differences from existing work
- Cite novelty-check results (if available)
- Point out differences the reviewer may have overlooked

**Format for each response**:
```markdown
**[Rvx-Cy]** {concern summary}

{response text, 2-5 sentences, annotated sources for traceability}
```

**Safety checks (per response)**:
- [ ] No fabrication: do not fabricate data or experiment results
- [ ] No overpromise: only commit to specific executable supplementary experiments
- [ ] Cited data is recorded in wiki/experiments/
- [ ] If claim is challenged/deprecated, do not pretend it is supported

### Step 5: Review LLM Stress-Test

**Follow cross-model-review.md**: do not send Claude's rebuttal strategy analysis to Review LLM.

If `--stress-test` is enabled (default):

```
mcp__llm-review__chat:
  system: "You are a critical reviewer who has just read a rebuttal to your review
           comments. You are skeptical and will push back on weak responses.
           For each rebuttal response, assess on a scale of 1-5:
           1 = unconvincing (deflection or fabrication suspected)
           2 = weak (vague, no concrete evidence)
           3 = acceptable (addresses concern but could be stronger)
           4 = strong (concrete evidence, clear reasoning)
           5 = fully convincing (compelling evidence, thorough response)
           Also check for overpromise: are commitments specific and feasible?
           Provide a follow-up question for any response scoring <= 3."
  message: |
    ## Original Review Concerns
    {atomic concerns list with Rvx-Cy IDs}

    ## Author Rebuttal
    {drafted rebuttal responses}

    ## Please assess each response (score 1-5) and provide follow-up questions.
```

**Handle Review LLM feedback**:
- **Score 4-5 (convincing)**: keep original response
- **Score 3 (acceptable)**: strengthen response, add details suggested by Review LLM
- **Score 1-2 (unconvincing/weak)**: rewrite response, consider switching strategy (A→B, acknowledge insufficiency)

**Second round (if any responses scored <= 2)**:

```
mcp__llm-review__chat-reply:
  threadId: {previous thread}
  message: |
    We've revised the following responses:
    {revised responses}
    Please re-assess (score 1-5).
```

Maximum 2 rounds of stress-test. Handle follow-up questions and update responses.

### Step 6: Format Output + Safety Check

**6a. Format formal rebuttal-{slug}.txt** (plain text, suitable for submission system):

```
We thank the reviewers for their constructive feedback. We address each concern below.

Reviewer 1:

[Rv1-C1] {concern summary}
{response}

[Rv1-C2] {concern summary}
{response}

Reviewer 2:
...

Summary of Revisions:
- {bulleted list of planned changes}

Additional Experiments (if applicable):
- {new experiments committed to, with timeline}
```

**6b. Format rich-text rebuttal-{slug}.md**:

```markdown
# Rebuttal Analysis: {paper title}

## Coverage Summary
| Concern ID | Type | Severity | Claim | Evidence Status | Review LLM Score | Strategy |
|------------|------|----------|-------|-----------------|------------|----------|
| Rv1-C1 | method | critical | [[claim-slug]] | sufficient | 4/5 | A |
| Rv1-C2 | missing | major | [[claim-slug]] | insufficient | 3/5 | B |

## Responses
### Reviewer 1
**[Rv1-C1]** ...
**[Rv1-C2]** ...

## Evidence Gap Analysis
| Claim | Confidence | Gap | Needed |
|-------|-----------|-----|--------|
| [[claim-slug]] | 0.5 | No ablation on dataset X | Run ablation experiment |

## Action Items

### Paper Edits
| Section | Change | Reason |
|---------|--------|--------|
| Section 3.2 | Clarify notation | Rv1-C3 clarity concern |

### Wiki Updates
| Page | Update | Reason |
|------|--------|--------|
| claims/{slug} | Add open question | Rv2-C1 evidence gap |

### Suggested Experiments
| Experiment | Target Claim | Suggested by |
|-----------|-------------|--------------|
| ablation-dataset-x | [[claim-slug]] | Rv1-C2 |

→ Run `/exp-design ablation-dataset-x` to design follow-up

## Review LLM Stress-Test Summary
- Average score: {N}/5
- Scores 4-5: {N}/{total}
- Scores 1-3: {N}/{total} (all revised)

## Safety Checklist
- [x] No fabrication: all cited data exists in wiki/experiments
- [x] No overpromise: all committed experiments are specific and feasible
- [x] Full coverage: {N}/{N} concerns addressed (no omissions)
- [x] Challenged claims not presented as supported
```

**6c. Final safety check**:
- **Full coverage**: confirm every concern has a response (no omissions)
- **No fabrication**: every cited data point is recorded in wiki/experiments/ (traceable)
- **No overpromise**: supplementary experiment commitments are specific and feasible
- **Honesty on weak claims**: if claim confidence < 0.4, do not pretend evidence is sufficient

**6d. Update wiki**:
- For claims with evidence gaps: append reviewer-identified gaps to `## Open questions` in `wiki/claims/{slug}.md`
- Append log:
  ```bash
  python3 tools/research_wiki.py log wiki/ \
    "rebuttal | {N} concerns addressed | {M} evidence gaps | stress-test avg: {score}/5"
  ```

## Constraints

- **No fabrication**: never fabricate experiment data or results. Every cited number must be traceable to wiki/experiments/ with source annotated
- **No overpromise**: only commit to specific executable supplementary experiments. Use "we will run ablation on X with setup Y" not "we will investigate"
- **Full coverage**: every reviewer concern (Rvx-Cy) must have a response; omissions block output
- **Evidence traceability**: every piece of evidence cited in a response must be traceable to a wiki page with source slug annotated
- **Do not directly modify wiki claims**: rebuttal only appends suggestions to claims' Open questions; do not modify confidence/status
- **Review LLM independence**: during stress-test, follow cross-model-review.md; do not reveal response strategy to Review LLM
- **Concern ID format**: strictly use Rvx-Cy format (Rv1-C1, Rv1-C2, Rv2-C1) to ensure traceability
- **Specific commitments**: all revision commitments and experiment plans must be specific (specific Section, specific dataset, explicit metric)
- **Output to wiki/outputs/**: rebuttal files are stored uniformly in the wiki/outputs/ directory

## Error Handling

- **Review file not found**: report error, list available files under raw/reviews/
- **Review format cannot be parsed**: fall back to plain-text processing; use LLM to extract concerns; annotate in report
- **Concern cannot be mapped to a claim (unmapped)**: annotate as "unmapped"; still respond (based on paper content rather than wiki claim)
- **Review LLM stress-test unavailable**: skip Step 5; annotate in report "stress-test skipped: Review LLM unavailable"
- **Evidence severely insufficient**: if >50% of concerns have insufficient evidence, warn the user and suggest supplementing experiments first
- **Wiki empty**: warn that wiki knowledge base is empty; suggest running /ingest to populate claims and experiments
- **All responses scored 1-2 by Review LLM**: halt output, report requires re-analysis, suggest supplementing experiments first

## Dependencies

### Tools（via Bash）
- `python3 tools/research_wiki.py slug "{title}"` — generate rebuttal slug
- `python3 tools/research_wiki.py log wiki/ "<message>"` — append log entry

### MCP Servers
- `mcp__llm-review__chat` — Step 5 stress-test first round
- `mcp__llm-review__chat-reply` — Step 5 stress-test subsequent rounds

### Claude Code Native
- `Read` — read review comments, wiki pages, shared references
- `Write` — write rebuttal-{slug}.md, rebuttal-{slug}.txt
- `Glob` — find claims, experiments
- `Grep` — search wiki for concern keywords

### Shared References
- `.claude/skills/shared-references/cross-model-review.md` — Review LLM stress-test independence principle

### Suggested follow-up skills
- `/exp-design` — design supplementary experiments for concerns with insufficient evidence
- `/paper-draft` — prepare revised paper (based on Paper Edits checklist)
