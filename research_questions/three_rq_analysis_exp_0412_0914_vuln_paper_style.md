# Multi-Shot Secure Coding, Correction Capability, and Recurrent Failure Patterns in `exp_0412_0914_vuln`

## Abstract

This report analyzes the Phase-1 vulnerability benchmark run [`exp_0412_0914_vuln`](/home/kira/pack/experiments/exp_0412_0914_vuln). We study three questions: the agent’s multi-shot ability to produce secure code, its ability to correct initially insecure outputs when feedback is available, and the recurrent residual failure patterns that remain after the generate-and-fix loop. The evaluated system is a single agentic pipeline in which both the `problem_solver` and `security_fixer` use `codellama`, while `mistral` is used for challenge design, judging, and pattern analysis. Across `156` Phase-1 runs, the pipeline reaches a final secure success rate of `73.7%`, but only `41.0%` of runs are secure on the first attempt. Feedback therefore contributes materially to final performance, adding `+32.7` percentage points and recovering `55.4%` of runs that fail initially. Residual failures are dominated by off-target vulnerabilities rather than inability to answer, with especially strong concentration in `Storage & Filesystem` and repeated recurrence of `codeql:py/path-injection` and `bandit:B201`. These results suggest that the pipeline has meaningful multi-shot secure-coding capability, non-trivial correction ability, and a small set of stable surface-dependent failure modes.

## 1. Research Questions

This analysis addresses the following refined research questions.

**RQ1. What is the multi-shot secure code generation capability of the coding agent on Phase-1 vulnerability scenarios?**

This question concerns the agent’s ability to eventually produce secure code within the allowed attempt budget, rather than on a single shot.

**RQ2. How effectively can the agent correct its initially insecure code when given iterative feedback and security-fixing opportunities?**

This question isolates correction behavior after an unsuccessful first attempt and asks whether feedback materially changes outcomes.

**RQ3. What recurrent vulnerability patterns are produced by the agents’ generated code, overall and by attack surface, and which of these patterns persist after correction?**

This question focuses on the vulnerability structure of the produced code, especially whether the same vulnerability classes recur in recognizable technical forms across surfaces and survive correction.

## 2. Method

### 2.1 Experimental scope

The analysis uses aggregated results from [`PHASE_ONE_5/analysis`](/home/kira/pack/experiments/exp_0412_0914_vuln/PHASE_ONE_5/analysis) for experiment [`exp_0412_0914_vuln`](/home/kira/pack/experiments/exp_0412_0914_vuln).

The evaluated pipeline is:

- `problem_solver`: `codellama`
- `security_fixer`: `codellama`
- `challenge_designer`: `mistral`
- `llm_judge`: `mistral`
- `pattern_analyzer`: `mistral`

This is therefore a **single-pipeline analysis**, not a comparison between multiple coding agents.

### 2.2 Data

- Total Phase-1 runs: `156`
- Failed runs used for residual failure analysis: `41`
- Unique target CWE labels covered: `7`
- Target CWE labels with at least one secure success: `7`

Primary artifacts:

- [`metrics.json`](/home/kira/pack/experiments/exp_0412_0914_vuln/PHASE_ONE_5/analysis/metrics.json)
- [`failure_patterns.json`](/home/kira/pack/experiments/exp_0412_0914_vuln/PHASE_ONE_5/analysis/failure_patterns.json)
- [`code_failure_pattern_analysis.json`](/home/kira/pack/experiments/exp_0412_0914_vuln/PHASE_ONE_5/analysis/code_failure_pattern_analysis.json)
- [`failure_patterns_by_attack_surface.csv`](/home/kira/pack/experiments/exp_0412_0914_vuln/PHASE_ONE_5/analysis/failure_patterns_by_attack_surface.csv)
- [`surface_specific_code_failure_patterns.csv`](/home/kira/pack/experiments/exp_0412_0914_vuln/PHASE_ONE_5/analysis/surface_specific_code_failure_patterns.csv)

### 2.3 Operational definitions

For this report:

- `secure success` means that the final run is judged secure and has no unresolved findings.
- `one-shot success` means secure success on the first counted attempt.
- `multi-shot success` means secure success after the full attempt budget and fixer loop.
- `correction` means improvement from an initially unsuccessful first attempt to a secure final state.
- `recurrent vulnerability pattern` means a repeated vulnerability signal in the generated code, anchored by SAST tests, CWE labels, and persistence from first attempt to final attempt when available.

Methodological note for RQ3:

- the aggregate report primarily captures vulnerability patterns present in the **final code state**
- persistence from the first attempt to the final attempt is captured through `persistent_test_ids`
- complete attempt-by-attempt artifacts are preserved in each run’s `attempts/` directory, but they are not yet aggregated into a full trajectory-level vulnerability-pattern report

## 3. Results

### 3.1 RQ1 — Multi-shot secure code generation capability

The agent demonstrates **meaningful multi-shot secure-coding capability**, but this capability is uneven across attack surfaces.

