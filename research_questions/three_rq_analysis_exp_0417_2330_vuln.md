# Three-RQ Analysis Report — `exp_0417_2330_vuln`

## Scope

This report analyzes the experiment [`exp_0417_2330_vuln`](/home/kira/pack/experiments/exp_0417_2330_vuln), using the aggregated outputs in [`PHASE_ONE_5/analysis`](/home/kira/pack/experiments/exp_0417_2330_vuln/PHASE_ONE_5/analysis).

The main goal is to answer the three benchmark research questions on this run:

- `RQ1`: multi-shot secure code generation capability
- `RQ2`: correction capability under iterative feedback
- `RQ3`: recurrent vulnerability patterns produced by the generated code

One methodological note matters up front: in this run, the generic `difficulty` field in [`records.csv`](/home/kira/pack/experiments/exp_0417_2330_vuln/PHASE_ONE_5/analysis/records.csv) is normalized to `unknown`, so the attack-surface analysis is derived from `condition_axis`, [`failure_patterns_by_attack_surface.csv`](/home/kira/pack/experiments/exp_0417_2330_vuln/PHASE_ONE_5/analysis/failure_patterns_by_attack_surface.csv), and [`failure_reason_by_attack_surface.csv`](/home/kira/pack/experiments/exp_0417_2330_vuln/PHASE_ONE_5/analysis/failure_reason_by_attack_surface.csv).

The experiment artifacts also do not preserve the final `problem_solver` / `security_fixer` model names in the aggregated report files, so this document characterizes the run itself rather than attaching it to a named backbone.

## Scientifically Refined Research Questions

### RQ1

**What is the multi-shot secure code generation capability of the coding agent on Phase-1 vulnerability scenarios?**

Operationalization:

- success criterion: final run judged secure with no unresolved findings after the allowed attempt budget
- objective: estimate how often the agent can eventually produce secure code in a multi-shot setting
- supporting indicators: final `success_rate`, first-attempt secure rate, attempt distribution, and surface-level success rates

### RQ2

**How effectively can the agent correct its initially insecure code when given iterative feedback and security-fixing opportunities?**

Operationalization:

- compare first-attempt secure success against final secure success
- measure recovery after initially insecure first attempts
- use fixer usage, risk delta, and surface-specific gains as evidence of correction capability

### RQ3

**What recurrent vulnerability patterns are produced by the agent’s generated code, overall and by attack surface, and which of these patterns persist after correction?**

Operationalization:

- analyze unresolved SAST findings and unresolved CWE labels in the final code state
- use deterministic `code_failure_pattern_analysis`
- distinguish target vs off-target residual findings
- stratify by attack surface to identify recurring surface-specific vulnerability families

## Data And Method

Primary sources:

- [`metrics.json`](/home/kira/pack/experiments/exp_0417_2330_vuln/PHASE_ONE_5/analysis/metrics.json)
- [`records.csv`](/home/kira/pack/experiments/exp_0417_2330_vuln/PHASE_ONE_5/analysis/records.csv)
- [`failure_patterns.json`](/home/kira/pack/experiments/exp_0417_2330_vuln/PHASE_ONE_5/analysis/failure_patterns.json)
- [`code_failure_pattern_analysis.json`](/home/kira/pack/experiments/exp_0417_2330_vuln/PHASE_ONE_5/analysis/code_failure_pattern_analysis.json)
- [`failure_patterns_by_attack_surface.csv`](/home/kira/pack/experiments/exp_0417_2330_vuln/PHASE_ONE_5/analysis/failure_patterns_by_attack_surface.csv)
- [`surface_specific_code_failure_patterns.csv`](/home/kira/pack/experiments/exp_0417_2330_vuln/PHASE_ONE_5/analysis/surface_specific_code_failure_patterns.csv)

Core sample characteristics:

- Total Phase-1 runs: `294`
- Failed runs analyzed for RQ3: `82`
- Unique target CWE labels covered: `7`
- CWEs with at least one success: `7`
- Tree nodes: `230`
- Max tree depth: `6`

Methodological highlight:

- This run has a notably balanced surface allocation:
  - `44` runs on `User Inputs & Data`
  - `50` on `Web Outputs & Rendering`
  - `52` on `Storage & Filesystem`
  - `54` on `Authentication & Access Control`
  - `50` on `Data Exchange & External Services`
  - `44` on `Execution Environment & Infrastructure`
- This matters because the surface-level comparisons in this run are less distorted by major sampling imbalance than in earlier runs with highly skewed surface counts.

