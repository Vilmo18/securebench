# RQ3 Report — `exp_0412_0914_vuln__PHASE_ONE_5`

## Research Question

**RQ3. What recurring reasoning and generation failure patterns explain why LLM-generated code introduces specific CWE vulnerabilities?**

## Dataset Used

- Experiment: `exp_0412_0914_vuln`
- Phase: `PHASE_ONE_5`
- Total runs: `156`
- Failed runs analyzed for RQ3: `41`

Primary data sources:

- `data/exp_0412_0914_vuln__PHASE_ONE_5/failure_patterns.json`
- `data/exp_0412_0914_vuln__PHASE_ONE_5/code_failure_pattern_analysis.json`
- `data/exp_0412_0914_vuln__PHASE_ONE_5/failure_patterns_by_attack_surface.csv`
- `data/exp_0412_0914_vuln__PHASE_ONE_5/surface_specific_code_failure_patterns.csv`
- `data/exp_0412_0914_vuln__PHASE_ONE_5/cwe_specific_code_failure_patterns.csv`

## Short Answer

In this run, failures are explained primarily by **recurring unsafe implementation patterns in the generated code**, not by empty answers or generic refusal. The strongest pattern is **off-target vulnerability introduction**, especially path-handling and debug/exposure issues, with clear concentration on `Storage & Filesystem` and repeated linkage to `CWE-22`-style outcomes.

## Main Finding

The dominant failure mode is **unresolved off-target findings**.

- `24/41` failed runs (`58.5%`) ended with unresolved off-target findings
- `10/41` (`24.4%`) ended with unresolved target findings
- `7/41` (`17.1%`) ended with syntax errors

This is important for RQ3 because it shows that the model often does not simply fail to solve the target vulnerability. Instead, it produces code that introduces or preserves **other unsafe behaviors** while attempting to solve the task.

## Concrete Pattern Evidence

### 1. The most common cross-cutting failure pattern is off-target path injection

Top common code failure patterns across all failed runs:

| Rank | Pattern | Support | Share of failed runs |
|---|---|---:|---:|
| 1 | Off-target `codeql:py/path-injection` | 9 | 22.0% |
| 2 | `syntax_error` | 7 | 17.1% |
| 3 | Off-target `bandit:B201` | 6 | 14.6% |
| 4 | Target `codeql:py/path-injection` persists | 4 | 9.8% |
| 5 | Target `bandit:B104` persists | 3 | 7.3% |

Interpretation:

- The strongest repeated pattern is not a formatting problem.
- The most recurrent implementation mistake is **unsafe path/file handling** that ends up as `codeql:py/path-injection`.
- A second recurring family is **unsafe debug/runtime exposure**, captured by `bandit:B201`.

### 2. Failures cluster around a small set of unresolved findings

Top unresolved SAST tests:

- `codeql:py/path-injection`: `17`
- `bandit:B201`: `10`
- `bandit:B104`: `4`
- `codeql:py/stack-trace-exposure`: `4`
- `codeql:py/reflective-xss`: `4`

Top unresolved final CWEs:

- `CWE-22`: `18`
- `CWE-94`: `10`
- `CWE-209`: `4`
- `CWE-605`: `4`
- `CWE-79`: `4`

Interpretation:

- `CWE-22` is the clearest recurring endpoint of failure in this run.
- `CWE-94` also appears repeatedly through debug and execution-related mistakes rather than only direct target failure.

## By Attack Surface

The failure patterns are not uniform across surfaces.

| Attack surface | Runs | Failed runs | Failed-run rate | Main signal |
|---|---:|---:|---:|---|
| User Inputs & Data | 12 | 4 | 33.3% | Mixed, including path injection and redirect issues |
| Web Outputs & Rendering | 5 | 0 | 0.0% | No failed runs in this sample |
| Storage & Filesystem | 40 | 19 | 47.5% | Strong concentration of path-injection failures |
| Authentication & Access Control | 19 | 5 | 26.3% | Syntax errors and weak hashing issues |
| Data Exchange & External Services | 72 | 12 | 16.7% | Off-target `bandit:B201` dominates |
| Execution Environment & Infrastructure | 8 | 1 | 12.5% | Specific `bandit:B605` signal |

### Surface-specific interpretation

**Storage & Filesystem** is the strongest failure hotspot.

- `19/40` runs failed (`47.5%`)
- `11/19` failed storage runs were dominated by unresolved off-target findings
- The most common storage-specific pattern is off-target `codeql:py/path-injection`
- In storage failures, this pattern appears in `7/19` failed runs on that surface