Global results:

- Final secure success rate: `73.7%` (`115/156`)
- Average attempts per run: `1.90`
- Attempts executed:
  - `66` runs ended after `1` attempt
  - `40` runs ended after `2` attempts
  - `50` runs ended after `3` attempts
- Median final risk: `0.0`
- Average final risk: `0.062`
- Judge-secure rate: `75.5%`

These values indicate that the pipeline often reaches a secure final state, but typically not immediately.

#### By attack surface

| Attack surface | Runs | Final secure successes | Multi-shot success rate |
|---|---:|---:|---:|
| User Inputs & Data | 12 | 8 | 66.7% |
| Web Outputs & Rendering | 5 | 5 | 100.0% |
| Storage & Filesystem | 40 | 21 | 52.5% |
| Authentication & Access Control | 19 | 14 | 73.7% |
| Data Exchange & External Services | 72 | 60 | 83.3% |
| Execution Environment & Infrastructure | 8 | 7 | 87.5% |

The strongest multi-shot performance appears on `Data Exchange & External Services` and `Execution Environment & Infrastructure`, while `Storage & Filesystem` is the weakest surface by a large margin. The `Web Outputs & Rendering` result is strong but based on only `5` runs and should be interpreted cautiously.

**Answer to RQ1.** The agent can often produce secure code in a multi-shot setting, but its final secure coding capability is highly surface-dependent and remains weak on storage- and path-sensitive tasks.

### 3.2 RQ2 — Correction capability under feedback

The agent shows a **substantial correction capability** once feedback is introduced.

Global correction results:

- One-shot secure success rate: `41.0%` (`64/156`)
- Final secure success rate: `73.7%` (`115/156`)
- Absolute gain from feedback: `+32.7` percentage points
- Successful recoveries after an initially failed first attempt: `51`
- Recovery rate after first failure: `55.4%`
- Share of successful runs that required feedback: `44.3%`
- Runs with risk improvement from first to final attempt: `47.4%`
- Mean risk reduction from first to final attempt: `0.167`

These results show that iterative feedback is not merely polishing already-correct solutions; it changes the final outcome on a large fraction of tasks.

#### Contribution of the security fixer

- Runs marked `fixed_by_security_fixer`: `51`
- All `51` of those runs ended in secure success

The most frequently resolved findings are:

- `bandit:B201`: `32`
- `codeql:py/weak-sensitive-data-hashing`: `8`
- `codeql:py/path-injection`: `7`
- `bandit:B314`: `6`
- `bandit:B104`: `4`

This suggests that the correction stage is particularly effective on a recurring subset of static-analysis findings.

#### By attack surface

| Attack surface | One-shot rate | Final rate | Gain from feedback |
|---|---:|---:|---:|
| User Inputs & Data | 50.0% | 66.7% | +16.7 pp |
| Web Outputs & Rendering | 60.0% | 100.0% | +40.0 pp |
| Storage & Filesystem | 22.5% | 52.5% | +30.0 pp |
| Authentication & Access Control | 26.3% | 73.7% | +47.4 pp |
| Data Exchange & External Services | 51.4% | 83.3% | +31.9 pp |
| Execution Environment & Infrastructure | 50.0% | 87.5% | +37.5 pp |

The largest correction gains occur on `Authentication & Access Control`, `Web Outputs & Rendering`, and `Execution Environment & Infrastructure`. However, even after correction, `Storage & Filesystem` remains the weakest area, which indicates a deeper capability limitation rather than a mere lack of repair.

**Answer to RQ2.** The agent is capable of correcting many of its initial security failures, recovering more than half of first-attempt failures, but this correction ability is incomplete and does not eliminate structural weaknesses on all surfaces.

### 3.3 RQ3 — Recurrent vulnerability patterns produced by the agents

RQ3 analyzes the `41` failed runs that remain after the full generate-and-fix process.

#### Global structure of produced residual vulnerabilities

Primary failure reasons:

- `unresolved_off_target_findings`: `24` (`58.5%`)
- `unresolved_target_findings`: `10` (`24.4%`)
- `syntax_error`: `7` (`17.1%`)

The most important observation is that residual failures are dominated by **off-target vulnerabilities**, not by the absence of output or a generic inability to solve the task.

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

#### Persistent versus newly introduced vulnerability patterns

The most common vulnerability findings that **persist from first attempt to final attempt** are:

- `codeql:py/path-injection`: `15`
- `bandit:B201`: `10`
- `bandit:B104`: `4`
- `codeql:py/stack-trace-exposure`: `4`
- `codeql:py/reflective-xss`: `3`

Newly introduced final vulnerability findings are comparatively rare:

- `codeql:py/reflective-xss`: `1`
- `bandit:B108`: `1`

This indicates that the main residual weakness is not late-stage corruption of otherwise safe code. Rather, it is the failure to eliminate a small number of recurrent vulnerability families that are already present early in the trajectory.

#### Most common recurrent vulnerability patterns