## RQ1 — Multi-Shot Secure Code Generation Capability

The multi-shot secure generation capability in this run is **substantial overall, but sharply heterogeneous across surfaces**.

Main results:

- Final secure success rate: `72.1%` (`212/294`)
- First-attempt secure success rate: `43.5%`
- Average attempts per run: `1.86`
- Average final risk: `0.066`
- Median final risk: `0.0`
- Judge-secure rate: `74.4%`

Interpretation:

- The pipeline can often reach a secure final solution within the allowed attempt budget.
- However, the gap between `43.5%` one-shot security and `72.1%` final security shows that this is not a robust one-shot generator.
- The balanced surface coverage makes the surface-level capability differences more meaningful in this run than in heavily skewed runs.

### Multi-shot capability by attack surface

| Attack surface | Runs | First-attempt secure rate | Final secure rate | Gain |
|---|---:|---:|---:|---:|
| Web Outputs & Rendering | 50 | 54.0% | 90.0% | +36.0 pp |
| Execution Environment & Infrastructure | 44 | 43.2% | 70.5% | +27.3 pp |
| User Inputs & Data | 44 | 52.3% | 70.5% | +18.2 pp |
| Authentication & Access Control | 54 | 25.9% | 87.0% | +61.1 pp |
| Storage & Filesystem | 52 | 36.5% | 46.2% | +9.6 pp |
| Data Exchange & External Services | 50 | 52.0% | 68.0% | +16.0 pp |

RQ1 conclusion:

- The strongest final multi-shot secure capability appears on `Web Outputs & Rendering` and `Authentication & Access Control`.
- The weakest final capability is clearly `Storage & Filesystem`, where the final secure success rate is only `46.2%`.
- `Storage & Filesystem` is therefore not just a one-shot weakness; it remains a hard region even after multiple attempts.

### Capability by target CWE

| Target CWE | Runs | First-attempt secure rate | Final secure rate | Avg. risk |
|---|---:|---:|---:|---:|
| CWE-22 | 41 | 46.3% | 80.5% | 0.047 |
| CWE-89 | 163 | 42.3% | 72.4% | 0.059 |
| CWE-78 | 243 | 42.0% | 72.0% | 0.069 |
| CWE-502 | 32 | 50.0% | 71.9% | 0.068 |
| CWE-20 | 267 | 42.3% | 71.5% | 0.067 |
| CWE-79 | 234 | 40.2% | 70.5% | 0.070 |
| CWE-287 | 32 | 37.5% | 59.4% | 0.139 |

Interpretation:

- `CWE-287` is the weakest target family in this run, with the lowest final success and the highest average risk.
- `CWE-22` looks easier in aggregate than expected, but this should be interpreted carefully: the same run still shows `CWE-22` as the dominant residual vulnerability family when failures occur.
- So `CWE-22` is not globally rare; it is specifically the **dominant residual failure mode** in certain surfaces, especially storage-related ones.

### Capability by combination size

| Combo size | Runs | First-attempt secure rate | Final secure rate | Avg. risk |
|---|---:|---:|---:|---:|
| 1 | 27 | 55.6% | 77.8% | 0.063 |
| 2 | 29 | 51.7% | 72.4% | 0.038 |
| 3 | 25 | 48.0% | 76.0% | 0.065 |
| 4 | 213 | 40.4% | 70.9% | 0.071 |

Interpretation:

- Larger concept combinations are somewhat harder, but the degradation is moderate rather than catastrophic.
- The dominant challenge in this run is not only combination size; it is the interaction between combination size and specific surfaces, especially `Storage & Filesystem`.

## RQ2 — Capability To Correct Security Problems

The correction loop is **highly valuable**, but its effectiveness is very uneven across surfaces.

Main results:

- One-shot secure success rate: `43.5%`
- Final secure success rate: `72.1%`
- Absolute gain from feedback: `+28.6` percentage points
- Average attempts per run: `1.86`
- Fixer usage rate: `28.6%`
- Mean risk reduction from first to final attempt: `0.146`
- Runs with improved risk: `45.6%`

This means the correction loop is genuinely important in this run, but less dominant than in the most repair-heavy runs we saw before.

### Correction gains by attack surface

