# Benchmark Results Across Three Agent Runs — CodeLlama, Qwen, Granite3.3

2UGPSJMALMDUJZ5JSQNAK4AB

## Scope

This report presents one integrated benchmark result section across three Phase-1 runs:

- CodeLlama run: [`exp_0412_0914_vuln`](/home/kira/pack/experiments/exp_0412_0914_vuln)
- Qwen run: [`exp_0412_1505_vuln`](/home/kira/pack/experiments/exp_0412_1505_vuln)
- Granite3.3 run: [`exp_0412_1918_vuln`](/home/kira/pack/experiments/exp_0412_1918_vuln)

The purpose is not only to rank agents. The purpose is to show what the benchmark reveals when applied to three different agent configurations.

## Research Questions

### RQ1

**What is the multi-shot secure code generation capability of the coding agent on Phase-1 vulnerability scenarios?**

### RQ2

**How effectively can the agent correct its initially insecure code when given iterative feedback and security-fixing opportunities?**

### RQ3

**What recurrent vulnerability patterns are produced by the agents’ generated code, overall and by attack surface, and which of these patterns persist after correction?**

## Method Summary

All three runs are analyzed from their Phase-1 aggregated outputs:

- [`exp_0412_0914_vuln/PHASE_ONE_5/analysis`](/home/kira/pack/experiments/exp_0412_0914_vuln/PHASE_ONE_5/analysis)
- [`exp_0412_1505_vuln/PHASE_ONE_5/analysis`](/home/kira/pack/experiments/exp_0412_1505_vuln/PHASE_ONE_5/analysis)
- [`exp_0412_1918_vuln/PHASE_ONE_5/analysis`](/home/kira/pack/experiments/exp_0412_1918_vuln/PHASE_ONE_5/analysis)

Main artifacts used:

- `metrics.json`
- `failure_patterns.json`
- `code_failure_pattern_analysis.json`
- `failure_patterns_by_attack_surface.csv`
- `surface_specific_code_failure_patterns.csv`

RQ3 is centered on **vulnerability patterns produced in the code**, especially final unresolved findings and persistent findings from first attempt to final attempt.

## Benchmark-Level View

Across three agents, the benchmark exposes three distinct secure-coding profiles:

- **CodeLlama**: strongest secure generation profile overall
- **Qwen**: strongest correction-driven recovery profile
- **Granite3.3**: weakest one-shot secure generation, strongest dependence on repeated repair, and the highest residual difficulty on several surfaces

At the same time, the benchmark reveals one shared cross-agent bottleneck:

- `Storage & Filesystem`
- especially `codeql:py/path-injection`
- mapping strongly to `CWE-22`

That shared pattern is important because it suggests the benchmark is surfacing a stable hard region rather than arbitrary model noise.

## Results

### RQ1 — Multi-shot secure code generation capability

The benchmark distinguishes the three agents clearly on multi-shot secure generation.

#### Overall comparison

| Metric | CodeLlama | Qwen | Granite3.3 |
|---|---:|---:|---:|
| Runs | 156 | 145 | 113 |
| Final secure success rate | 73.7% | 66.2% | 55.8% |
| First-attempt secure success rate | 41.0% | 19.8% | 4.5% |
| Average attempts per run | 1.90 | 1.96 | 2.66 |
| Average final risk | 0.062 | 0.147 | 0.112 |
| Judge-secure rate | 75.5% | 77.4% | 63.6% |

Interpretation:

- CodeLlama is the strongest generator in both final secure success and one-shot secure success.
- Qwen remains competitive in final secure success, but only after substantial repair.
- Granite3.3 is the weakest generator in this benchmark slice, with the lowest final secure success and an almost absent one-shot secure profile.

#### By attack surface

| Attack surface | CodeLlama runs | CodeLlama success | Qwen runs | Qwen success | Granite3.3 runs | Granite3.3 success |
|---|---:|---:|---:|---:|---:|---:|
| User Inputs & Data | 12 | 66.7% | 10 | 60.0% | 16 | 56.3% |
| Web Outputs & Rendering | 5 | 100.0% | 7 | 28.6% | 4 | 75.0% |
| Storage & Filesystem | 40 | 52.5% | 40 | 45.0% | 36 | 30.6% |
| Authentication & Access Control | 19 | 73.7% | 31 | 90.3% | 29 | 82.8% |
| Data Exchange & External Services | 72 | 83.3% | 48 | 75.0% | 14 | 57.1% |
| Execution Environment & Infrastructure | 8 | 87.5% | 9 | 66.7% | 14 | 57.1% |

Benchmark findings for RQ1:

