# Three-RQ Analysis Report — `exp_0412_0914_vuln`

## Scope

This report analyzes the experiment [`exp_0412_0914_vuln`](/home/kira/pack/experiments/exp_0412_0914_vuln), using the aggregated results in [`PHASE_ONE_5/analysis`](/home/kira/pack/experiments/exp_0412_0914_vuln/PHASE_ONE_5/analysis).

The evaluated pipeline is not a comparison of multiple coding backbones. In this run:

- `problem_solver` uses `codellama`
- `security_fixer` uses `codellama`
- `challenge_designer`, `llm_judge`, and `pattern_analyzer` use `mistral`

So the report characterizes the secure-code capabilities of **one agentic coding pipeline** under Phase-1 vulnerability benchmarking.

## Scientifically Refined Research Questions

### RQ1

**What is the multi-shot secure code generation capability of the coding agent on Phase-1 vulnerability scenarios?**

Operationalization:

- success criterion: final run judged secure with no unresolved findings after the allowed attempt budget
- objective: estimate how often the agent can eventually produce secure code in a **multi-shot setting**
- supporting indicators: final `success_rate`, `avg_attempts`, and attempt distribution

### RQ2

**How effectively can the agent correct its initially insecure code when given iterative feedback and security-fixing opportunities?**

Operationalization:

- condition on initially unsuccessful first attempts
- measure recovery after an initially unsuccessful first attempt
- use `fixed_by_security_fixer`, attempts, and risk deltas as evidence of correction capability

### RQ3

**What recurrent vulnerability patterns are produced by the agents’ generated code, overall and by attack surface, and which of these patterns persist after correction?**

Operationalization:

- analyze the vulnerability findings present in generated code after the generation-and-feedback loop
- use final unresolved SAST tests, final unresolved CWEs, and deterministic `code_failure_pattern_analysis`
- use `persistent_test_ids` and `introduced_test_ids` to distinguish vulnerabilities that persist from the first attempt versus those introduced later
- stratify by attack surface to identify recurring surface-specific vulnerability patterns

## Data And Method

- Total Phase-1 runs: `156`
- Failed runs analyzed for RQ3: `41`
- Unique target CWE labels covered: `7`
- CWEs with at least one success: `7`

Primary sources:

- [`metrics.json`](/home/kira/pack/experiments/exp_0412_0914_vuln/PHASE_ONE_5/analysis/metrics.json)
- [`failure_patterns.json`](/home/kira/pack/experiments/exp_0412_0914_vuln/PHASE_ONE_5/analysis/failure_patterns.json)
- [`code_failure_pattern_analysis.json`](/home/kira/pack/experiments/exp_0412_0914_vuln/PHASE_ONE_5/analysis/code_failure_pattern_analysis.json)
- [`failure_patterns_by_attack_surface.csv`](/home/kira/pack/experiments/exp_0412_0914_vuln/PHASE_ONE_5/analysis/failure_patterns_by_attack_surface.csv)
- [`surface_specific_code_failure_patterns.csv`](/home/kira/pack/experiments/exp_0412_0914_vuln/PHASE_ONE_5/analysis/surface_specific_code_failure_patterns.csv)

Methodological note for RQ3:

- the current aggregate report captures vulnerability patterns primarily at the **final code state**
- persistence from the first attempt to the final attempt is available through `persistent_test_ids`
- full attempt-by-attempt artifacts exist in each run directory under `attempts/`, but they are not yet aggregated into a trajectory-level pattern report

## RQ1 — Multi-Shot Secure Code Generation Capability

The multi-shot secure generation capability is **substantial, but not uniformly strong across surfaces**.

Main results:

- Final secure success rate: `73.7%` (`115/156`)
- Average attempts per run: `1.90`
- Attempts executed distribution:
  - `1` attempt: `66` runs
  - `2` attempts: `40` runs
  - `3` attempts: `50` runs
- Median final risk: `0.0`
- Average final risk: `0.062`
- Judge-secure rate: `75.5%`

Interpretation:

- The pipeline can frequently reach a secure final solution within the allowed budget.
- The agent therefore has meaningful **multi-shot** secure-coding capability.
- However, this capability should not be confused with strong one-shot robustness.
- All `7` target CWE groups achieved at least one success, but none achieved perfect success across explored tasks.

### Multi-shot capability by attack surface