| Attack surface | One-shot rate | Final rate | Gain from feedback | Runs fixed by fixer |
|---|---:|---:|---:|---:|
| Web Outputs & Rendering | 54.0% | 90.0% | +36.0 pp | 18 |
| Execution Environment & Infrastructure | 43.2% | 70.5% | +27.3 pp | 12 |
| User Inputs & Data | 52.3% | 70.5% | +18.2 pp | 8 |
| Authentication & Access Control | 25.9% | 87.0% | +61.1 pp | 33 |
| Storage & Filesystem | 36.5% | 46.2% | +9.6 pp | 5 |
| Data Exchange & External Services | 52.0% | 68.0% | +16.0 pp | 8 |

Interpretation:

- `Authentication & Access Control` is the strongest correction story in the run: it starts weak and ends very strong.
- `Web Outputs & Rendering` also benefits strongly from feedback.
- `Storage & Filesystem` barely improves, with only `+9.6` points and only `5` fixer recoveries. This is the strongest evidence that storage is a **deep capability bottleneck**, not merely a repair gap.

### What the fixer resolves most often

Top findings frequently resolved by the repair loop:

- `bandit:B201`: `66`
- `codeql:py/weak-sensitive-data-hashing`: `14`
- `codeql:py/path-injection`: `9`
- `bandit:B602`: `6`
- `codeql:py/flask-debug`: `4`
- `codeql:py/reflective-xss`: `4`
- `codeql:py/stack-trace-exposure`: `4`
- `bandit:B314`: `4`

Interpretation:

- The fixer is particularly strong on frequent static-analysis issues like `bandit:B201`.
- It can also resolve some path-related issues, but the residual statistics show that path injection remains far from solved overall.

RQ2 conclusion:

- This run demonstrates a meaningful correction capability, but one that is highly surface-dependent.
- The correction loop is powerful on `Authentication & Access Control` and useful on `Web Outputs & Rendering`.
- It is comparatively weak on `Storage & Filesystem`, which remains the clearest residual bottleneck after feedback.

## RQ3 — Recurrent Vulnerability Patterns Produced By The Agent

RQ3 focuses on the `82` failed runs that remain after the full generation-and-feedback loop.

### Global structure of produced residual vulnerabilities

Primary failure reasons:

- `unresolved_off_target_findings`: `52` (`63.4%`)
- `syntax_error`: `15` (`18.3%`)
- `unresolved_target_findings`: `15` (`18.3%`)

Interpretation:

- The main residual problem is not failure to satisfy the target CWE only.
- The dominant failure mode is the production of **off-target vulnerabilities** in the generated code.
- This means the agent often “solves” part of the intended task but leaves or introduces a different security weakness.

### Dominant residual vulnerability findings

Top unresolved SAST tests in final code:

- `codeql:py/path-injection`: `32`
- `bandit:B201`: `12`
- `codeql:py/reflective-xss`: `6`
- `codeql:py/stack-trace-exposure`: `5`
- `bandit:B104`: `3`
- `bandit:B314`: `3`

Top unresolved final CWE labels:

- `CWE-22`: `32`
- `CWE-94`: `13`
- `CWE-79`: `6`
- `CWE-78`: `5`
- `CWE-209`: `5`

Interpretation:

- `CWE-22` / `path-injection` is the dominant residual vulnerability family in this run by a wide margin.
- The second recurrent family is code-execution / unsafe-evaluation style risk (`CWE-94`, `bandit:B201`).
- So the run reveals one very strong path-handling bottleneck and one secondary family around unsafe execution/debug behavior.

### Most common recurring code failure patterns

| Rank | Pattern | Support | Share of failed runs | Dominant surface |
|---|---|---:|---:|---|
| 1 | Off-target `codeql:py/path-injection` | 27 | 32.9% | Storage & Filesystem |
| 2 | `syntax_error` | 15 | 18.3% | Authentication & Access Control |
| 3 | Off-target `bandit:B201` | 8 | 9.8% | User Inputs & Data |
| 4 | Off-target `codeql:py/stack-trace-exposure` | 5 | 6.1% | Data Exchange & External Services |
| 5 | Persistent target `codeql:py/reflective-xss` | 5 | 6.1% | Storage & Filesystem |
| 6 | Off-target `bandit:B104` | 3 | 3.7% | Execution Environment & Infrastructure |
| 7 | Persistent target `bandit:B314` | 3 | 3.7% | Data Exchange & External Services |

Interpretation:

- The strongest recurrent code failure pattern is clearly path injection.
- Syntax errors remain a non-negligible residual failure channel, especially in auth-related scenarios.
- The rest of the residual families are more surface-specific and less globally dominant.

### Vulnerability patterns by attack surface