- `Storage & Filesystem` is a shared hard surface across all three agents.
- `Authentication & Access Control` is where both Qwen and Granite3.3 recover to strong final multi-shot performance.
- `Web Outputs & Rendering` is highly agent-sensitive: CodeLlama is perfect in this sample, Qwen is very weak, Granite3.3 is moderate to strong.
- Some surface-level contrasts should be read together with sample size: for example, `Web Outputs & Rendering` remains a very small slice in all three runs, while `Storage & Filesystem` and `Data Exchange & External Services` are much more heavily represented.

#### Supplementary CWE × attack-surface capability table

Cells report **final secure success rate** for **marginal single-CWE Phase-1 runs**, with sample size in parentheses. A dash means that no single-CWE marginal run was observed for that `(model, CWE, surface)` bucket in these three experiments.

| CWE | User Inputs & Data |  |  | Web Outputs & Rendering |  |  | Storage & Filesystem |  |  |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|  | CL | QW | GR | CL | QW | GR | CL | QW | GR |
| CWE-22 | 0.00 (1) | - | 1.00 (2) | 1.00 (1) | 1.00 (1) | - | 0.33 (3) | 0.67 (3) | 0.00 (3) |
| CWE-79 | 1.00 (2) | - | 1.00 (1) | 1.00 (1) | 0.00 (2) | - | 0.67 (3) | 0.50 (2) | - |
| CWE-89 | 1.00 (1) | 0.75 (4) | 1.00 (1) | 1.00 (1) | - | - | 1.00 (1) | 0.20 (5) | 0.50 (2) |
| CWE-287 | 1.00 (1) | 0.50 (2) | - | 1.00 (1) | - | - | 0.67 (3) | 0.40 (5) | 0.00 (2) |
| CWE-502 | - | 0.00 (1) | 0.20 (5) | - | 0.00 (1) | 1.00 (1) | 1.00 (1) | 0.50 (2) | 0.67 (3) |

| CWE | Authentication & Access Control |  |  | Data Exchange & External Services |  |  | Execution Environment & Infrastructure |  |  |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|  | CL | QW | GR | CL | QW | GR | CL | QW | GR |
| CWE-22 | 1.00 (1) | 1.00 (1) | 1.00 (2) | 0.50 (2) | 0.75 (4) | - | 1.00 (1) | 0.00 (1) | 1.00 (1) |
| CWE-79 | 0.67 (3) | 1.00 (3) | 1.00 (1) | 0.94 (17) | 1.00 (2) | 0.00 (1) | 1.00 (1) | 0.50 (2) | - |
| CWE-89 | 1.00 (1) | 0.80 (5) | 1.00 (2) | 1.00 (4) | 1.00 (3) | 0.67 (6) | 0.67 (3) | 1.00 (1) | 0.00 (1) |
| CWE-287 | 1.00 (1) | 1.00 (4) | 0.50 (2) | 0.75 (4) | 0.89 (9) | - | 1.00 (1) | - | - |
| CWE-502 | 0.00 (1) | 1.00 (2) | 0.67 (3) | 1.00 (4) | 0.00 (2) | 0.67 (3) | 1.00 (1) | 0.00 (1) | 0.75 (4) |

**Answer to RQ1.** The benchmark reveals three different multi-shot secure-generation profiles. CodeLlama is the strongest overall generator, Qwen is intermediate, and Granite3.3 is the weakest. The most consistent benchmark-level bottleneck is `Storage & Filesystem`.

### RQ2 — Capability to correct security problems

The benchmark separates generation ability from correction ability even more sharply when Granite3.3 is included.

#### Overall comparison

| Metric | CodeLlama | Qwen | Granite3.3 |
|---|---:|---:|---:|
| First-attempt secure success | 41.0% | 19.8% | 4.5% |
| Final secure success | 73.7% | 66.2% | 55.8% |
| Absolute gain from feedback | +32.7 pp | +48.3 pp | +51.3 pp |
| Successful recoveries after first failure | 51 | 70 | 58 |
| Recovery rate after first failure | 55.4% | 58.8% | 53.7% |
| Share of successes needing feedback | 44.3% | 72.9% | 92.1% |
| Runs fixed by security fixer | 51 | 70 | 58 |
| Mean risk reduction first to final | 0.167 | 0.324 | 0.757 |
| Runs with improved risk | 47.4% | 75.6% | 92.9% |

Interpretation:

- CodeLlama is the least dependent on correction because it starts from the strongest one-shot base.
- Qwen has a strong correction profile and gains substantially from feedback.
- Granite3.3 is the most correction-dependent profile in the benchmark: almost all of its successful outcomes require feedback.

#### By attack surface

