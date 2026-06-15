# Benchmark Results Across Two Agent Runs — `exp_0412_0914_vuln` and `exp_0412_1505_vuln`

## Scope

This report merges the results of two Phase-1 vulnerability benchmark runs into a single **benchmark-oriented results section**:

- CodeLlama run: [`exp_0412_0914_vuln`](/home/kira/pack/experiments/exp_0412_0914_vuln)
- Qwen run: [`exp_0412_1505_vuln`](/home/kira/pack/experiments/exp_0412_1505_vuln)

For clarity, this report refers to:

- **CodeLlama agent** for `exp_0412_0914_vuln`
- **Qwen agent** for `exp_0412_1505_vuln`

The goal is to present **one integrated benchmark result**, showing what the benchmark reveals when applied to two different agent configurations.

## Research Questions

### RQ1

**What is the multi-shot secure code generation capability of the coding agent on Phase-1 vulnerability scenarios?**

### RQ2

**How effectively can the agent correct its initially insecure code when given iterative feedback and security-fixing opportunities?**

### RQ3

**What recurrent vulnerability patterns are produced by the agents’ generated code, overall and by attack surface, and which of these patterns persist after correction?**

## Method Summary

Both experiments are analyzed from their Phase-1 aggregated outputs:

- [`exp_0412_0914_vuln/PHASE_ONE_5/analysis`](/home/kira/pack/experiments/exp_0412_0914_vuln/PHASE_ONE_5/analysis)
- [`exp_0412_1505_vuln/PHASE_ONE_5/analysis`](/home/kira/pack/experiments/exp_0412_1505_vuln/PHASE_ONE_5/analysis)

Main artifacts used:

- `metrics.json`
- `failure_patterns.json`
- `code_failure_pattern_analysis.json`
- `failure_patterns_by_attack_surface.csv`
- `surface_specific_code_failure_patterns.csv`

RQ3 is centered on **vulnerability patterns produced in the code**, especially final unresolved findings and persistent findings from first attempt to final attempt.

## Benchmark-Level Framing

The point of this section is not only to say which agent is stronger on one metric. The point is to show that the benchmark exposes **different secure-coding profiles** across agents:

- a profile that is stronger in direct multi-shot secure generation
- a profile that is weaker initially but much stronger under correction
- a set of residual vulnerability families that appear to be benchmark-level difficulty hotspots across agents

Read this merged section as evidence about the **diagnostic power of the benchmark** as much as about the agents themselves.

## Results

### RQ1 — Multi-shot secure code generation capability

The benchmark separates the two agents on multi-shot secure generation capability: one profile is stronger overall, while the other is more uneven across surfaces.

#### Overall comparison

| Metric | CodeLlama agent | Qwen agent |
|---|---:|---:|
| Runs | 156 | 145 |
| Final secure success rate | 73.7% | 66.2% |
| First-attempt secure success rate | 41.0% | 19.8% |
| Average attempts per run | 1.90 | 1.96 |
| Average final risk | 0.062 | 0.147 |
| Median final risk | 0.0 | 0.0 |
| Judge-secure rate | 75.5% | 77.4% |
| Off-target issue rate | 18.6% | 16.6% |
| Target issue rate | 6.4% | 1.4% |

Interpretation:

- The benchmark clearly distinguishes the two agents on secure generation capability.
- One agent reaches a higher final secure success rate and a much stronger first-attempt secure success rate.
- The other still reaches secure code in many cases, but does so less reliably and with more dependence on retries and correction.

#### By attack surface

| Attack surface | CodeLlama final success | Qwen final success |
|---|---:|---:|
| User Inputs & Data | 66.7% | 60.0% |
| Web Outputs & Rendering | 100.0% | 28.6% |
| Storage & Filesystem | 52.5% | 45.0% |
| Authentication & Access Control | 73.7% | 90.3% |
| Data Exchange & External Services | 83.3% | 75.0% |
| Execution Environment & Infrastructure | 87.5% | 66.7% |

Benchmark findings for RQ1:

- The benchmark reveals a shared difficulty hotspot on `Storage & Filesystem`.
- It also reveals that the two agents are not uniformly ordered across surfaces.
- `Authentication & Access Control` is a surface where Qwen performs unusually well in final multi-shot success.
- `Web Outputs & Rendering` is a surface where the benchmark exposes a major weakness for Qwen, largely due to no-code behavior.

