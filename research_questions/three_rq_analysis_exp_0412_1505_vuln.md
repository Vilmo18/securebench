# Three-RQ Analysis Report — `exp_0412_1505_vuln`

## Scope

This report analyzes the experiment [`exp_0412_1505_vuln`](/home/kira/pack/experiments/exp_0412_1505_vuln), using the aggregated results in [`PHASE_ONE_5/analysis`](/home/kira/pack/experiments/exp_0412_1505_vuln/PHASE_ONE_5/analysis).

In this run, both the coding and fixing stages use **Qwen Coder**:

- `problem_solver`: `qwen2.5-coder:latest` in [agent_config_vul.yml](/home/kira/pack/agent_config_vul.yml#L441)
- `security_fixer`: `qwen2.5-coder:latest` in [agent_config_vul.yml](/home/kira/pack/agent_config_vul.yml#L448)

So this report characterizes the secure-code capabilities of the Qwen-based agentic pipeline under the same Phase-1 vulnerability benchmark.

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

- Total Phase-1 runs: `145`
- Failed runs analyzed for RQ3: `49`
- Unique target CWE labels covered: `7`
- CWEs with at least one success: `7`

Primary sources:

- [`metrics.json`](/home/kira/pack/experiments/exp_0412_1505_vuln/PHASE_ONE_5/analysis/metrics.json)
- [`failure_patterns.json`](/home/kira/pack/experiments/exp_0412_1505_vuln/PHASE_ONE_5/analysis/failure_patterns.json)
- [`code_failure_pattern_analysis.json`](/home/kira/pack/experiments/exp_0412_1505_vuln/PHASE_ONE_5/analysis/code_failure_pattern_analysis.json)
- [`failure_patterns_by_attack_surface.csv`](/home/kira/pack/experiments/exp_0412_1505_vuln/PHASE_ONE_5/analysis/failure_patterns_by_attack_surface.csv)
- [`surface_specific_code_failure_patterns.csv`](/home/kira/pack/experiments/exp_0412_1505_vuln/PHASE_ONE_5/analysis/surface_specific_code_failure_patterns.csv)

Methodological note for RQ3:

- the current aggregate report captures vulnerability patterns primarily at the **final code state**
- persistence from the first attempt to the final attempt is available through `persistent_test_ids`
- complete attempt-by-attempt artifacts are preserved in each run’s `attempts/` directory, but they are not yet aggregated into a full trajectory-level vulnerability-pattern report

## RQ1 — Multi-Shot Secure Code Generation Capability

The Qwen-based pipeline shows **moderate multi-shot secure-coding capability**, but it relies heavily on retries and correction.

Main results:

- Final secure success rate: `66.2%` (`96/145`)
- Average attempts per run: `1.96`
- Attempts executed distribution:
  - `0` counted attempts: `14` runs
  - `1` attempt: `26` runs
  - `2` attempts: `57` runs
  - `3` attempts: `48` runs
- Median final risk: `0.0`
- Average final risk: `0.147`
- Judge-secure rate: `77.4%`

Interpretation:

- The pipeline can often reach a secure final solution within the attempt budget.
- However, the overall profile is weaker than the earlier Codellama-based run: lower final secure success and much lower first-attempt success.
- The `0` counted-attempt cases correspond to runs that never produced code, which is an important limitation of this agent configuration.

### Multi-shot capability by attack surface

| Attack surface | Runs | Final secure successes | Multi-shot success rate |
|---|---:|---:|---:|
| User Inputs & Data | 10 | 6 | 60.0% |
| Web Outputs & Rendering | 7 | 2 | 28.6% |
| Storage & Filesystem | 40 | 18 | 45.0% |
| Authentication & Access Control | 31 | 28 | 90.3% |
| Data Exchange & External Services | 48 | 36 | 75.0% |
| Execution Environment & Infrastructure | 9 | 6 | 66.7% |

RQ1 conclusion:

- Qwen performs strongly in multi-shot mode on `Authentication & Access Control` and reasonably well on `Data Exchange & External Services`.
- The weakest multi-shot capability appears on `Web Outputs & Rendering` and `Storage & Filesystem`.
- `Storage & Filesystem` remains the clearest secure-coding weakness, while `Web Outputs & Rendering` is severely affected by no-code failures.

## RQ2 — Capability To Correct Security Problems

Qwen shows a **strong correction capability once feedback enters the loop**, even though its one-shot capability is weak.

Main results:

- One-shot secure success rate: `19.8%` (`26/145`)
- Final secure success rate: `66.2%` (`96/145`)
- Absolute gain from feedback: `+48.3` percentage points
- Successful recoveries after a first failed attempt: `70`
- Recovery rate after first failure: `58.8%`
- Share of all successful runs that required feedback: `72.9%`
- Average attempts per run: `1.96`
- Risk improved from first to final attempt in `75.6%` of runs
- Mean risk reduction from first to final attempt: `0.324`

This means the Qwen pipeline depends heavily on correction. Most of its secure successes are not obtained one-shot, but through the feedback-and-fixer loop.

### Contribution of the security fixer to correction

- Runs fixed by `security_fixer`: `70`
- All `70` of those runs ended successfully

Top findings frequently resolved by the fixer:

- `bandit:B201`: `51`
- `codeql:py/stack-trace-exposure`: `12`
- `bandit:B104`: `8`
- `codeql:py/url-redirection`: `7`
- `bandit:B314`: `6`

Interpretation:

- The correction loop is very active and very important in this run.
- Qwen’s final secure performance would be much lower without the fixer.
- The agent corrects many initial vulnerabilities, but the presence of `14` no-code failures shows that correction cannot help when no usable initial code is produced.

### Correction gains by attack surface

| Attack surface | One-shot rate | Final rate | Gain from feedback |
|---|---:|---:|---:|
| User Inputs & Data | 10.0% | 60.0% | +50.0 pp |
| Web Outputs & Rendering | 0.0% | 28.6% | +28.6 pp |
| Storage & Filesystem | 10.0% | 45.0% | +35.0 pp |
| Authentication & Access Control | 9.7% | 90.3% | +80.6 pp |
| Data Exchange & External Services | 31.3% | 75.0% | +43.8 pp |
| Execution Environment & Infrastructure | 33.3% | 66.7% | +33.3 pp |

RQ2 conclusion:

- Qwen has a very pronounced correction profile: poor one-shot security, but large gains from iterative fixing.
- The largest improvement appears on `Authentication & Access Control`, where correction transforms a weak one-shot profile into a very strong final profile.
- Even after correction, `Storage & Filesystem` remains weak, indicating a deeper capability gap.

## RQ3 — Recurrent Vulnerability Patterns Produced By The Agents

RQ3 focuses on the `49` failed runs that remain after the full generation-and-feedback process.

### Global structure of produced residual vulnerabilities

Primary failure reasons:

- `unresolved_off_target_findings`: `24` (`49.0%`)
- `no_code`: `14` (`28.6%`)
- `syntax_error`: `9` (`18.4%`)
- `unresolved_target_findings`: `2` (`4.1%`)

For vulnerability analysis, the key point is that when Qwen does produce insecure code, the residual problems are dominated by **off-target vulnerabilities**, not by failure to fix the target CWE.

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

### Persistent versus newly introduced vulnerability patterns

Among failed runs, the most common **persistent** vulnerability findings from first attempt to final attempt are:

- `codeql:py/path-injection`: `14`
- `codeql:py/reflective-xss`: `3`
- `codeql:py/stack-trace-exposure`: `2`
- `bandit:B301`: `1`
- `codeql:py/xxe`: `1`

Newly **introduced** final vulnerability findings are very rare in this run:

- `codeql:py/path-injection`: `2`

Interpretation:

- The main residual vulnerability patterns are mostly **persistent**, not introduced late.
- Qwen’s problem is therefore less about creating new classes of vulnerability during repair, and more about failing to eliminate certain recurring classes, especially path-related issues.

### Most common recurring vulnerability patterns

If we focus on vulnerability-producing patterns rather than generic generation failures, the dominant recurring patterns are:

| Rank | Pattern | Support | Share of failed runs |
|---|---|---:|---:|
| 1 | Off-target `codeql:py/path-injection` | 16 | 32.7% |
| 2 | Off-target `codeql:py/reflective-xss` | 1 | 2.0% |
| 3 | Off-target `bandit:B301` | 1 | 2.0% |
| 4 | Off-target `codeql:py/partial-ssrf` | 1 | 2.0% |
| 5 | Off-target `codeql:py/stack-trace-exposure` | 1 | 2.0% |

Important note:

- `no_code` and `syntax_error` are very visible in the raw failure taxonomy, but they are not vulnerability classes.
- For the vulnerability-centered reading of RQ3, `codeql:py/path-injection` is overwhelmingly the dominant residual pattern.

### Vulnerability patterns by attack surface

| Attack surface | Failed runs | Failed-run rate | Dominant vulnerability signal |
|---|---:|---:|---|
| User Inputs & Data | 4 | 40.0% | Sparse; one `bandit:B301` signal plus syntax issues |
| Web Outputs & Rendering | 5 | 71.4% | Mostly no-code, with one `bandit:B301` case |
| Storage & Filesystem | 22 | 55.0% | `codeql:py/path-injection` overwhelmingly dominates |
| Authentication & Access Control | 3 | 9.7% | Low failure rate; one `codeql:py/reflective-xss` case |
| Data Exchange & External Services | 12 | 25.0% | Mixed `stack-trace-exposure`, `xxe`, `partial-ssrf`, and one path-injection case |
| Execution Environment & Infrastructure | 3 | 33.3% | Mostly syntax/no-code rather than stable vulnerability findings |

Key surface-level findings:

- `Storage & Filesystem` is the clearest vulnerability hotspot.
  - `22/40` runs fail
  - `18/22` failed storage runs are unresolved off-target findings
  - final `codeql:py/path-injection` appears `17` times on this surface
  - off-target `codeql:py/path-injection` appears in `15/22` failed storage runs

- `Data Exchange & External Services` has a more diverse vulnerability signature.
  - final unresolved findings include `codeql:py/stack-trace-exposure`, `codeql:py/xxe`, `codeql:py/partial-ssrf`, and `codeql:py/weak-sensitive-data-hashing`
  - unlike storage, this surface does not collapse to one single dominating vulnerability family

- `Authentication & Access Control` is strong in final success terms, but its few residual vulnerability failures include `codeql:py/reflective-xss`

RQ3 conclusion:

- The vulnerability patterns produced by Qwen are structured, not random.
- The dominant recurring vulnerability family is path-related unsafe code, especially `codeql:py/path-injection`.
- Most important vulnerability patterns are persistent from first attempt to final attempt.
- The residual vulnerability story is highly surface-dependent: storage tasks are dominated by path-injection, while data-exchange tasks show a more diverse mix of exposure and parser-related findings.

## Overall Synthesis

Across the three RQs, the evidence supports a clear scientific story for the Qwen-based pipeline:

1. Qwen has **moderate multi-shot secure coding capability**, reaching a final secure success rate of `66.2%`, but this is weaker than its final judge-secure rate suggests because many failures are concentrated on a few difficult surfaces.
2. Qwen has a **very strong reliance on correction**, recovering `58.8%` of first-attempt failures and gaining `+48.3` percentage points through feedback.
3. The remaining failures are explained by a **small number of recurring vulnerability patterns produced in the generated code**, dominated by `codeql:py/path-injection`, with especially strong concentration on `Storage & Filesystem`.

In short, this run shows a pipeline that is much less reliable than the previous agent in one-shot secure generation, but highly capable of improving under feedback. Its residual weaknesses are concentrated in persistent vulnerability families rather than uniformly distributed across tasks.

## Threats To Validity

- This report is based on one experiment and one Qwen-based pipeline configuration, not a multi-model comparison.
- `Web Outputs & Rendering` and `Execution Environment & Infrastructure` have small sample sizes.
- Some surface-specific vulnerability patterns have support `1`; they are useful indicators, but weak standalone evidence.
- Because both `problem_solver` and `security_fixer` use `qwen2.5-coder:latest`, RQ1 and RQ2 describe one pipeline’s behavior rather than differences between distinct coding agents.