| Attack surface | CodeLlama (`before -> after`) | Qwen (`before -> after`) | Granite3.3 (`before -> after`) |
|---|---|---|---|
| User Inputs & Data | `50.0% -> 66.7%` (`+16.7 pp`, `n=12`) | `10.0% -> 60.0%` (`+50.0 pp`, `n=10`) | `6.2% -> 56.3%` (`+50.0 pp`, `n=16`) |
| Web Outputs & Rendering | `60.0% -> 100.0%` (`+40.0 pp`, `n=5`) | `0.0% -> 28.6%` (`+28.6 pp`, `n=7`) | `0.0% -> 75.0%` (`+75.0 pp`, `n=4`) |
| Storage & Filesystem | `22.5% -> 52.5%` (`+30.0 pp`, `n=40`) | `10.0% -> 45.0%` (`+35.0 pp`, `n=40`) | `2.8% -> 30.6%` (`+27.8 pp`, `n=36`) |
| Authentication & Access Control | `26.3% -> 73.7%` (`+47.4 pp`, `n=19`) | `9.7% -> 90.3%` (`+80.6 pp`, `n=31`) | `0.0% -> 82.8%` (`+82.8 pp`, `n=29`) |
| Data Exchange & External Services | `51.4% -> 83.3%` (`+31.9 pp`, `n=72`) | `31.2% -> 75.0%` (`+43.8 pp`, `n=48`) | `0.0% -> 57.1%` (`+57.1 pp`, `n=14`) |
| Execution Environment & Infrastructure | `50.0% -> 87.5%` (`+37.5 pp`, `n=8`) | `33.3% -> 66.7%` (`+33.3 pp`, `n=9`) | `21.4% -> 57.1%` (`+35.7 pp`, `n=14`) |

Benchmark findings for RQ2:

- The benchmark clearly separates agents that are good at generating secure code from agents that are good at recovering under feedback.
- Qwen and Granite3.3 both gain far more from repair than CodeLlama.
- The strongest correction gains in the benchmark appear on `Authentication & Access Control`, especially for Qwen and Granite3.3.
- `Storage & Filesystem` still improves substantially after feedback, but it remains the hardest shared surface even after repair.

**Answer to RQ2.** The benchmark reveals a spectrum of correction dependence. CodeLlama is the strongest initial secure generator, Qwen is a strong correction-driven profile, and Granite3.3 is the most repair-dependent of the three.

### RQ3 — Recurrent vulnerability patterns produced by the agents

The benchmark reveals one especially strong cross-agent regularity: all three agents converge on **path-related unsafe code** as the dominant residual vulnerability family.

#### Global residual vulnerability comparison

| Metric | CodeLlama | Qwen | Granite3.3 |
|---|---:|---:|---:|
| Failed runs | 41 | 49 | 50 |
| Dominant failure reason | Off-target findings | Off-target findings | Off-target findings |
| Off-target failure count | 24 | 24 | 26 |
| No-code failures | 0 | 14 | 1 |
| Syntax-error failures | 7 | 9 | 13 |
| Top unresolved SAST test | `path-injection` (17) | `path-injection` (18) | `path-injection` (19) |
| Top unresolved final CWE | `CWE-22` (18) | `CWE-22` (18) | `CWE-22` (19) |
| Top persistent vulnerability | `path-injection` (15) | `path-injection` (14) | `path-injection` (5) |

Interpretation:

- The benchmark repeatedly surfaces `codeql:py/path-injection` / `CWE-22` as the dominant residual vulnerability family across all three agents.
- This is strong evidence of a benchmark-level hard region.
- Agent-specific differences remain important: Qwen has a large `no_code` component, while Granite3.3 has stronger syntax-related failure pressure.

#### Top residual vulnerability families

CodeLlama:

- `codeql:py/path-injection`
- `bandit:B201`
- `bandit:B104`
- `codeql:py/stack-trace-exposure`
- `codeql:py/reflective-xss`

Qwen:

- `codeql:py/path-injection`
- `codeql:py/stack-trace-exposure`
- `codeql:py/reflective-xss`
- `bandit:B301`
- `codeql:py/xxe`

Granite3.3:

- `codeql:py/path-injection`
- `codeql:py/reflective-xss`
- `codeql:py/polynomial-redos`
- `codeql:py/stack-trace-exposure`
- `codeql:py/url-redirection`

Interpretation:

- CodeLlama leaves the broadest residual vulnerability spectrum.
- Qwen leaves a narrower spectrum but is heavily affected by no-code failures.
- Granite3.3 combines a strong path-injection concentration with additional residual signatures like `polynomial-redos` and `reflective-xss`.

#### By attack surface

Residual surface profile (`failed runs / total runs`, followed by dominant residual pattern):

