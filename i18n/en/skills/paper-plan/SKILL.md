---
description: Compile a paper outline from the claim graph — evidence map → narrative structure → section plan + figure plan + citation plan, Review LLM review mandatory
argument-hint: <claim-slugs...> --venue <ICLR|NeurIPS|ICML|ACL|CVPR|IEEE> [--title <working-title>]
---

# /paper-plan

> Compile a paper outline from the wiki's claim graph.
> Input target claims (status: supported or weakly_supported), specify the target venue,
> compile an evidence map from the wiki → determine narrative structure → generate a section outline + figure plan + citation plan.
> Review LLM review is a mandatory step (acting as area chair to assess outline persuasiveness).
> Output PAPER_PLAN.md to wiki/outputs/.
>
> Key distinction: the outline is claim-graph-driven — each section exists because it supports a claim,
> not because paper convention requires that section.

## Inputs

- `claims`: list of target claim slugs (space-separated)
  - each claim should have status `supported` or `weakly_supported`
  - if `proposed` or `challenged` claims are included, warn but continue
- `--venue` (required): target venue, determines page limit and format requirements
  - supported: `ICLR` / `NeurIPS` / `ICML` / `ACL` / `CVPR` / `IEEE`
- `--title` (optional): working title; if omitted, generated from target claims

## Outputs

- `wiki/outputs/paper-plan-{slug}-{date}.md` — complete paper plan (PAPER_PLAN.md)
- `wiki/graph/edges.jsonl` — new derived_from edges (plan → source claims/papers)
- `wiki/graph/context_brief.md` — rebuilt
- `wiki/log.md` — appended log entry
- **PAPER_PLAN_REPORT** (printed to terminal) — plan summary

## Wiki Interaction

### Reads
- `wiki/claims/*.md` — status, confidence, evidence list, conditions of target claims
- `wiki/experiments/*.md` — supporting experiments for claims (results, metrics, key_result)
- `wiki/papers/*.md` — evidence source papers (Method, Results, Related)
- `wiki/concepts/*.md` — technical concepts involved (supports Method section writing)
- `wiki/topics/*.md` — research direction context (supports Introduction positioning)
- `wiki/ideas/*.md` — motivation and hypothesis of original ideas
- `wiki/graph/context_brief.md` — global context
- `wiki/graph/open_questions.md` — knowledge gaps (annotate paper limitations)
- `wiki/graph/edges.jsonl` — relationship graph (build narrative logic chain)
- `.claude/skills/shared-references/academic-writing.md` — writing principles
- `.claude/skills/shared-references/citation-verification.md` — citation discipline

### Writes
- `wiki/outputs/paper-plan-{slug}-{date}.md` — paper plan file
- `wiki/graph/edges.jsonl` — derived_from edges
- `wiki/graph/context_brief.md` — rebuilt
- `wiki/log.md` — appended operation log

### Graph edges created
- `derived_from`: paper-plan → claims (which claims the plan is derived from)
- `derived_from`: paper-plan → papers (which papers the plan cites)

## Workflow

**Precondition**: confirm the working directory is the wiki project root (the directory containing `wiki/`, `raw/`, `tools/`).

### Step 1: Load Claim Graph

1. Read `wiki/claims/{slug}.md` for all target claims
2. For each claim, collect its evidence list:
   - each evidence item's source (paper slug or experiment slug)
   - evidence type (supports / contradicts / tested_by / invalidates)
   - evidence strength (weak / moderate / strong)
3. For each evidence source, read the corresponding wiki page:
   - `wiki/experiments/{source}.md` → key_result, metrics, outcome
   - `wiki/papers/{source}.md` → Method, Results
4. Load relevant edges from `wiki/graph/edges.jsonl` to build relationships between claims
5. Read `wiki/graph/context_brief.md` for global context
6. Read `wiki/graph/open_questions.md` to annotate known limitations