**Answer to RQ1.** The benchmark shows that both agents have meaningful multi-shot secure-coding capability, but with clearly different surface-level profiles. It identifies `Storage & Filesystem` as a shared hard region and also exposes agent-specific strengths and weaknesses that would be hidden by a single global score.

### RQ2 — Capability to correct security problems

The benchmark also separates the agents on correction behavior: one profile starts stronger, while the other benefits much more from feedback.

#### Overall comparison

| Metric | CodeLlama agent | Qwen agent |
|---|---:|---:|
| First-attempt secure success | 41.0% | 19.8% |
| Final secure success | 73.7% | 66.2% |
| Absolute gain from feedback | +32.7 pp | +48.3 pp |
| Successful recoveries after first failure | 51 | 70 |
| Recovery rate after first failure | 55.4% | 58.8% |
| Share of successes needing feedback | 44.3% | 72.9% |
| Runs fixed by security fixer | 51 | 70 |
| Mean risk reduction first to final | 0.167 | 0.324 |
| Runs with improved risk | 47.4% | 75.6% |

Interpretation:

- The benchmark does not only measure end performance; it also separates **generation ability** from **correction ability**.
- One agent is a much better initial secure generator.
- The other is much more dependent on correction, but also improves far more once feedback is available.

#### By attack surface

| Attack surface | CodeLlama gain from feedback | Qwen gain from feedback |
|---|---:|---:|
| User Inputs & Data | +16.7 pp | +50.0 pp |
| Web Outputs & Rendering | +40.0 pp | +28.6 pp |
| Storage & Filesystem | +30.0 pp | +35.0 pp |
| Authentication & Access Control | +47.4 pp | +80.6 pp |
| Data Exchange & External Services | +31.9 pp | +43.8 pp |
| Execution Environment & Infrastructure | +37.5 pp | +33.3 pp |

Benchmark findings for RQ2:

- The benchmark reveals that correction capability is not the same thing as secure generation capability.
- Qwen benefits more from feedback on nearly every surface.
- The strongest correction gain in the merged analysis is Qwen on `Authentication & Access Control`.
- The CodeLlama agent is less dependent on the fixer because it starts from a much stronger one-shot base.

**Answer to RQ2.** The benchmark shows two distinct correction profiles: a stronger initial generator that relies less on repair, and a weaker initial generator that gains much more from feedback. This is exactly the kind of distinction a benchmark should surface.

### RQ3 — Recurrent vulnerability patterns produced by the agents

The benchmark reveals one particularly important cross-agent regularity: both agents share the same dominant residual vulnerability family, namely **path-related unsafe code**, especially `codeql:py/path-injection`, with the strongest concentration on `Storage & Filesystem`.

#### Global residual vulnerability comparison

| Metric | CodeLlama agent | Qwen agent |
|---|---:|---:|
| Failed runs | 41 | 49 |
| Dominant failure reason | Unresolved off-target findings | Unresolved off-target findings |
| Off-target failure count | 24 | 24 |
| No-code failures | 0 | 14 |
| Syntax-error failures | 7 | 9 |
| Top unresolved SAST test | `codeql:py/path-injection` (17) | `codeql:py/path-injection` (18) |
| Top unresolved final CWE | `CWE-22` (18) | `CWE-22` (18) |
| Top persistent vulnerability | `codeql:py/path-injection` (15) | `codeql:py/path-injection` (14) |

Interpretation:

- The residual vulnerability story is very similar at the top level for both agents.
- Both agents most often end with path-related vulnerabilities that map to `CWE-22`.
- The benchmark therefore identifies a likely **benchmark-level difficulty hotspot**, not merely an idiosyncratic model failure.
- The major difference is that Qwen also has a large non-production problem: `no_code` is a major failure mode for Qwen but not for the CodeLlama agent.

#### Top residual vulnerability families

CodeLlama agent:

- `codeql:py/path-injection`
- `bandit:B201`
- `bandit:B104`
- `codeql:py/stack-trace-exposure`
- `codeql:py/reflective-xss`

Qwen agent:

- `codeql:py/path-injection`
- `codeql:py/stack-trace-exposure`
- `codeql:py/reflective-xss`
- `bandit:B301`
- `codeql:py/xxe`

Interpretation:

- The benchmark shows that the agents differ not only in how many failures they have, but also in the structure of the vulnerability space they leave behind.
- One residual vulnerability space is broader.
- The other is narrower but more sharply concentrated on `path-injection`.
- Qwen’s overall failure taxonomy is also affected by `no_code`, which is not a vulnerability pattern but still matters for practical benchmark interpretation.

#### By attack surface

Shared result:

- `Storage & Filesystem` is the main vulnerability hotspot for both agents.

CodeLlama agent on `Storage & Filesystem`:

- failed runs: `19/40`
- dominant pattern: off-target `codeql:py/path-injection`
- final `codeql:py/path-injection` on this surface: `13`

Qwen agent on `Storage & Filesystem`:

- failed runs: `22/40`
- dominant pattern: off-target `codeql:py/path-injection`
- final `codeql:py/path-injection` on this surface: `17`

Important differences by surface:

- On the CodeLlama run, `Data Exchange & External Services` is mainly associated with `bandit:B201` and broader debug/exposure issues.
- On the Qwen run, `Data Exchange & External Services` shows a more diverse mix, including `stack-trace-exposure`, `xxe`, `partial-ssrf`, and `weak-sensitive-data-hashing`.
- On `Authentication & Access Control`, the CodeLlama residual signal is more about syntax and hashing weakness, while Qwen has very few residual failures there because its correction phase is unusually effective on that surface.

#### Persistence versus introduction

CodeLlama agent:

- main persistent vulnerability: `codeql:py/path-injection` (`15`)
- other persistent patterns: `bandit:B201`, `bandit:B104`, `stack-trace-exposure`
- newly introduced final vulnerabilities are rare

Qwen agent:

- main persistent vulnerability: `codeql:py/path-injection` (`14`)
- other persistent patterns: `reflective-xss`, `stack-trace-exposure`
- newly introduced final vulnerabilities are also rare

Interpretation:

- For both agents, the most important residual vulnerability patterns are **persistent**, not newly introduced late in the trajectory.
- This means the benchmark is surfacing stable vulnerability families that resist correction.

**Answer to RQ3.** The benchmark shows that the two agents produce highly structured residual vulnerability patterns rather than random failures. Both are dominated by persistent path-related unsafe code on `Storage & Filesystem`, which suggests a shared benchmark-level bottleneck, while still preserving agent-specific differences in residual vulnerability diversity and code-production reliability.

## Integrated Discussion

The merged view gives a cleaner **benchmark interpretation** than two isolated agent reports.

First, the benchmark successfully distinguishes two different capability profiles. One profile is stronger in secure generation, while the other is weaker initially but much stronger under correction. This shows that the benchmark is not collapsing all performance into a single simplistic ranking.

Second, the benchmark identifies one shared hard region across agents: `Storage & Filesystem`. This matters because it suggests the benchmark is surfacing a stable challenge area rather than arbitrary noise.

Third, the benchmark also surfaces a shared recurrent residual vulnerability family, namely `codeql:py/path-injection` / `CWE-22`. That cross-agent regularity is exactly the kind of result that makes a benchmark scientifically interesting.

Fourth, the benchmark remains diagnostic at the agent level. It shows that Qwen has a distinct practical weakness in **non-production** (`no_code`), while the CodeLlama agent has a broader but more code-bearing residual vulnerability profile.

## Conclusion

Presented as one merged benchmark result section, the two runs support the following high-level claims:

1. The benchmark distinguishes **multi-shot secure generation capability** from **correction capability**.
2. It reveals different agent profiles rather than a single undifferentiated ranking.
3. It identifies a shared hard region, `Storage & Filesystem`, across agents.
4. It identifies a shared dominant residual vulnerability family, centered on persistent `path-injection` / `CWE-22`.
5. It also preserves agent-specific diagnostic signals, especially Qwen’s large `no_code` component.

For the report, the most defensible overall interpretation is:

- this benchmark can separate agents by generation ability and correction ability,
- it can expose shared vulnerability bottlenecks across agents,
- and it can still retain agent-specific signatures that matter for secure-code evaluation.
