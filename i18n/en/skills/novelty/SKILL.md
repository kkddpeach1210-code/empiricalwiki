---
description: Multi-source novelty verification — WebSearch + Semantic Scholar + wiki + Review LLM cross-verify — outputs novelty score and recommendations
argument-hint: <idea-description-or-slug>
---

# /novelty

> Verify the novelty of a research idea or method using multiple sources. Searches WebSearch,
> Semantic Scholar, existing wiki work, and arXiv recent preprints, then Review LLM cross-verifies.
> Outputs a novelty score (1-5), closest prior work, differentiation points, and next-step recommendations.
> Can be used standalone or called by /ideate Phase 4.

## Inputs

- `target`: one of the following:
  - free-text description of the idea (a paragraph or a few sentences)
  - slug of an ideas/ page in the wiki (e.g. `sparse-lora-for-edge-devices`)
  - paper title or arXiv URL (check novelty of that paper's method)
- `--quick`: fast mode, skip Review LLM cross-verify (Step 3), search only
- `--verbose`: output full search results, not just summaries

## Outputs

- **Novelty Report** (output to terminal, not written to wiki):
  - Novelty Score (1-5)
  - List of closest prior work (top 3-5)
  - Differentiation points versus each prior work
  - Review LLM cross-verify assessment (unless --quick)
  - Recommended action: proceed / modify / abandon
- This skill is a **read-only query** — it does not modify any wiki content

## Wiki Interaction

### Reads
- `wiki/papers/*.md` — search existing papers for similar methods
- `wiki/concepts/*.md` — check concept overlap
- `wiki/ideas/*.md` — check for duplication with existing ideas (especially `failure_reason` of failed ideas)
- `wiki/claims/*.md` — check the current status of claims the idea depends on
- `wiki/graph/context_brief.md` — global context to assist search

### Writes
- **None**. Novelty check is a pure query operation; it does not modify the wiki.

### Graph edges created
- **None**.

## Workflow

**Precondition**: confirm working directory is the wiki project root (containing `wiki/`, `raw/`, `tools/`).

### Step 1: Extract Method Signature

1. **If target is a slug**: read `wiki/ideas/{slug}.md`, extract title, Hypothesis, Approach sketch
2. **If target is free text**: use directly
3. **If target is an arXiv URL**: download the abstract, extract method description
4. Extract the "method signature" from the target — the core elements of the method:
   - **What**: what it does (task / goal)
   - **How**: the method used (technical approach)
   - **Why novel**: claimed innovation
5. Generate 3-5 core keywords for subsequent searches

### Step 2: Multi-Source Search

Execute the following searches in parallel (use Agent tool for concurrency):

**Source A — Web Search (5+ queries):**
1. Direct query: `"<method-name>" + "<task>"` — exact phrase search
2. Component query: `<component-1> + <component-2> + <domain>` — component combination search
3. Survey query: `"survey" OR "review" + <task-area> + 2024 2025`
4. Competitor query: `<alternative-approach> + <same-task>`
5. Recent query: `<method-keywords> + arXiv + 2025 2026`

**Source B — Semantic Scholar + DeepXiv:**
```bash
python3 tools/fetch_s2.py search "<method-keywords>" --limit 20
python3 tools/fetch_deepxiv.py search "<method-keywords>" --mode hybrid --limit 20
```
Merge results from both sources (deduplicate by arxiv_id). DeepXiv's hybrid semantic search finds semantically similar work that S2 keyword search may miss.
- Fetch details and TLDR for top 5 results:
```bash
python3 tools/fetch_s2.py paper <s2_id>
python3 tools/fetch_deepxiv.py brief <arxiv_id>
```
Use DeepXiv brief TLDRs to quickly judge method similarity.
**If DeepXiv is unavailable**: fall back to S2 search only (original behavior).

**Source C — Wiki Internal Search:**
1. Scan Key idea and Method sections of all pages in `wiki/papers/`
2. Scan Definition and Variants sections of `wiki/concepts/`
3. Scan all content in `wiki/ideas/`, with special attention to:
   - ideas with status = failed and their failure_reason (anti-repetition)
   - ideas with status = proposed/in_progress (avoid internal duplication)
4. Read `wiki/graph/context_brief.md` for global perspective

**Source D — Recent arXiv Preprints:**
- Use WebSearch: `site:arxiv.org <method-keywords> 2025 2026`

### Step 3: Review LLM Cross-Verify

(Skip if `--quick`)

Submit the following to Review LLM for independent assessment:

```
mcp__llm-review__chat:
  system: "You are a senior ML researcher assessing the novelty of a proposed method.
           Be rigorous: if the method is essentially a recombination of known techniques
           with minor changes, score it low. Only score 4-5 if there is a genuinely new
           insight or formulation."
  message: |
    ## Proposed Method
    {method signature from Step 1}

    ## Existing Similar Work Found
    {top 5 similar works from Step 2, with title + one-line summary}

    ## Questions
    1. Is this method genuinely novel, or a minor variation of existing work?
    2. What is the closest existing work and what's the real difference?
    3. Novelty score 1-5 with justification.
    4. If score <= 2, what modification could increase novelty?
```

### Step 4: Generate Novelty Report

Synthesize Step 2 search results and Step 3 Review LLM assessment into a structured report:

```markdown
# Novelty Report: {idea title}

## Score: {1-5}/5 — {label}

| Score | Label | Meaning |
|-------|-------|---------|
| 1 | Published | Highly similar published work exists |
| 2 | Very Similar | Very similar method exists, only minor differences |
| 3 | Incremental | Clear incremental contribution over existing work |
| 4 | Novel Combination | Creatively combines existing techniques, producing new insight |
| 5 | Fundamentally New | Proposes an entirely new paradigm or formulation |

## Closest Prior Work

1. **{title}** ({year}) — {one-sentence description of the similarity}
   - Difference: {key distinction between this method and the prior work}
   - Wiki link: [[slug]] (if it exists)
2. ...

## Review LLM Assessment
{summary of Review LLM's independent judgment}

## Anti-repetition Check
- Failed ideas in wiki: {list relevant failed ideas with failure_reason}
- In-progress ideas in wiki: {list potentially overlapping ideas}

## Recommendation
- **{proceed / modify / abandon}**
- Rationale: {one paragraph}
- If modify: suggested differentiation directions: {specific suggestions}
```

**Scoring rules (composite judgment):**
- Take the lower of Claude's search-based score and Review LLM's score (conservative principle)
- If wiki contains a failed idea whose failure_reason overlaps with this idea → lower score by 1
- If wiki contains a highly overlapping in_progress idea → mark as abandon (internal duplication)

## Constraints

- **Do not modify the wiki**: novelty check is a pure query; all results are output to terminal only
- **Conservative scoring**: underestimate novelty rather than overestimate to avoid wasting effort on known work
- **Must check failed ideas**: ideas with status=failed in wiki/ideas/ are important anti-repetition signals
- **Search coverage**: at least 5 distinct WebSearch queries + Semantic Scholar + wiki internal search
- **Review LLM independence**: do not include Claude's own novelty judgment when submitting to Review LLM; let Review LLM assess independently
- **Cite real sources**: all prior work listed in the report must be real (returned by WebSearch/S2); do not fabricate

## Error Handling

- **WebSearch unavailable**: skip Sources A and D, rely only on S2 + wiki search; note limited coverage in report
- **Semantic Scholar API unavailable**: skip S2 portion, use DeepXiv + WebSearch as compensation
- **DeepXiv API unavailable**: skip DeepXiv portion, rely on S2 + WebSearch (fall back to original behavior)
- **Review LLM unavailable**: skip Step 3; annotate report with "Review LLM cross-verify unavailable, single-model assessment only"
- **Wiki empty**: proceed with external searches normally; annotate wiki internal search section with "wiki empty"
- **idea slug not found**: prompt user to check the slug, list available slugs in wiki/ideas/

## Dependencies

### Tools（via Bash）
- `python3 tools/fetch_s2.py search "<query>" --limit 20` — Semantic Scholar keyword search
- `python3 tools/fetch_s2.py paper <s2_id>` — fetch paper details
- `python3 tools/fetch_deepxiv.py search "<query>" --mode hybrid --limit 20` — DeepXiv semantic search
- `python3 tools/fetch_deepxiv.py brief <arxiv_id>` — fetch paper TLDR for similarity judgment

### MCP Servers
- `mcp__llm-review__chat` — Review LLM cross-verify (Step 3)

### Claude Code Native
- `WebSearch` — multi-query web search (Step 2 Sources A + D)
- `Agent` tool — parallel execution of multi-source search (Step 2)

### Shared References
- `.claude/skills/shared-references/cross-model-review.md` (created in Phase 2, Review LLM independence principle)