| Attack surface | Runs | Final secure successes | Multi-shot success rate |
|---|---:|---:|---:|
| User Inputs & Data | 12 | 8 | 66.7% |
| Web Outputs & Rendering | 5 | 5 | 100.0% |
| Storage & Filesystem | 40 | 21 | 52.5% |
| Authentication & Access Control | 19 | 14 | 73.7% |
| Data Exchange & External Services | 72 | 60 | 83.3% |
| Execution Environment & Infrastructure | 8 | 7 | 87.5% |

RQ1 conclusion:

- The strongest multi-shot capability appears on `Data Exchange & External Services` and `Execution Environment & Infrastructure`, with `Web Outputs & Rendering` also strong but on a very small sample.
- The weakest multi-shot capability is on `Storage & Filesystem`, where only `52.5%` of runs end securely.
- This suggests that even with multiple attempts, the agent remains comparatively weak on file/path-sensitive secure coding.

## RQ2 — Capability To Correct Security Problems

The agent shows a **meaningful but incomplete correction capability** once an initial problem appears.

Main results:

- One-shot secure success rate: `41.0%`
- Final secure success rate: `73.7%`
- Absolute gain from feedback: `+32.7` percentage points
- Successful recoveries after a first failed attempt: `51`
- Recovery rate after first failure: `55.4%`
- Share of all successful runs that required feedback: `44.3%`
- Average attempts per run: `1.90`
- Risk improved from first to final attempt in `47.4%` of runs
- Mean risk reduction from first to final attempt: `0.167`

This means the correction loop is not a minor optimization. It is a central part of how the pipeline reaches secure outcomes.

### Contribution of the security fixer to correction

- Runs fixed by `security_fixer`: `51`
- All `51` of those runs ended successfully

Top findings frequently resolved by the fixer:

- `bandit:B201`: `32`
- `codeql:py/weak-sensitive-data-hashing`: `8`
- `codeql:py/path-injection`: `7`
- `bandit:B314`: `6`
- `bandit:B104`: `4`

Interpretation:

- The feedback loop is especially valuable for cleaning up recurrent static-analysis findings.
- The fixer seems particularly effective on some high-frequency issues, especially `bandit:B201`.
- At the same time, `41` runs still fail overall, so the correction capability is important but not sufficient.

### Correction gains by attack surface

| Attack surface | One-shot rate | Final rate | Gain from feedback |
|---|---:|---:|---:|
| User Inputs & Data | 50.0% | 66.7% | +16.7 pp |
| Web Outputs & Rendering | 60.0% | 100.0% | +40.0 pp |
| Storage & Filesystem | 22.5% | 52.5% | +30.0 pp |
| Authentication & Access Control | 26.3% | 73.7% | +47.4 pp |
| Data Exchange & External Services | 51.4% | 83.3% | +31.9 pp |
| Execution Environment & Infrastructure | 50.0% | 87.5% | +37.5 pp |

RQ2 conclusion:

- The agent can correct a large fraction of its initial security mistakes: more than half of initially unsuccessful runs are recovered.
- Correction helps everywhere, but the largest gains appear on `Authentication & Access Control`, `Web Outputs & Rendering`, and `Execution Environment & Infrastructure`.
- Even after correction, `Storage & Filesystem` remains the weakest surface, which means this is a deeper capability gap rather than only a lack of repair.

## RQ3 — Recurrent Vulnerability Patterns Produced By The Agents

RQ3 focuses on the `41` failed runs that remain after the full generation-and-feedback process.

### Global structure of produced residual vulnerabilities

Primary failure reasons:

- `unresolved_off_target_findings`: `24` (`58.5%`)
- `unresolved_target_findings`: `10` (`24.4%`)
- `syntax_error`: `7` (`17.1%`)

This context matters, but the core of RQ3 is the vulnerability content of the produced code. The dominant residual problem is the persistence or introduction of unsafe code patterns, especially **off-target vulnerabilities**.

Top vulnerability patterns in final produced code, measured by unresolved SAST tests:

- `codeql:py/path-injection`: `17`
- `bandit:B201`: `10`
- `bandit:B104`: `4`
- `codeql:py/stack-trace-exposure`: `4`
- `codeql:py/reflective-xss`: `4`

Top final unresolved CWEs produced by the agents’ code:

- `CWE-22`: `18`
- `CWE-94`: `10`
- `CWE-209`: `4`
- `CWE-605`: `4`
- `CWE-79`: `4`

### Persistent versus newly introduced vulnerability patterns

Among failed runs, the most common **persistent** vulnerability findings from first attempt to final attempt are:

- `codeql:py/path-injection`: `15`
- `bandit:B201`: `10`
- `bandit:B104`: `4`
- `codeql:py/stack-trace-exposure`: `4`
- `codeql:py/reflective-xss`: `3`

Newly **introduced** final vulnerability findings are rare in this run:

- `codeql:py/reflective-xss`: `1`
- `bandit:B108`: `1`

Interpretation:

- the dominant vulnerability patterns are mainly **persistent**, not freshly introduced late in the process
- this means the main weakness is failure to remove certain vulnerability classes, especially path-related and debug/exposure findings

### Most common recurring code failure patterns

| Rank | Pattern | Support | Share of failed runs |
|---|---|---:|---:|
| 1 | Off-target `codeql:py/path-injection` | 9 | 22.0% |
| 2 | `syntax_error` | 7 | 17.1% |
| 3 | Off-target `bandit:B201` | 6 | 14.6% |
| 4 | Persistent target `codeql:py/path-injection` | 4 | 9.8% |
| 5 | Persistent target `bandit:B104` | 3 | 7.3% |

Interpretation:

- The strongest recurring vulnerability pattern is **unsafe path handling**.
- The second major vulnerability family is **unsafe debug/runtime exposure**.
- `syntax_error` still appears in the ranking because it is part of the deterministic pattern synthesis, but it is not itself a vulnerability pattern and should be treated as secondary for this RQ.

### Vulnerability patterns by attack surface

| Attack surface | Failed runs | Failed-run rate | Dominant residual pattern |
|---|---:|---:|---|
| User Inputs & Data | 4 | 33.3% | Mixed off-target findings, including path-injection and redirect issues |
| Web Outputs & Rendering | 0 | 0.0% | No residual failures in this sample |
| Storage & Filesystem | 19 | 47.5% | Path-injection dominates |
| Authentication & Access Control | 5 | 26.3% | Syntax errors and weak hashing issues |
| Data Exchange & External Services | 12 | 16.7% | Off-target `bandit:B201` dominates |
| Execution Environment & Infrastructure | 1 | 12.5% | `bandit:B605`-linked off-target failure |

Key surface-level findings:

- `Storage & Filesystem` is the clearest failure hotspot.
  - `19/40` runs fail
  - `11/19` storage failures are unresolved off-target findings
  - final `codeql:py/path-injection` appears `13` times on this surface
  - off-target `codeql:py/path-injection` appears in `7/19` failed storage runs

- `Authentication & Access Control` fails differently.
  - `3/5` failed auth runs are `syntax_error`
  - `syntax_error` has a surface specificity lift of about `3.51`
  - auth also shows `codeql:py/weak-sensitive-data-hashing`

- `Data Exchange & External Services` has a lower failure rate but a stable repeated signature.
  - `8/12` failed runs are unresolved off-target findings
  - the most common unresolved SAST test there is `bandit:B201`

RQ3 conclusion:

- The vulnerability patterns produced by the agents are structured, not random.
- The dominant recurrent vulnerability pattern is path-related unsafe code, especially `codeql:py/path-injection`.
- Most of the important vulnerability patterns are **persistent** from first attempt to final attempt rather than being newly introduced at the end.
- The exact vulnerability type depends strongly on attack surface: path handling for storage, weak hashing and some syntax brittleness for auth, and debug/exposure issues for data exchange.

## Overall Synthesis

Across the three RQs, the evidence supports a clear scientific story:

1. The coding agent has **meaningful multi-shot secure coding capability**, reaching a final secure success rate of `73.7%`.
2. The agent also has a **real correction capability**, recovering `55.4%` of runs that fail on the first attempt and gaining `+32.7` percentage points through feedback.
3. The remaining failures are explained by a **small number of recurring vulnerability patterns produced in the generated code**, especially path-injection and debug/exposure findings, and these patterns are strongly surface-dependent.

In short, this run shows an agentic pipeline that can often arrive at secure code in a multi-shot setting, can correct many of its initial security mistakes, but still produces a stable set of recurring vulnerability patterns concentrated in specific technical surfaces rather than uniformly spread across tasks.

## Threats To Validity

- This report is based on one experiment and one coding backbone configuration, not a multi-model comparison.
- `Web Outputs & Rendering` has only `5` runs, so its apparent strength should be interpreted cautiously.
- Some surface-specific patterns have support `1`; those are useful diagnostic hints, but not strong standalone evidence.
- Because both `problem_solver` and `security_fixer` use `codellama`, RQ1 and RQ2 describe one pipeline’s behavior rather than differences between distinct coding agents.
