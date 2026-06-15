# Research Questions (RQ) — Outputs Folder

This folder is a **workspace to store plots, tables, and written analysis** for each research question (RQ)
in your Prism/VulnBench-inspired project.

Each RQ has its own subfolder with a consistent structure:
- `data/`: exported CSV/JSON used for the analysis
- `plots/`: generated figures (PNG/SVG/PDF)
- `notes/`: markdown notes, interpretations, paper-ready text

## Auto-export (from vuln_report)
`pack/src/vuln_report.py` can auto-export relevant plots/stats into these folders.

Options:
- default: exports to `pack/research_questions/`
- `--rq-out-dir <PATH>`: choose a different root
- `--no-rq-export`: disable the export

## RQ1 — CWE frequency across tasks & difficulty 
What types of CWE vulnerabilities are most frequently introduced by LLM-generated code across tasks, and difficulty levels? 

Folder: `pack/research_questions/rq1_cwe_frequency/`

Goal: Identify which CWE types appear most often, stratified by difficulty and (optionally) by task/problem.

## RQ2 — Task complexity vs vulnerability density & CWE distribution
How does task complexity influence the vulnerability density and CWE distribution in LLM-generated code?
Folder: `pack/research_questions/rq2_complexity_effects/`

Goal: Relate complexity proxies (difficulty, `combo_size`, `loc_nonempty`, `cyclomatic_approx`) to issue density and CWE mix.

## RQ3 — Recurring failure patterns (reasoning/generation)
What recurring reasoning and generation failure patterns explain why LLM-generated code introduces specific CWE vulnerabilities?

Folder: `pack/research_questions/rq3_failure_patterns/`

Goal: Summarize recurring failure modes (e.g., persistent SAST findings, fixer loops, syntax errors) and connect them to CWE outcomes.

## RQ4 — Fundamental capability gaps by CWE (prompts/models)
Which CWE categories reveal fundamental capability gaps in LLM secure code reasoning, and how do these gaps evolve across prompting strategies and models?
Folder: `pack/research_questions/rq4_capability_gaps/`

Goal: Compare CWE-level performance across prompting strategies and models (capability tables, success rates, avg risk).