| Attack surface | CodeLlama | Qwen | Granite3.3 |
|---|---|---|---|
| User Inputs & Data | `4/12`; `path-injection` / `CWE-22` | `4/10`; `B301` / `CWE-502` | `7/16`; `polynomial-redos` / `CWE-1333` |
| Web Outputs & Rendering | `0/5`; no residual vulnerability pattern | `5/7`; `B301` / `CWE-502` with dominant `no_code` failures | `1/4`; no dominant residual SAST family, mostly `syntax_error` |
| Storage & Filesystem | `19/40`; `path-injection` / `CWE-22` | `22/40`; `path-injection` / `CWE-22` | `25/36`; `path-injection` / `CWE-22` |
| Authentication & Access Control | `5/19`; `weak-sensitive-data-hashing` / `CWE-327` | `3/31`; `reflective-xss` / `CWE-79` with dominant `no_code` failures | `5/29`; `reflective-xss` / `CWE-79` |
| Data Exchange & External Services | `12/72`; `B201` with broad off-target spread including `CWE-22` | `12/48`; `stack-trace-exposure` / `CWE-209` with `xxe` and `partial-ssrf` also present | `6/14`; `B314` / `CWE-20` with `stack-trace-exposure` also present |
| Execution Environment & Infrastructure | `1/8`; `B605` / `CWE-78` | `3/9`; no dominant residual SAST family, mostly `syntax_error` | `6/14`; `clear-text-logging-sensitive-data` / `CWE-312` |

Benchmark-level surface findings:

- `Storage & Filesystem` is the only surface where all three agents converge on the same dominant residual family, `codeql:py/path-injection` / `CWE-22`, making it the clearest shared hard region.
- `Data Exchange & External Services` is the broadest residual surface for Qwen, where exposure-style findings such as `stack-trace-exposure`, `xxe`, and `partial-ssrf` accumulate.
- `User Inputs & Data` is where Granite3.3 shows its most distinctive agent-specific residual pattern, `codeql:py/polynomial-redos`.
- `Authentication & Access Control` is relatively strong in final success for Qwen and Granite3.3, but their remaining failures still concentrate around web-style output issues such as `reflective-xss`.
- Some surfaces mix vulnerability residuals with reliability failures: for Qwen, `Web Outputs & Rendering` and `Authentication & Access Control` are partly shaped by `no_code`, while for Granite3.3 `Web Outputs & Rendering` and `Execution Environment & Infrastructure` retain a syntax-driven component.

#### Persistence versus introduction

CodeLlama:

- main persistent vulnerability: `codeql:py/path-injection` (`15`)
- residual patterns are mostly persistent rather than newly introduced

Qwen:

- main persistent vulnerability: `codeql:py/path-injection` (`14`)
- newly introduced final vulnerabilities are rare

Granite3.3:

- main persistent vulnerability: `codeql:py/path-injection` (`5`)
- introduced findings exist but remain small in number

Interpretation:

- For all three agents, the benchmark primarily surfaces **stable vulnerability families** rather than large volumes of newly introduced late-stage issues.
- Persistent path-related unsafe code remains the clearest cross-agent benchmark signal.

**Answer to RQ3.** The benchmark shows that all three agents produce highly structured residual vulnerability patterns rather than random failures. The dominant cross-agent pattern is persistent path-related unsafe code on `Storage & Filesystem`, while Qwen and Granite3.3 additionally expose agent-specific reliability and vulnerability signatures.

## Integrated Discussion

The three-agent view strengthens the benchmark contribution.

First, the benchmark clearly does **not** collapse the agents into a single ordering across all dimensions. Instead, it separates:

- secure generation strength
- correction dependence
- residual vulnerability structure

Second, the benchmark identifies one shared hard region across all agents: `Storage & Filesystem`. That is a strong signal that the benchmark is surfacing a meaningful security difficulty zone.

Third, the benchmark identifies one shared dominant residual vulnerability family across all agents: `codeql:py/path-injection` / `CWE-22`. This is precisely the kind of stable, interpretable cross-agent phenomenon that makes a benchmark scientifically useful.

Fourth, the benchmark remains diagnostic at the agent level:

- CodeLlama stands out as the strongest direct generator.
- Qwen stands out as a strong correction-driven profile with a pronounced `no_code` weakness.
- Granite3.3 stands out as the most repair-dependent profile and the weakest initial secure generator, while still sharing the same cross-agent storage/path bottleneck.

## Conclusion

Presented as one merged benchmark result section, the three runs support the following high-level claims:

1. The benchmark distinguishes **multi-shot secure generation capability** from **correction capability**.
2. It reveals three different agent profiles rather than a single undifferentiated ranking.
3. It identifies a shared hard region, `Storage & Filesystem`, across CodeLlama, Qwen, and Granite3.3.
4. It identifies a shared dominant residual vulnerability family, centered on persistent `codeql:py/path-injection` / `CWE-22`.
5. It also preserves agent-specific signatures, especially Qwen’s `no_code` issue and Granite3.3’s extreme dependence on iterative repair.

For the report, the most defensible overall interpretation is:

- this benchmark can separate agents by generation ability and correction ability,
- it can expose shared vulnerability bottlenecks across agents,
- and it can retain agent-specific residual signatures that matter for secure-code evaluation.
