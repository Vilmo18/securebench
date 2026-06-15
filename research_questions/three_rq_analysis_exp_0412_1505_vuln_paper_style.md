# Multi-Shot Secure Coding, Correction Capability, and Recurrent Vulnerability Patterns in `exp_0412_1505_vuln`

## Abstract

This report analyzes the Phase-1 vulnerability benchmark run [`exp_0412_1505_vuln`](/home/kira/pack/experiments/exp_0412_1505_vuln). In this experiment, both the `problem_solver` and `security_fixer` use `qwen2.5-coder:latest` as configured in [agent_config_vul.yml](/home/kira/pack/agent_config_vul.yml#L441) and [agent_config_vul.yml](/home/kira/pack/agent_config_vul.yml#L448). We study three questions: the agent’s multi-shot ability to produce secure code, its ability to correct initially insecure outputs when feedback is available, and the recurrent vulnerability patterns that remain after the generate-and-fix loop. Across `145` Phase-1 runs, the pipeline reaches a final secure success rate of `66.2%`, but only `19.8%` of runs are secure on the first attempt. Feedback therefore contributes heavily to final performance, adding `+48.3` percentage points and recovering `58.8%` of runs that fail initially. Residual failures are dominated by off-target vulnerabilities and by non-production failures such as `no_code`, but among genuine vulnerability patterns the strongest by far is `codeql:py/path-injection`, especially on `Storage & Filesystem`. These results suggest that the Qwen-based pipeline has moderate multi-shot secure-coding capability, strong correction dependence, and highly concentrated residual vulnerability weaknesses.

## 1. Research Questions

This analysis addresses the following refined research questions.

**RQ1. What is the multi-shot secure code generation capability of the coding agent on Phase-1 vulnerability scenarios?**

This question concerns the agent’s ability to eventually produce secure code within the allowed attempt budget.

**RQ2. How effectively can the agent correct its initially insecure code when given iterative feedback and security-fixing opportunities?**

This question isolates correction behavior after an unsuccessful first attempt.

**RQ3. What recurrent vulnerability patterns are produced by the agents’ generated code, overall and by attack surface, and which of these patterns persist after correction?**

This question focuses on the vulnerability structure of the produced code, not only on generic failure reasons.

## 2. Method

### 2.1 Experimental scope

The analysis uses aggregated results from [`PHASE_ONE_5/analysis`](/home/kira/pack/experiments/exp_0412_1505_vuln/PHASE_ONE_5/analysis) for experiment [`exp_0412_1505_vuln`](/home/kira/pack/experiments/exp_0412_1505_vuln).

The evaluated pipeline is:

- `problem_solver`: `qwen2.5-coder:latest`
- `security_fixer`: `qwen2.5-coder:latest`
- `challenge_designer`: `mistral`
- `llm_judge`: `mistral`
- `pattern_analyzer`: `mistral`

This is therefore a **single-pipeline analysis**, not a comparison between multiple coding agents.

### 2.2 Data

- Total Phase-1 runs: `145`
- Failed runs used for residual vulnerability analysis: `49`
- Unique target CWE labels covered: `7`
- Target CWE labels with at least one secure success: `7`

Primary artifacts:

- [`metrics.json`](/home/kira/pack/experiments/exp_0412_1505_vuln/PHASE_ONE_5/analysis/metrics.json)
- [`failure_patterns.json`](/home/kira/pack/experiments/exp_0412_1505_vuln/PHASE_ONE_5/analysis/failure_patterns.json)
- [`code_failure_pattern_analysis.json`](/home/kira/pack/experiments/exp_0412_1505_vuln/PHASE_ONE_5/analysis/code_failure_pattern_analysis.json)
- [`failure_patterns_by_attack_surface.csv`](/home/kira/pack/experiments/exp_0412_1505_vuln/PHASE_ONE_5/analysis/failure_patterns_by_attack_surface.csv)
- [`surface_specific_code_failure_patterns.csv`](/home/kira/pack/experiments/exp_0412_1505_vuln/PHASE_ONE_5/analysis/surface_specific_code_failure_patterns.csv)

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
- full attempt-by-attempt artifacts are preserved in each run’s `attempts/` directory, but they are not yet aggregated into a complete trajectory-level vulnerability-pattern report

## 3. Results

### 3.1 RQ1 — Multi-shot secure code generation capability

The Qwen-based pipeline demonstrates **moderate multi-shot secure-coding capability**, but it is much weaker in initial secure generation than in final outcome.

Global results:

- Final secure success rate: `66.2%` (`96/145`)
- Average attempts per run: `1.96`
- Attempts executed:
  - `14` runs ended with `0` counted attempts
  - `26` runs ended after `1` attempt
  - `57` runs ended after `2` attempts
  - `48` runs ended after `3` attempts
- Median final risk: `0.0`
- Average final risk: `0.147`
- Judge-secure rate: `77.4%`

These values indicate that Qwen can often reach a secure final state, but usually not directly. The presence of `14` runs with `0` counted attempts also shows that non-production remains a meaningful limitation of this configuration.

#### By attack surface

| Attack surface | Runs | Final secure successes | Multi-shot success rate |
|---|---:|---:|---:|
| User Inputs & Data | 10 | 6 | 60.0% |
| Web Outputs & Rendering | 7 | 2 | 28.6% |
| Storage & Filesystem | 40 | 18 | 45.0% |
| Authentication & Access Control | 31 | 28 | 90.3% |
| Data Exchange & External Services | 48 | 36 | 75.0% |
| Execution Environment & Infrastructure | 9 | 6 | 66.7% |

The strongest multi-shot performance appears on `Authentication & Access Control`, while `Storage & Filesystem` and `Web Outputs & Rendering` are the weakest surfaces.

**Answer to RQ1.** Qwen can often produce secure code in a multi-shot setting, but its final secure-coding capability is uneven across surfaces and clearly dependent on multiple attempts.

### 3.2 RQ2 — Correction capability under feedback

Qwen shows a **very strong correction profile**, despite weak one-shot secure generation.

Global correction results:

- One-shot secure success rate: `19.8%` (`26/145`)
- Final secure success rate: `66.2%` (`96/145`)
- Absolute gain from feedback: `+48.3` percentage points
- Successful recoveries after an initially failed first attempt: `70`
- Recovery rate after first failure: `58.8%`
- Share of successful runs that required feedback: `72.9%`
- Runs with risk improvement from first to final attempt: `75.6%`
- Mean risk reduction from first to final attempt: `0.324`

This shows that feedback is not a minor refinement layer. It is the main mechanism by which the Qwen-based pipeline reaches secure outcomes.

#### Contribution of the security fixer

- Runs marked `fixed_by_security_fixer`: `70`
- All `70` of those runs ended in secure success

The most frequently resolved findings are:

- `bandit:B201`: `51`
- `codeql:py/stack-trace-exposure`: `12`
- `bandit:B104`: `8`
- `codeql:py/url-redirection`: `7`
- `bandit:B314`: `6`

This suggests that the fixer is especially effective on a recurring set of SAST findings, even though it cannot help on runs where the model fails to produce usable code.

#### By attack surface

| Attack surface | One-shot rate | Final rate | Gain from feedback |
|---|---:|---:|---:|
| User Inputs & Data | 10.0% | 60.0% | +50.0 pp |
| Web Outputs & Rendering | 0.0% | 28.6% | +28.6 pp |
| Storage & Filesystem | 10.0% | 45.0% | +35.0 pp |
| Authentication & Access Control | 9.7% | 90.3% | +80.6 pp |
| Data Exchange & External Services | 31.3% | 75.0% | +43.8 pp |
| Execution Environment & Infrastructure | 33.3% | 66.7% | +33.3 pp |

The largest correction gains occur on `Authentication & Access Control`, where Qwen moves from a weak one-shot profile to very high final success. However, even after correction, `Storage & Filesystem` remains weak.

**Answer to RQ2.** Qwen is capable of correcting many of its initial security failures and depends strongly on feedback to do so, but this correction capability does not fully eliminate deeper weaknesses on difficult surfaces.

### 3.3 RQ3 — Recurrent vulnerability patterns produced by the agents

RQ3 analyzes the `49` failed runs that remain after the full generate-and-fix process.

#### Global structure of produced residual vulnerabilities

Primary failure reasons:

- `unresolved_off_target_findings`: `24` (`49.0%`)
- `no_code`: `14` (`28.6%`)
- `syntax_error`: `9` (`18.4%`)
- `unresolved_target_findings`: `2` (`4.1%`)

This means that the residual failure space contains both vulnerability-bearing failures and non-production failures. For the vulnerability-focused reading of RQ3, the important result is that the remaining insecure code is dominated by **off-target** vulnerability patterns.

Top vulnerability patterns in final produced code, measured by unresolved SAST tests:

- `codeql:py/path-injection`: `18`
- `codeql:py/stack-trace-exposure`: `4`
- `codeql:py/reflective-xss`: `3`
- `bandit:B301`: `2`
- `codeql:py/xxe`: `2`

Top final unresolved CWEs produced by the agents’ code:

- `CWE-22`: `18`
- `CWE-209`: `4`
- `CWE-79`: `3`
- `CWE-502`: `2`
- `CWE-611`: `2`

#### Persistent versus newly introduced vulnerability patterns

The most common vulnerability findings that **persist from first attempt to final attempt** are:

- `codeql:py/path-injection`: `14`
- `codeql:py/reflective-xss`: `3`
- `codeql:py/stack-trace-exposure`: `2`
- `bandit:B301`: `1`
- `codeql:py/xxe`: `1`

Newly introduced final vulnerability findings are rare:

- `codeql:py/path-injection`: `2`

This indicates that the main residual weakness is not late-stage corruption of otherwise safe code. Rather, it is the failure to eliminate a small number of recurring vulnerability families that survive correction.

#### Most common recurrent vulnerability patterns

If we focus on vulnerability-producing patterns and set aside generic generation failures such as `no_code` and `syntax_error`, the dominant recurring patterns are:

| Rank | Pattern | Support | Share of failed runs |
|---|---|---:|---:|
| 1 | Off-target `codeql:py/path-injection` | 16 | 32.7% |
| 2 | Off-target `codeql:py/reflective-xss` | 1 | 2.0% |
| 3 | Off-target `bandit:B301` | 1 | 2.0% |
| 4 | Off-target `codeql:py/partial-ssrf` | 1 | 2.0% |
| 5 | Off-target `codeql:py/stack-trace-exposure` | 1 | 2.0% |

This concentration shows that the residual vulnerability space is not diffuse. It is dominated by one very large family, namely path-related unsafe code.

#### By attack surface

| Attack surface | Failed runs | Failed-run rate | Dominant residual vulnerability signal |
|---|---:|---:|---|
| User Inputs & Data | 4 | 40.0% | Sparse; one `bandit:B301` vulnerability plus syntax issues |
| Web Outputs & Rendering | 5 | 71.4% | Mostly no-code, with one `bandit:B301` vulnerability |
| Storage & Filesystem | 22 | 55.0% | `codeql:py/path-injection` overwhelmingly dominates |
| Authentication & Access Control | 3 | 9.7% | Low failure rate; one `codeql:py/reflective-xss` case |
| Data Exchange & External Services | 12 | 25.0% | Mixed `stack-trace-exposure`, `xxe`, `partial-ssrf`, and one path-injection case |
| Execution Environment & Infrastructure | 3 | 33.3% | Mostly syntax/no-code rather than stable vulnerability findings |

The surface-specific structure is especially informative:

- `Storage & Filesystem` is the clearest vulnerability hotspot.
  - `22/40` runs fail
  - `18/22` failed storage runs are driven by unresolved off-target findings
  - final `codeql:py/path-injection` appears `17` times on this surface

- `Data Exchange & External Services` has a more diverse residual vulnerability profile.
  - findings include `codeql:py/stack-trace-exposure`, `codeql:py/xxe`, `codeql:py/partial-ssrf`, and `codeql:py/weak-sensitive-data-hashing`
  - unlike storage, this surface does not collapse to one single dominant vulnerability family

- `Authentication & Access Control` is strong in final success terms, but its few residual failures still reveal a specific vulnerability signature via `codeql:py/reflective-xss`

**Answer to RQ3.** The vulnerability patterns produced by Qwen are strongly structured rather than random. The dominant recurring vulnerability family is path-related unsafe code, especially `codeql:py/path-injection`, and most important patterns are persistent from first attempt to final attempt. Their technical form depends heavily on attack surface.

## 4. Discussion

Taken together, the three RQs support a coherent interpretation of this experiment.

First, the Qwen-based pipeline has genuine secure-coding ability in a **multi-shot** regime, but its final performance (`66.2%`) depends heavily on repeated attempts and correction. Its one-shot capability is weak enough that it should not be characterized as reliably secure by default.

Second, iterative correction is even more central here than in the earlier run. Nearly three quarters of successful outcomes require feedback, and the absolute gain from correction is `+48.3` percentage points. This means that evaluation of Qwen in one-shot mode would dramatically understate the capability of the full agentic pipeline.

Third, the residual vulnerability story is highly asymmetric. On the one hand, many failures are not vulnerability-bearing at all, but `no_code` or `syntax_error`. On the other hand, when Qwen does produce insecure code that survives correction, it does so in a highly concentrated way, overwhelmingly around `codeql:py/path-injection` on `Storage & Filesystem`.

This makes the benchmark diagnostically useful in two different ways. It identifies both a **generation reliability problem** and a **stable residual vulnerability family**. These are distinct weaknesses and should not be conflated.

## 5. Threats to Validity

- This analysis covers a single experiment and one Qwen-based pipeline configuration, not multiple coding agents.
- Because both `problem_solver` and `security_fixer` use `qwen2.5-coder:latest`, the results characterize one pipeline rather than a comparison between model families.
- `Web Outputs & Rendering` and `Execution Environment & Infrastructure` have relatively small sample sizes.
- Some surface-specific vulnerability patterns have support `1`; those are useful indicators but weak standalone evidence.
- The conclusions are conditioned on the Phase-1 benchmark setup and should not be generalized to all prompting or all repair settings without additional runs.

## 6. Conclusion

This experiment shows a Qwen-based agentic pipeline that is moderately capable of producing secure code in a multi-shot setting, strongly dependent on iterative correction, and characterized by a sharply concentrated residual vulnerability profile. The strongest practical weakness is `Storage & Filesystem`, where final performance and residual vulnerability analysis both point to persistent path-related unsafe code. More broadly, the results suggest that Qwen’s secure-code capability should be evaluated jointly in terms of eventual secure performance, correction ability, generation reliability, and the technical structure of the vulnerabilities that remain after correction.