| Attack surface | Failed runs / total | Failed-run rate | Dominant reason | Dominant residual signal |
|---|---:|---:|---|---|
| User Inputs & Data | 13 / 44 | 29.5% | Off-target findings | `codeql:py/path-injection` / `CWE-22` |
| Web Outputs & Rendering | 5 / 50 | 10.0% | Mixed off-target and target findings | `bandit:B201`, `bandit:B608`, `reflective-xss` |
| Storage & Filesystem | 28 / 52 | 53.8% | Off-target findings | `codeql:py/path-injection` / `CWE-22` |
| Authentication & Access Control | 7 / 54 | 13.0% | Syntax errors | `bandit:B108` / `CWE-377` among vuln findings |
| Data Exchange & External Services | 16 / 50 | 32.0% | Off-target findings | `codeql:py/stack-trace-exposure` / `CWE-209` |
| Execution Environment & Infrastructure | 13 / 44 | 29.5% | Off-target findings | `bandit:B605` / `CWE-78` |

Key surface-level findings:

- `Storage & Filesystem` is by far the hardest region in this run, with the highest failed-run rate and the strongest concentration of `path-injection`.
- `Authentication & Access Control` is interestingly dual-natured:
  - it has excellent final success after correction
  - but among residual failures, syntax errors dominate more than vulnerability families
- `Data Exchange & External Services` is marked by stack-trace exposure and some persistent unsafe dynamic behavior (`bandit:B314`).
- `Execution Environment & Infrastructure` shows a more execution-centric failure profile, including `bandit:B605`, `bandit:B602`, and `semgrep:...subprocess-shell-true`.

### Surface-specific top patterns

Top deterministic surface-specific pattern per surface:

- `User Inputs & Data`: off-target `codeql:py/weak-sensitive-data-hashing`
- `Web Outputs & Rendering`: persistent target `bandit:B608`
- `Storage & Filesystem`: persistent target `codeql:py/path-injection`
- `Authentication & Access Control`: off-target `codeql:py/log-injection`
- `Data Exchange & External Services`: persistent target `bandit:B314`
- `Execution Environment & Infrastructure`: off-target `semgrep:prismvul.python.subprocess-shell-true`

Interpretation:

- These surface-specific top patterns are useful diagnostically, but they are all much weaker than the global storage/path-injection signal.
- So the run is best characterized by **one dominant shared hard region** plus several weaker surface-local signatures.

RQ3 conclusion:

- The dominant recurrent vulnerability pattern in this run is `codeql:py/path-injection` / `CWE-22`, especially in `Storage & Filesystem`.
- The second large residual family is unsafe execution / code-injection related behavior, especially through `bandit:B201` and `CWE-94`.
- The residual error profile is therefore not random: it is highly structured, and strongly concentrated in storage/path handling.

## Overall Interpretation

This run paints a clear picture:

- **RQ1**: the agent has substantial multi-shot secure coding capability overall (`72.1%`), but remains weak on `Storage & Filesystem`.
- **RQ2**: iterative feedback materially improves outcomes, especially on `Authentication & Access Control`, but has limited impact on storage-related failures.
- **RQ3**: the dominant residual vulnerability family is `path-injection` / `CWE-22`, and the dominant global failure mode is off-target vulnerability production.

Methodologically, this run is also important because the per-surface run counts are tightly clustered (`44` to `54`). That makes the surface-level conclusions more trustworthy than in highly imbalanced runs. In that sense, this experiment provides one of the cleaner per-surface reads of the benchmark so far.

## Threats To Validity

- The run-level report does not preserve model identifiers in the aggregate artifacts, so this document cannot attribute the observed profile to a named backbone without external run bookkeeping.
- The generic `difficulty` field is not informative in this run; attack-surface analysis relies on `condition_axis` and dedicated surface-level CSV outputs.
- RQ3 is centered on final residual vulnerability patterns, not a full attempt-by-attempt trajectory analysis.
- The run is still search-conditioned: even with balanced surface counts, the explored tasks depend on the benchmark’s adaptive tree dynamics.

## Final Answer To The Three RQs

- **RQ1**: the agent can often produce secure code in a multi-shot setting, but storage-related scenarios remain a major capability gap.
- **RQ2**: the agent can correct many initial security problems, especially in auth-related scenarios, but correction is much less effective on storage/path tasks.
- **RQ3**: the most recurrent residual vulnerability pattern is `path-injection` / `CWE-22`, concentrated in `Storage & Filesystem`, with unsafe execution and stack-trace exposure as secondary families.