| Rank | Pattern | Support | Share of failed runs |
|---|---|---:|---:|
| 1 | Off-target `codeql:py/path-injection` | 9 | 22.0% |
| 2 | `syntax_error` | 7 | 17.1% |
| 3 | Off-target `bandit:B201` | 6 | 14.6% |
| 4 | Persistent target `codeql:py/path-injection` | 4 | 9.8% |
| 5 | Persistent target `bandit:B104` | 3 | 7.3% |

These patterns indicate that the produced residual vulnerabilities are concentrated around a small number of technical families, especially unsafe path handling and debug/runtime exposure. The presence of `syntax_error` in this table is informative for robustness, but it should be interpreted as secondary because it is not itself a vulnerability class.

#### By attack surface

| Attack surface | Failed runs | Failed-run rate | Dominant residual pattern |
|---|---:|---:|---|
| User Inputs & Data | 4 | 33.3% | Mixed off-target findings, including path-injection and redirect issues |
| Web Outputs & Rendering | 0 | 0.0% | No residual failures in this sample |
| Storage & Filesystem | 19 | 47.5% | Path-injection dominates |
| Authentication & Access Control | 5 | 26.3% | Syntax errors and weak hashing issues |
| Data Exchange & External Services | 12 | 16.7% | Off-target `bandit:B201` dominates |
| Execution Environment & Infrastructure | 1 | 12.5% | `bandit:B605`-linked off-target failure |

The surface-specific structure is especially informative:

- `Storage & Filesystem` is the clearest failure hotspot.
  - `19/40` runs fail
  - `11/19` failed storage runs are driven by unresolved off-target findings
  - final `codeql:py/path-injection` appears `13` times on this surface
  - off-target `codeql:py/path-injection` appears in `7/19` failed storage runs

- `Authentication & Access Control` has a different signature.
  - `3/5` failed auth runs are `syntax_error`
  - syntax errors have a surface specificity lift of about `3.51`
  - auth also shows weak-sensitive-data-hashing as a recurring specific issue

- `Data Exchange & External Services` fails less often overall, but when it fails it does so in a repeated way.
  - `8/12` failed runs are unresolved off-target findings
  - the most common unresolved SAST test is `bandit:B201`

**Answer to RQ3.** The vulnerability patterns produced by the agents are strongly structured rather than random. The dominant recurring vulnerability family is path-related unsafe code, especially `codeql:py/path-injection`, followed by debug/exposure findings such as `bandit:B201`. Most important patterns are persistent from first attempt to final attempt, and their exact technical form depends heavily on attack surface.

## 4. Discussion

Taken together, the three RQs support a coherent interpretation of this experiment.

First, the pipeline has genuine secure-coding ability in a **multi-shot** regime. A `73.7%` final secure success rate is too high to characterize the system as broadly incapable. At the same time, the low first-attempt rate (`41.0%`) shows that this capability is not robust enough to be treated as default secure behavior.

Second, iterative correction is a central component of observed performance rather than an ancillary convenience. Nearly half of successful outcomes require feedback, and more than half of first-attempt failures are recovered. This means that evaluating only one-shot secure coding would substantially underestimate the capability of the full agentic system.

Third, the vulnerabilities that remain are diagnostically meaningful. They are not noise. They recur in a small number of stable technical forms, especially off-target path-handling and debug/exposure issues. This makes the benchmark valuable not only for capability measurement but also for identifying concrete steering and repair targets.

The most important qualitative takeaway is that **different attack surfaces expose different failure regimes**. Storage/file tasks reveal a persistent inability to reliably control unsafe path behavior. Authentication tasks reveal unusual syntax brittleness and cryptographic weakness patterns. Data-exchange tasks reveal debug and exposure regressions. This surface-dependent structure is precisely the kind of signal that is useful for capability mapping and benchmark design.

## 5. Threats to Validity

- This analysis covers a single experiment and one coding backbone configuration, not multiple coding agents.
- Because both `problem_solver` and `security_fixer` use `codellama`, the results characterize one pipeline rather than a comparison between model families.
- `Web Outputs & Rendering` has only `5` runs, so its apparent performance should be treated cautiously.
- Some surface-specific patterns have support `1`; those are useful diagnostic indicators but weak standalone evidence.
- The conclusions are conditioned on the Phase-1 benchmark setup and should not be generalized to all prompting or all repair settings without additional runs.

## 6. Conclusion

This experiment shows a pipeline that is meaningfully capable of producing secure code in a multi-shot setting, substantially benefits from iterative correction, and still exhibits stable recurrent residual vulnerability patterns. The strongest practical weakness is `Storage & Filesystem`, where both final success rates and vulnerability-pattern analysis point to persistent problems with unsafe path handling. More broadly, the results suggest that secure-code capability should be evaluated jointly in terms of eventual secure performance, correction ability, and the technical structure of the vulnerabilities that the agents’ code continues to produce, rather than by one-shot success alone.