This is the clearest answer to RQ3 at the surface level: when the model works on storage/file tasks, it repeatedly generates code that remains vulnerable to path-based misuse even when trying to solve another target CWE.

**Authentication & Access Control** shows a different failure type.

- `3/5` failed runs on this surface are `syntax_error`
- This gives `syntax_error` a surface-specific lift of about `3.51`
- There is also a specific off-target hashing weakness: `codeql:py/weak-sensitive-data-hashing`

This suggests that, on auth-related tasks, the model is not only unsafe but also more brittle at the code-construction level.

**Data Exchange & External Services** has lower failure rate but still a stable recurring pattern.

- `12/72` runs failed (`16.7%`)
- `8/12` failures are unresolved off-target findings
- The most common unresolved SAST test on this surface is `bandit:B201`

So this surface is not the most failure-prone overall, but when it fails, it tends to fail in a recognizable and repeated way.

## By Target CWE

The failure patterns also specialize by target CWE.

### `CWE-22`

This is the strongest CWE-specific pattern in the run.

- Top CWE-specific pattern: persistent target `codeql:py/path-injection`
- Support: `4`
- Group share within failed `CWE-22` runs: `22.2%`
- Specificity lift: `2.28`

This means `CWE-22` failures are not random. They are strongly tied to repeated inability to eliminate path-dependent unsafe behavior.

### `CWE-20`

`CWE-20` is associated with several target-side persistence failures rather than one single dominant signature.

- Persistent `bandit:B102`
- Persistent `bandit:B310`
- Persistent `bandit:B201`
- Off-target `codeql:py/stack-trace-exposure`
- Off-target `bandit:B201`

Interpretation:

- For `CWE-20`, the model appears to struggle with a broader secure-coding discipline problem rather than one single recurring API misuse.

### `CWE-287`

`CWE-287` failures show mainly **off-target security regressions**:

- `codeql:py/clear-text-storage-sensitive-data`
- `codeql:py/url-redirection`

So the model’s attempt to solve auth-related tasks can create new exposure elsewhere in the program.

## Role Of The Fixer

The fixer helps substantially, but does not remove the core RQ3 story.

- Eligible fixer runs: `78`
- Top resolved finding: `bandit:B201` with `32` resolutions
- Other frequently resolved findings:
  - `codeql:py/weak-sensitive-data-hashing`: `8`
  - `codeql:py/path-injection`: `7`
  - `bandit:B314`: `6`

Interpretation:

- Many of the recurring failure patterns are at least partly repairable.
- However, the same families still recur enough in final failures to remain diagnostically meaningful.
- This makes them good candidates for future steering, repair prompting, or targeted training data.

## Answer To RQ3

For `exp_0412_0914_vuln__PHASE_ONE_5`, the recurring failure patterns are primarily **unsafe code patterns that survive generation and repair**, not mere output absence.

The most concrete findings are:

1. **Off-target findings dominate failure behavior**, especially `codeql:py/path-injection` and `bandit:B201`.
2. **Storage & Filesystem is the clearest failure hotspot**, with repeated path-injection behavior and the highest failure rate among well-supported surfaces.
3. **Authentication & Access Control fails differently**, showing a strong syntax-error signature rather than only vulnerability persistence.
4. **`CWE-22` has the strongest CWE-specific failure identity**, centered on persistent path-injection behavior.

Taken together, the evidence suggests that near the secure/non-secure boundary, the model’s errors are best explained by a small number of recurring implementation-level security mistakes that generalize across multiple tasks, while still showing strong specialization by attack surface and target CWE.

## Caveats

- This report uses **Phase 1 only**.
- `Web Outputs & Rendering` has only `5` runs, so the absence of failures there should not be over-interpreted.
- Patterns with support `1` and very high `specificity_lift` are useful hints, but not strong conclusions.

## Suggested Figures For The Paper

- `plots/exp_0412_0914_vuln__PHASE_ONE_5/failure_primary_reasons.png`
- `plots/exp_0412_0914_vuln__PHASE_ONE_5/failure_reason_count_by_attack_surface.png`
- `plots/exp_0412_0914_vuln__PHASE_ONE_5/failure_top_unresolved_sast_tests.png`
- `plots/exp_0412_0914_vuln__PHASE_ONE_5/failure_top_unresolved_cwes.png`