**Validation**:
- If any target claim has status `proposed`: warn "claim is unvalidated; paper may lack evidence support"
- If any target claim has confidence < 0.5: warn "claim confidence is low; consider running more experiments first"
- If no experiment evidence supports any claim: error "at least one experimental result is required to plan a paper"

### Step 2: Compile Evidence Map from Wiki

Generate a structured matrix mapping claims → evidence → sections:

```markdown
| Claim | Status | Confidence | Evidence Sources | Strength | Paper Section |
|-------|--------|-----------|-----------------|----------|---------------|
| [[primary-claim]] | supported | 0.85 | exp-main, paper-A | strong | Method + Exp 5.2 |
| [[supporting-claim-1]] | supported | 0.75 | exp-ablation-1 | moderate | Exp 5.3 (Ablation) |
| [[supporting-claim-2]] | weakly_supported | 0.55 | exp-scaling | weak | Exp 5.4 (Scaling) |
```

Map claims to paper structure along each dimension:
- **Target claim** → core contribution, drives Abstract + Introduction + Method
- **Decomposition claims** → factor contributions, drives Ablation subsections
- **Contextual claims** → background knowledge, drives Related Work + Introduction

### Step 3: Determine Narrative Structure

Follow the hourglass principle in `shared-references/academic-writing.md`:

1. **Identify the paper's core storyline**:
   - Gap (extracted from ideas/ motivation or gap_map)
   - Solution (extracted from target claim's approach)
   - Evidence (extracted from experiments' results)
   - Impact (inferred from claim confidence + scope)

2. **Determine the narrative angle**:
   - What problem does the paper solve? (problem-driven vs. method-driven vs. data-driven)
   - Who is the primary audience? (theory / systems / applications)
   - How does it differentiate from the 3 most relevant recent papers?

3. **Establish section → claim mapping**:
   Every section must support at least one claim. A section with no claim support is filler and should be removed.

### Step 4: Generate Section Outline

Generate the outline according to venue format requirements; each section includes:

```markdown
## 1. Introduction (1.5 pages)

### Claims addressed
- Gap claim: {existing approaches lack X because Y}
- Contribution claim: [[primary-claim]]

### Paragraph plan
1. Broad context: {field importance, recent progress}
2. Specific problem: {what's missing, why it matters}
3. Our approach: "In this work, we propose..." + contributions list
4. Results preview: {headline numbers}
5. Paper structure: "The rest of this paper..."

### Key citations
- [[paper-A]] — establishes the problem
- [[paper-B]] — closest prior work (we improve upon)
- [[paper-C]] — our baseline

---

## 2. Related Work (1 page)

### Groupings
- Direction A: {papers, our position}
- Direction B: {papers, our position}
- Direction C: {papers, our position}

### Claims addressed
- Contextual claims distinguishing from prior work

---

## 3. Method (2-3 pages)

### Claims addressed
- [[primary-claim]]: section 3.1-3.2
- [[supporting-claim-1]]: section 3.3

### Subsection plan
- 3.1 Problem formulation: notation, objective
- 3.2 Core approach: intuition → formalism
- 3.3 Component X: design decision + justification
- 3.4 Training/inference details

### Figures
- Figure 1: Overall architecture (mandatory)
- Figure 2: Component X detail (if complex)

---

## 4. Experiments (2-3 pages)

### Claims addressed
- [[primary-claim]]: section 4.2 (main results)
- [[supporting-claim-1]]: section 4.3 (ablation)
- [[supporting-claim-2]]: section 4.4 (scaling)

### Subsection plan
- 4.1 Setup: datasets, baselines, metrics, implementation details
- 4.2 Main results: Table 1 (main comparison), [[exp-main]]
- 4.3 Ablation study: Table 2 (component analysis), [[exp-ablation-*]]
- 4.4 Analysis: scaling, robustness, qualitative examples

### Figures/Tables
- Table 1: Main comparison vs baselines
- Table 2: Ablation results
- Figure 3: Scaling curves / qualitative examples

---

## 5. Conclusion (0.5 page)

### Key takeaway
- {one sentence the reader should remember}

### Limitations
- {from gap_map or claim conditions}

### Future work
- {from gap_map open questions}
```

**Page budget**: allocated by `--venue` (refer to the venue table in academic-writing.md); total section pages <= venue main-body limit.

### Step 5: Figure Plan

Design each planned figure/table:

```markdown
## Figure Plan

### Figure 1: System Architecture
- Type: diagram
- Source: Method section description
- Style: block diagram with labeled components
- Size: full width (1 column = text width)

### Table 1: Main Results
- Type: comparison table
- Source: [[exp-main]] key_result + baselines
- Columns: Method | Metric-1 | Metric-2 | ...
- Rows: baselines + ours (ours in bold)
- Notes: best bold, second underline, ↑/↓ arrows for direction

### Figure 3: Scaling Analysis
- Type: line plot
- Source: [[exp-scaling]] results
- X-axis: scale dimension (model size / data size)
- Y-axis: performance metric
- Lines: ours vs baseline, with error bands
```

### Step 6: Citation Plan

Following `shared-references/citation-verification.md`:

1. List all wiki papers referenced via `[[slug]]` in the outline
2. For each paper, pre-fetch BibTeX:
   - DBLP first, then CrossRef, then S2
   - Success: record BibTeX key + source
   - Failure: mark `[UNCONFIRMED]`
3. Generate citation coverage report:
   ```
   Citations: 15 total, 12 verified (DBLP: 8, CrossRef: 3, S2: 1), 3 [UNCONFIRMED]
   ```
4. For [UNCONFIRMED] entries, provide suggested URLs for manual verification

### Step 7: Review LLM Review (mandatory)

```
mcp__llm-review__chat:
  system: "You are an area chair at {venue} reviewing a paper outline.
           Assess: Is the narrative convincing? Does every section serve a clear purpose?
           Are the experiments sufficient to support the claims?
           Is the related work coverage adequate?
           Are there obvious gaps that reviewers will attack?
           Provide specific suggestions for strengthening the outline."
  message: |
    ## Paper Outline
    {complete outline from Step 4}

    ## Evidence Map
    {evidence map from Step 2}

    ## Figure/Table Plan
    {plan from Step 5}

    ## Citation Coverage
    {report from Step 6}

    ## Questions for Review
    1. Is the narrative arc (gap → solution → evidence → impact) convincing?
    2. Are any claims under-supported? Which experiments are missing?
    3. Is the related work grouping appropriate? Missing directions?
    4. Will the page budget work? Any section too long/short?
    5. Are the figures/tables sufficient to tell the story?
```

Revise the outline based on Review LLM feedback (add sections, adjust page budget, add figures/tables, correct narrative structure).

### Step 8: Write to Wiki

1. **Generate slug**:
   ```bash
   python3 tools/research_wiki.py slug "<working-title>"
   ```

2. **Write PAPER_PLAN.md**:
   Create `wiki/outputs/paper-plan-{slug}-{date}.md` containing:
   - Metadata (venue, title, date, target claims)
   - Evidence Map (Step 2)
   - Complete section outline (Step 4, with Review LLM revisions)
   - Figure/Table Plan (Step 5)
   - Citation Plan + coverage report (Step 6)
   - Review LLM Review Summary (Step 7 key feedback and revision record)

3. **Add graph edges**:
   ```bash
   # plan → target claim
   python3 tools/research_wiki.py add-edge wiki/ \
     --from "outputs/paper-plan-{slug}-{date}" --to "claims/{primary-claim}" \
     --type derived_from --evidence "Paper plan built from this claim"

   # plan → key papers
   python3 tools/research_wiki.py add-edge wiki/ \
     --from "outputs/paper-plan-{slug}-{date}" --to "papers/{paper-slug}" \
     --type derived_from --evidence "Paper plan cites this paper"
   ```

4. **Rebuild derived data**:
   ```bash
   python3 tools/research_wiki.py rebuild-context-brief wiki/
   ```

5. **Append log**:
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "paper-plan | {venue} paper outline for [[{slug}]] | claims: {claim-list} | citations: {verified}/{total}"
   ```

6. **Print PAPER_PLAN_REPORT to terminal**:
   ```markdown
   # Paper Plan Report

   ## Meta
   - Title: {working title}
   - Venue: {venue}
   - Page limit: {N} pages
   - Date: {date}

   ## Claims → Sections
   | Claim | Confidence | Section |
   |-------|-----------|---------|
   | [[primary]] | 0.85 | Method + Exp 5.2 |
   | [[supporting-1]] | 0.75 | Exp 5.3 |

   ## Page Budget
   | Section | Pages | Claims |
   |---------|-------|--------|
   | Introduction | 1.5 | gap, contribution |
   | Related Work | 1.0 | context |
   | Method | 2.5 | primary, supporting |
   | Experiments | 2.5 | all |
   | Conclusion | 0.5 | — |

   ## Figures/Tables: {N} planned
   ## Citations: {verified}/{total} verified, {verify_count} [UNCONFIRMED]
   ## Review LLM Review: score {X}/10, verdict: {verdict}

   ## Next Steps
   - Run `/paper-draft wiki/outputs/paper-plan-{slug}-{date}.md` to draft the paper
   - Resolve {verify_count} [UNCONFIRMED] citations before /paper-compile
   ```

## Constraints

- **--venue is required**: page limits and format requirements vary significantly by venue; cannot be omitted
- **At least one experiment evidence**: purely theoretical claims are insufficient for an empirical paper; at least one experimental result is required
- **Page budget must be feasible**: total section pages <= venue main-body limit; otherwise adjust (compress or move to appendix)
- **Review LLM review is mandatory**: cannot be skipped; catching problems at the outline stage has the lowest cost
- **All citations from wiki**: every paper in the citation plan must exist in wiki/papers/
- **claim → section mapping must be complete**: every target claim must appear in at least one section
- **Every section must have a claim**: a section with no claim support is filler and should be removed or merged
- **Graph edges via tools/research_wiki.py**: do not manually edit edges.jsonl
- **Citations use [[slug]]**: all citations in the outline use wikilink syntax

## Error Handling

- **Insufficient claim status**: if all claims are `proposed`, error "claims are unvalidated; run experiments first"
- **No experiment evidence**: error "at least one experimental result is required"; suggest running /exp-design + /exp-run first
- **Insufficient wiki papers**: if the citation plan has fewer than 5 wiki papers, warn "related work coverage is insufficient; consider /ingest of more papers first"
- **Page budget exceeded**: automatically move lower-priority sections to appendix plan; report the adjustment
- **Review LLM unavailable**: fall back to Claude self-review; report annotated "single-model review — cross-model verification unavailable"
- **BibTeX fetch failed**: mark [UNCONFIRMED]; summarize in the citation plan report
- **Slug conflict**: append date suffix
- **Target claim not found**: error; list candidates in wiki/claims/

## Dependencies

### Tools（via Bash）
- `python3 tools/research_wiki.py slug "<title>"` — generate slug
- `python3 tools/research_wiki.py add-edge wiki/ ...` — add graph edge
- `python3 tools/research_wiki.py rebuild-context-brief wiki/` — rebuild query_pack
- `python3 tools/research_wiki.py log wiki/ "<message>"` — append log
- `python3 tools/fetch_s2.py search "<title>"` — Semantic Scholar search (citation plan fallback)

### MCP Servers
- `mcp__llm-review__chat` — Step 7 outline review (mandatory)

### Claude Code Native
- `Read` — read wiki pages
- `Glob` — find claims, experiments, papers
- `WebFetch` — DBLP / CrossRef BibTeX fetch (Step 6)

### Shared References
- `.claude/skills/shared-references/academic-writing.md` — narrative structure and section design principles
- `.claude/skills/shared-references/citation-verification.md` — citation fetch and verification rules

### Called by
- `/research` Stage 5 (paper writing stage)
- Manual user invocation
