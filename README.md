# PrismBench LLM Capability Mapping Framework

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![OpenAI API](https://img.shields.io/badge/OpenAI-API-green.svg)](https://platform.openai.com/docs/guides/text-generation)
[![Hugging Face](https://img.shields.io/badge/Hugging%20Face-Inference-yellow.svg)](https://huggingface.co/docs/inference-providers/index)


PrismBench is an LLM capability mapping framework designed to assess and understand the strengths and weaknesses of LLM models in computer science problem-solving. The framework operates in three distinct phases, each building upon the previous to provide a comprehensive analysis of the model's capabilities.

## Table of Contents
- [Overview](#overview)
- [Quick Start](#quick-start)
  - [Setting up the environment variables](#setting-up-the-environment-variables)
  - [Selecting the models](#selecting-the-models)
  - [Running the PrismBench Framework](#running-the-prismbench-framework)
- [Program Flow](#program-flow)
- [Monte Carlo Tree Search](#monte-carlo-tree-search-mcts)
  - [Core MCTS Process](#core-mcts-process)
  - [Key Components](#key-components)
- [Phases](#phases)
  - [Phase 1 - Initial Capability Mapping](#phase-1---initial-capability-mapping)
  - [Phase 2 - Challenge Discovery](#phase-2---challenge-discovery)
  - [Phase 3 - Comprehensive Evaluation](#phase-3---comprehensive-evaluation)
- [Configuration Variables](#configuration-variables)
  - [Environment Variables in `configs.yml`](#environment-variables-in-configsyml)
  - [Agent Roles in `agent_config_v7.yml`](#agent-roles-in-agent_config_v7yml)
- [Analysis Pipeline](#analysis-pipeline)

## Overview

PrismBench systematically evaluates an LLM model by generating coding challenges, assessing the model's solutions, and analyzing performance across various computer science concepts and difficulty levels.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/CommissarSilver/PrismBench.git
cd PrismBench

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # Unix
.\.venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

If your virtualenv is created **without** `pip` (common on Debian/Ubuntu when `python3-venv` is missing), bootstrap it:

```bash
curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
.venv/bin/python /tmp/get-pip.py
.venv/bin/python -m pip install -r requirements.txt
```

### Setting up the environment variables
This migrated copy uses [Hugging Face Inference Providers](https://huggingface.co/docs/inference-providers/index) through its OpenAI-compatible chat endpoint. Create a fine-grained Hugging Face token with permission to call Inference Providers.

Add `HF_TOKEN` to the copied `.env`; `.env.example` is a safe reference template:

```bash
HF_TOKEN=hf_your_token_here
HUGGINGFACE_BASE_URL=https://router.huggingface.co/v1
DEEPSEEK_API_KEY=your_deepseek_api_key
```

### Selecting the models
Select models in `agent_config_v7.yml` for benchmark mode and `agent_config_vul.yml` for vulnerability mode. Hugging Face roles must include `provider: huggingface` and use a model ID exposed by the Inference Providers router. The migrated defaults use `openai/gpt-oss-20b:fastest` for design and analysis, and `Qwen/Qwen2.5-Coder-32B-Instruct:fastest` for code generation and repair.

### Running the PrismBench Framework
To run the PrismBench framework, you can use the following command:

```bash
python src/main.py
```

### Running the SAST-based Vulnerability Mode (PrismVul)
PrismBench also includes a vulnerability benchmarking mode that uses SAST (CodeQL by default) instead of unit tests.

```bash
pip install -r requirements.txt
python src/main.py --mode vuln
```

You can customize the CWE concept list in `data/cwe_database.yml` and SAST settings in `configs.yml` (tool + thresholds + CodeQL/Semgrep settings).

Example:

```yaml
sast:
  tool: codeql
  severity_threshold: LOW
  confidence_threshold: LOW
  timeout_seconds: 300
  codeql:
    # Optional: set a CodeQL CLI path if it's not on PATH.
    # path: tools/codeql/codeql
    language: python
    build_mode: none
    threads: 0
    # Where CodeQL should look for QL packs (recommended: a local checkout of github/codeql).
    search_path: tools/codeql-repo
    queries:
      - codeql/python-queries:Security/CWE-078/CommandInjection.ql
      - codeql/python-queries:Security/CWE-089/SqlInjection.ql
      - codeql/python-queries:Security/CWE-502/UnsafeDeserialization.ql
      # ... see configs.yml for the full curated list, or use the full suite:
      # - tools/codeql-repo/python/ql/src/codeql-suites/python-security-extended.qls
    # Set to true only if you have GHCR access (requires GITHUB_TOKEN).
    download_packs: false
  semgrep:
    # You can provide a single config or a list of configs.
    config:
      - p/security-audit
      - semgrep_rules.yml
```

#### Installing CodeQL CLI (Linux)
CodeQL is an external CLI (not a pip package). You can install it into `tools/codeql/`:

```bash
bash scripts/install_codeql.sh
export PATH="$PWD/tools/codeql:$PATH"
codeql version
```

#### Installing CodeQL query packs (required)
The CodeQL CLI download does **not** include query packs by default. To run CodeQL without authenticating to GHCR,
install the open-source query packs by cloning `github/codeql` into `tools/codeql-repo/`:

```bash
bash scripts/install_codeql_queries.sh
```

This script checks out a `github/codeql` tag matching your installed CodeQL CLI version.

If you prefer GHCR downloads instead, set `GITHUB_TOKEN` and set `download_packs: true` in `configs.yml`.

Optional (GHCR): pre-download packs into your CodeQL cache:

```bash
export GITHUB_TOKEN="<YOUR_TOKEN>"
bash scripts/download_codeql_packs.sh
```

#### LLM-as-judge (recommended)
SAST can miss issues or produce false positives. Vulnerability mode can optionally use an LLM-as-judge to
evaluate security and refine the reward signal (enabled by default).

Configure in `configs.yml`:

```yaml
judge:
  enabled: true
  mode: review_only        # review_only|review_and_detect
  success_policy: judge_only   # judge_only|judge_and_sast|sast_only
  combine_mode: weighted       # weighted|max
  judge_weight: 0.35
```

The judge also **reviews SAST findings** via `sast_review` and the runner filters findings flagged as likely
false positives before scoring / fixing. Raw scans are still preserved in run artifacts as `sast_raw.json`.

#### Console output (generated code + SAST output)
Vulnerability mode prints the generated code and SAST findings to the console by default. You can toggle what gets printed in `configs.yml`:

```yaml
vuln_console:
  enabled: true
  show_problem: false
  show_code: true
  show_sast_output: true
  show_sast_json: false
```

#### Metrics + plots (paper-ready)
After a run, a single run directory is created under `experiments/` (e.g. `experiments/exp_<timestamp>_vuln/`), with one subfolder per phase:

- `PHASE_ONE_<max_depth>/`
- `PHASE_TWO_<max_depth>/`
- `PHASE_THREE/`

Generate metrics and plots for a single experiment:

```bash
python src/vuln_report.py --experiment experiments/<RUN_DIR>/PHASE_THREE
```

Or analyze all `PHASE_*` experiments under `experiments/` (recursively):

```bash
python src/vuln_report.py --experiments-dir experiments --out experiments/vuln_summary
```

Compare multiple runs/models (Table-2 style capability table):

```bash
python src/vuln_report.py --compare-experiments experiments/<EXP1> experiments/<EXP2> --out experiments/vuln_compare
```

Outputs:
- `analysis/metrics.json` (aggregates + rankings)
- `analysis/records.csv` (per-run records)
- `analysis/failure_patterns.json` + `analysis/failure_patterns.csv` (behavioral failure reasons + unresolved patterns)
- `analysis/plots/` (PNG+SVG, if `matplotlib` is installed)

To generate a **small Prism-style plot set** (and optionally “retire” the noisy plot folder), run:

```bash
python scripts/make_prism_plots_vuln.py --experiment-dir experiments/<RUN_DIR>_vuln
python scripts/make_prism_plots_vuln.py --experiment-dir experiments/<RUN_DIR>_vuln --curate
```

`--curate` archives the original `PHASE_THREE/analysis/plots/` to `plots_full_<timestamp>/` and recreates
`PHASE_THREE/analysis/plots/` with a curated, paper-ready subset (plus `README.md` + `curation_manifest.json`).

To generate a **Prism-style CWE capability table** (failure rate by difficulty group) from a vuln run:

```bash
python scripts/plot_cwe_capability_table_vuln.py \
  --experiments experiments/<RUN_DIR>_vuln \
  --phase phase_1 \
  --out-prefix cwe_capability_phase_1
```


## Program Flow

1. **Initialization**: The environment and tree structures are set up based on the configuration files.
2. **Phase 1 Execution**: The MCTS algorithm maps the model's initial capabilities.
3. **Phase 2 Execution**: The algorithm identifies challenging concept combinations where the model underperforms.
4. **Phase 3 Execution**: A comprehensive evaluation is conducted on the challenging areas.
5. **Results Analysis**: The system compiles performance metrics, error analyses, and actionable insights.

## Monte Carlo Tree Search (MCTS)

Monte Carlo Tree Search (MCTS) is a probabilistic search algorithm that combines tree search principles with random sampling to find optimal decisions. It is particularly effective in domains with large state spaces where traditional exhaustive search is impractical.

### Core MCTS Process
MCTS iteratively builds a search tree through four key steps:

1. **Selection**: Starting from the root, navigate through the tree using a selection policy (like UCB1) that balances exploration and exploitation until reaching a leaf node.

2. **Expansion**: Create one or more child nodes from the selected leaf node to explore new states.

3. **Simulation**: From the new node, perform a "rollout" by simulating random actions until reaching a terminal state or predefined depth.

4. **Backpropagation**: Update the statistics (visits and values) of all nodes along the path from the simulated node back to the root.

### Key Components

Node Statistics:

- Visit count: Times node was traversed
- Value: Aggregated results from simulations
- Children: Available next states

## Phases

### Phase 1 - Initial Capability Mapping

- **Objective**: Understand the model's basic capabilities across different concepts.
- **Process**:
  - Uses a Monte Carlo Tree Search (MCTS) to explore various concepts and difficulties.
  - Simulates challenges to gather performance data.
  - Builds an initial tree structure representing the model's strengths.
- **Outcome**: A broad understanding of the model's performance, highlighting areas of proficiency.

![ Phase 1 Diagram](./images/phase1.png)
```mermaid
flowchart TD
    Start1[Start Phase 1] --> SelectNode1[Select Node]
    SelectNode1 --> Simulate1[Simulate Challenge]
    Simulate1 --> Score1[Calculate Score]
    Score1 --> Backprop1[Backpropagate Results]
    Backprop1 --> Expand1{Should Expand?}
    Expand1 -->|Yes| CreateChild1[Create Child Node]
    CreateChild1 --> CheckConv1[Check Convergence]
    Expand1 -->|No| CheckConv1
    CheckConv1 -->|Not Converged| SelectNode1
    CheckConv1 -->|Converged| End1[End Phase 1]
```

### Phase 1: Initial MCTS
Focuses on broad exploration of concept space:
- Runs until value convergence is achieved
- Node selection uses inverse probability distribution to favor less-explored nodes 
- Score calculation considers:
  - Challenge success/failure
  - Number of tests passed
  - Penalties for failures, errors, and multiple attempts
  - Difficulty level weighting
- Node expansion occurs when:
  - Node value exceeds performance threshold
  - Node depth is below maximum
- Expansion happens by either:
  - Combining with another node to add new concepts
  - Increasing difficulty level
---

### Phase 2 - Challenge Discovery

- **Objective**: Identify areas where the model struggles.
- **Process**:
  - Takes the Phase 1 tree as input.
  - Focuses on nodes where performance is below a certain threshold.
  - Explores combinations of concepts that are challenging for the model.
- **Outcome**: A collection of challenging concept combinations for further analysis.

![ Phase 2 Diagram](./images/phase2.png)
```mermaid
flowchart TD
    Start2[Start Phase 2] --> LoadP1[Load Phase 1 Tree]
    LoadP1 --> SelectNode2[Select Low Performance Node]
    SelectNode2 --> Simulate2[Simulate Variations]
    Simulate2 --> Score2[Calculate Challenge Score]
    Score2 --> Backprop2[Backpropagate Results]
    Backprop2 --> Expand2{Challenge Score > Threshold?}
    Expand2 -->|Yes| Record[Record Challenge Combination]
    Record --> CheckMore2[Check More Nodes]
    Expand2 -->|No| CheckMore2
    CheckMore2 -->|Continue| SelectNode2
    CheckMore2 -->|Complete| End2[End Phase 2]
```

### Phase 2: Concept MCTS 
Focuses on finding challenging concept combinations:
- Uses UCB (Upper Confidence Bound) with challenge metrics
- Challenge score calculation considers:
  - Inverse success rate
  - Number of attempts needed
  - Whether fixes were required
- Node expansion prioritizes:
  - Combinations exceeding challenge threshold
  - Increasing difficulty for challenging nodes
  - Adding new concepts for non-challenging nodes
- Maintains a record of challenging combinations with their scores

---

### Phase 3 - Comprehensive Evaluation

- **Objective**: Deeply understand the model's challenges.
- **Process**:
  - Generates multiple variations of challenging problems identified in Phase 2.
  - Runs extensive testing using an enhanced environment.
  - Collects detailed performance data.
- **Outcome**: In-depth insights into the model's weaknesses, ready for detailed analysis.

![ Phase 3 Diagram](./images/phase3.png)    
```mermaid
flowchart LR
Start3[Start Phase 3] --> LoadChallenges[Load Challenge Combinations]
LoadChallenges --> GenVar[Generate Problem Variations]
GenVar --> RunTests[Run Enhanced Tests]
RunTests --> Analyze[Analyze Performance]
Analyze --> CollectMetrics[Collect Metrics]
CollectMetrics --> GenReport[Generate Report]
GenReport --> End3[End Phase 3]
```

### Phase 3: Comprehensive MCTS
Focuses on detailed evaluation of challenging areas:
- Takes challenging nodes identified in Phase 2
- Generates multiple problem variations per concept combination
- Records detailed challenge descriptions and results
- Maintains full history of:
  - Problem statements
  - Solution attempts
  - Test cases
  - Performance metrics

## Configuration Variables

Configuration variables are defined in `agent_config_v7.yml` and `configs.yml`. They control various aspects of the system's behavior.

### Environment Variables in `configs.yml`:

- **Global Constants**:
  - `max_attempts`: Maximum number of attempts the model has to solve a challenge.
  - `discount_factor`: Discount factor used in backpropagation during MCTS.
  - `learning_rate`: Learning rate for updating node values.

- **Phase 1 Settings**:
  - `performance_threshold`: Minimum node value to consider for expansion.
  - `value_delta_threshold`: Threshold to determine convergence based on value changes.
  - `convergence_checks`: Number of iterations to confirm convergence.
  - `exploration_probability`: Probability of exploring new nodes randomly.

- **Scoring Parameters**:
  - `penalty_per_failure`: Penalty for each failed test.
  - `penalty_per_error`: Penalty for each error encountered.
  - `penalty_per_attempt`: Penalty for each additional attempt after the first.
  - `fixed_by_problem_fixer_penalty`: Additional penalty if the solution needed fixing.

- **Phase 2 Settings**:
  - `challenge_threshold`: Threshold to consider a concept combination challenging.
  - `convergence_checks`: Number of iterations to confirm convergence.
  - `value_delta_threshold`: Threshold to determine convergence based on value changes.
  - `exploration_weight`: Weight given to exploration in UCB calculation.
  - `exploration_probability`: Probability of exploring new nodes in Phase 2.

- **Phase 3 Settings**:
  - `variations_per_concept`: Number of variations to generate per concept combination.
  - `node_selection_threshold`: Threshold for selecting nodes based on challenge score.

### Agent Roles in `agent_config_v7.yml`

Agents define specialized roles for generating prompts and processing responses.

- **challenge_designer**:
  - **Role**: Creates coding challenges focused on specific CS concepts and difficulty levels.
  - **Template**: Designs problems similar to LeetCode challenges, ensuring they match the specified concept and difficulty.

- **challenge_designer_advanced**:
  - **Role**: Generates new and unique coding challenges, avoiding duplication.
  - **Template**: Ensures problems are substantially different from previous ones while maintaining the same concepts.

- **test_generator**:
  - **Role**: Develops comprehensive unittest test cases for coding problems.
  - **Template**: Creates test suites covering a range of scenarios from very easy to very hard.

- **problem_solver**:
  - **Role**: Implements efficient and well-structured solutions to coding problems.
  - **Template**: Provides a single Python function named `solution` that adheres to problem specifications.

- **problem_fixer**:
  - **Role**: Analyzes failing solutions to identify issues and provides corrections.
  - **Template**: Offers a corrected version of the code enclosed within specific delimiters.

- **test_validator**:
  - **Role**: Validates test cases to ensure they properly verify problem requirements.
  - **Template**: Checks for coverage, correctness, and adherence to best practices.

- **test_error_analyzer**:
  - **Role**: Analyzes test execution outputs to provide insights into failures.
  - **Template**: Identifies failed tests, analyzes errors, and suggests areas for investigation.

- **solution_pattern_analyzer**:
  - **Role**: Reviews solution code to identify patterns and implementation approaches.
  - **Template**: Provides a structured JSON report highlighting algorithm choices, data structures, and coding patterns.

## Analysis Pipeline
Once the benchmarking is finished after running `src/main.py`, the terminal will display:

```bash
MCTS Phase 3 completed
```
Afterwards, the entire analysis pipeline can be run with the following command:

```bash
python src/phase_one_report.py
```

This will provide analysis on the metrics outlined in [Benchmark Metrics](/benchmark_metrics.md). The results will be available in full JSON files alongside charts that visualize the model's performance for each of the described metrics. The structure of the JSON files in outlined in [Comparative Analysis](/comparative%20analysis.md). 
# securebench
