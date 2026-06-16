import inspect
import math
import json
import os
import random
from collections import Counter
from datetime import datetime
from typing import Any, Dict, Optional

import yaml
from loguru import logger

from environment import CodingChallengeEnvironment, EnhancedCodingChallengeEnvironment
from issue_snippets import build_issue_snippets
from node import ChallengeNode
from attack_surface_conditions import attack_surface_rank, normalize_attack_surface
from scenario_conditions import condition_axis_label, condition_rank, normalize_condition
from tree import Tree

# Load configurations from YAML file as global constants

with open(
    os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)),
        "configs.yml",
    ),
    "r",
    encoding="utf-8",
) as f:
    configs = yaml.safe_load(f)

# Global constants
MAX_ATTEMPTS = configs["max_attempts"]
DISCOUNT_FACTOR = configs["discount_factor"]

# Phase 1 evaluation settings (capability mapping)
_PHASE1_CFG = configs.get("phase1", {}) if isinstance(configs, dict) else {}
PHASE_ONE_ONE_SHOT = bool(_PHASE1_CFG.get("one_shot", False))
PHASE_ONE_MAX_ATTEMPTS = int(_PHASE1_CFG.get("max_attempts", MAX_ATTEMPTS) or MAX_ATTEMPTS)
PHASE_ONE_ALLOW_FIXER = bool(_PHASE1_CFG.get("allow_fixer", True))
if PHASE_ONE_ONE_SHOT:
    PHASE_ONE_MAX_ATTEMPTS = 1
    PHASE_ONE_ALLOW_FIXER = False

# Phase 1 configurations
PHASE_ONE_PERFORMANCE_THRESHOLD = configs["phase1"]["performance_threshold"]
PHASE_ONE_VALUE_DELTA_THRESHOLD = configs["phase1"]["value_delta_threshold"]
PHASE_ONE_CONVERGENCE_CHECKS = configs["phase1"]["convergence_checks"]
PHASE_ONE_EXPLORATION_PROBABILITY = configs["phase1"]["exploration_probability"]
PHASE_ONE_SURFACE_BALANCE_WEIGHT = float(
    _PHASE1_CFG.get("surface_balance_weight", 0.0) or 0.0
)

# Phase 1 scoring parameters
PENALTY_PER_FAILURE = configs["phase1"]["scoring"]["penalty_per_failure"]
PENALTY_PER_ERROR = configs["phase1"]["scoring"]["penalty_per_error"]
PENALTY_PER_ATTEMPT = configs["phase1"]["scoring"]["penalty_per_attempt"]
FIXED_BY_PROBLEM_FIXER_PENALTY = configs["phase1"]["scoring"][
    "fixed_by_problem_fixer_penalty"
]
MAX_NUM_PASSED = configs["phase1"]["scoring"]["max_num_passed"]

# Phase 2 configurations
PHASE_TWO_VALUE_DELTA_THRESHOLD = configs["phase2"]["value_delta_threshold"]
PHASE_TWO_CONVERGENCE_CHECKS = configs["phase2"]["convergence_checks"]
CHALLENGE_THRESHOLD = configs["phase2"]["challenge_threshold"]
EXPLORATION_WEIGHT = configs["phase2"]["exploration_weight"]
PHASE_TWO_EXPLORATION_PROBABILITY = configs["phase2"]["exploration_probability"]
_PHASE2_CFG = configs.get("phase2", {}) if isinstance(configs, dict) else {}
_PHASE2_SCORING = (_PHASE2_CFG.get("scoring", {}) if isinstance(_PHASE2_CFG, dict) else {}) or {}
PHASE_TWO_LAMBDA = float(_PHASE2_SCORING.get("lambda", 0.5))
PHASE_TWO_GAMMA = float(_PHASE2_SCORING.get("gamma", 0.3))
PHASE_TWO_BETA = float(_PHASE2_SCORING.get("beta", 0.2))

# Phase 3 configurations
VARIAITONS_PER_CONCEPT = configs["phase3"]["variations_per_concept"]
NODE_SELECTION_THRESHOLD = configs["phase3"]["node_selection_threshold"]

class BaseMCTS:
    """
    A base class for Monte Carlo Tree Search implementations.
    Contains common methods and attributes shared by MCTS variants.
    """

    def __init__(
        self,
        environment: CodingChallengeEnvironment,
        tree: Tree,
        max_depth: int,
        iterations: int,
    ):
        self.environment = environment
        self.tree = tree
        self.max_depth = max_depth
        self.iterations = iterations
        self.experiment_path: Optional[str] = None
        self.surface_balance_weight = 0.0

    def set_experiment_path(self, path: str) -> None:
        self.experiment_path = path
        try:
            os.makedirs(os.path.join(path, "runs"), exist_ok=True)
        except Exception:
            # Non-fatal; visualization/tree pickles are still useful.
            logger.opt(exception=True).warning("Failed to create runs artifact directory.")
        try:
            setter = getattr(self.environment, "set_experiment_path", None)
            if callable(setter):
                setter(path)
        except Exception:
            logger.opt(exception=True).warning("Failed to propagate experiment path to environment.")

    def _run_challenge(self, node: ChallengeNode) -> Dict[str, Any]:
        return self.environment.run_challenge(
            concept=node.concepts,
            difficulty_level=node.difficulty,
            max_attempts=MAX_ATTEMPTS,
        )

    def _save_run_artifacts(
        self, node: ChallengeNode, result: Dict[str, Any], run_index: Optional[int] = None
    ) -> None:
        if not self.experiment_path:
            return

        run_index = run_index or (len(node.run_results) + 1)
        base_dir = os.path.join(self.experiment_path, "runs", f"node_{id(node)}")
        run_dir = os.path.join(base_dir, f"run_{run_index:04d}")

        try:
            os.makedirs(run_dir, exist_ok=True)

            label = getattr(node, "condition_label", None) or getattr(node, "difficulty", None)
            attack_surface = normalize_attack_surface(label)
            if attack_surface == "unknown":
                attack_surface = None
            resolved_condition_axis = getattr(node, "condition_axis", None)
            resolved_condition_label = getattr(node, "condition_label", None)
            resolved_condition_rank = getattr(node, "condition_rank", None)
            if attack_surface:
                resolved_condition_axis = resolved_condition_axis or attack_surface
                resolved_condition_label = resolved_condition_label or attack_surface
                resolved_condition_rank = (
                    resolved_condition_rank if resolved_condition_rank is not None else attack_surface_rank(attack_surface)
                )
            else:
                resolved_condition_axis = resolved_condition_axis or condition_axis_label(
                    getattr(node, "difficulty", None)
                )
                resolved_condition_label = resolved_condition_label or normalize_condition(
                    getattr(node, "difficulty", None)
                )
                resolved_condition_rank = (
                    resolved_condition_rank
                    if resolved_condition_rank is not None
                    else condition_rank(label)
                )
            meta = {
                "node_id": id(node),
                "phase": getattr(node, "phase", None),
                "difficulty": getattr(node, "difficulty", None),
                "attack_surface": attack_surface,
                "condition_axis": resolved_condition_axis,
                "condition_label": resolved_condition_label,
                "condition_rank": resolved_condition_rank,
                "difficulty_normalized": normalize_condition(
                    getattr(node, "condition_label", None) or getattr(node, "difficulty", None)
                ),
                "concepts": getattr(node, "concepts", None),
                "success": result.get("success"),
                "attempts_till_success": result.get("attempts_till_success"),
                "total_issues": result.get("total_issues")
                if result.get("total_issues") is not None
                else (result.get("sast", {}) or {}).get("total_issues")
                if isinstance(result.get("sast"), dict)
                else None,
            }

            # Human-readable files
            problem = result.get("problem_statement") or ""
            code = result.get("solution_code") or ""
            output = result.get("output") or ""
            sast = result.get("sast")
            sast_raw = result.get("sast_raw")
            scenario_path = None

            with open(os.path.join(run_dir, "meta.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)

            if problem:
                problem_path = os.path.join(run_dir, "problem.md")
                with open(problem_path, "w", encoding="utf-8") as f:
                    f.write(problem)
                scenario_path = os.path.join(run_dir, "scenario.md")
                with open(scenario_path, "w", encoding="utf-8") as f:
                    f.write(problem)

            if code:
                with open(os.path.join(run_dir, "solution.py"), "w", encoding="utf-8") as f:
                    f.write(code)

            if output:
                with open(
                    os.path.join(run_dir, "sast_output.txt"), "w", encoding="utf-8"
                ) as f:
                    f.write(output)

            if isinstance(sast, dict):
                with open(os.path.join(run_dir, "sast.json"), "w", encoding="utf-8") as f:
                    json.dump(sast, f, indent=2, ensure_ascii=False)

            if isinstance(sast_raw, dict):
                with open(os.path.join(run_dir, "sast_raw.json"), "w", encoding="utf-8") as f:
                    json.dump(sast_raw, f, indent=2, ensure_ascii=False)

            judge = result.get("judge")
            if isinstance(judge, dict):
                with open(os.path.join(run_dir, "judge.json"), "w", encoding="utf-8") as f:
                    json.dump(judge, f, indent=2, ensure_ascii=False)

            failure_pattern = result.get("failure_pattern")
            if isinstance(failure_pattern, dict):
                with open(
                    os.path.join(run_dir, "failure_pattern.json"),
                    "w",
                    encoding="utf-8",
                ) as f:
                    json.dump(failure_pattern, f, indent=2, ensure_ascii=False)

            failure_steering = result.get("failure_steering")
            if isinstance(failure_steering, dict):
                failure_steering_path = os.path.join(run_dir, "failure_steering.json")
                with open(failure_steering_path, "w", encoding="utf-8") as f:
                    json.dump(failure_steering, f, indent=2, ensure_ascii=False)

                failure_code = str(failure_steering.get("final_code") or code or "")
                failure_code_path = None
                if failure_code.strip() and not bool(result.get("success")):
                    failure_code_path = os.path.join(run_dir, "failure_code.py")
                    with open(failure_code_path, "w", encoding="utf-8") as f:
                        f.write(failure_code)

                failure_bank_entry = {
                    "run_dir": run_dir,
                    "scenario_path": scenario_path,
                    "problem_statement": problem,
                    "failure_steering_path": failure_steering_path,
                    "failure_code_path": failure_code_path,
                    **meta,
                    "primary_reason": failure_steering.get("primary_reason"),
                    "detail": failure_steering.get("detail"),
                    "target_cwes": failure_steering.get("target_cwes"),
                    "attack_surface": failure_steering.get("attack_surface") or attack_surface,
                    "final_test_ids": failure_steering.get("final_test_ids"),
                    "final_cwe_ids": failure_steering.get("final_cwe_ids"),
                    "persistent_test_ids": failure_steering.get("persistent_test_ids"),
                    "introduced_test_ids": failure_steering.get("introduced_test_ids"),
                    "steering_summary": failure_steering.get("steering_summary"),
                }
                with open(
                    os.path.join(self.experiment_path, "failure_bank.jsonl"),
                    "a",
                    encoding="utf-8",
                ) as f:
                    f.write(json.dumps(failure_bank_entry, ensure_ascii=False) + "\n")

            pattern_analysis = result.get("pattern_analysis")
            if isinstance(pattern_analysis, dict):
                with open(
                    os.path.join(run_dir, "pattern_analysis.json"),
                    "w",
                    encoding="utf-8",
                ) as f:
                    json.dump(pattern_analysis, f, indent=2, ensure_ascii=False)

            if code and isinstance(sast, dict):
                try:
                    issues = sast.get("issues") or []
                    issues = [i for i in issues if isinstance(i, dict)]
                    fps = sast.get("false_positives") or []
                    fps = [i for i in fps if isinstance(i, dict)]

                    payload = {
                        "tool": sast.get("tool"),
                        "total_issues": sast.get("total_issues"),
                        "issue_snippets": build_issue_snippets(code, issues, radius=2, max_issues=50),
                        "false_positive_snippets": build_issue_snippets(code, fps, radius=2, max_issues=50),
                    }
                    with open(
                        os.path.join(run_dir, "issue_snippets.json"),
                        "w",
                        encoding="utf-8",
                    ) as f:
                        json.dump(payload, f, indent=2, ensure_ascii=False)
                except Exception:
                    # Best-effort, should not break experiments.
                    pass

            # Full machine-readable record
            with open(os.path.join(run_dir, "result.json"), "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            # Per-attempt artifacts when present
            data_trail = result.get("data_trail")
            if isinstance(data_trail, dict) and data_trail:
                attempts_dir = os.path.join(run_dir, "attempts")
                os.makedirs(attempts_dir, exist_ok=True)
                for k, details in data_trail.items():
                    try:
                        attempt_num = int(k) + 1
                    except Exception:
                        attempt_num = str(k)

                    if not isinstance(details, dict):
                        continue

                    attempt_code = details.get("solution_code") or ""
                    if attempt_code:
                        with open(
                            os.path.join(attempts_dir, f"attempt_{attempt_num}_solution.py"),
                            "w",
                            encoding="utf-8",
                        ) as f:
                            f.write(attempt_code)

                    attempt_sast = details.get("sast")
                    if isinstance(attempt_sast, dict):
                        with open(
                            os.path.join(attempts_dir, f"attempt_{attempt_num}_sast.json"),
                            "w",
                            encoding="utf-8",
                        ) as f:
                            json.dump(attempt_sast, f, indent=2, ensure_ascii=False)

                    attempt_sast_raw = details.get("sast_raw")
                    if isinstance(attempt_sast_raw, dict):
                        with open(
                            os.path.join(attempts_dir, f"attempt_{attempt_num}_sast_raw.json"),
                            "w",
                            encoding="utf-8",
                        ) as f:
                            json.dump(attempt_sast_raw, f, indent=2, ensure_ascii=False)

                    attempt_judge = details.get("judge")
                    if isinstance(attempt_judge, dict):
                        with open(
                            os.path.join(attempts_dir, f"attempt_{attempt_num}_judge.json"),
                            "w",
                            encoding="utf-8",
                        ) as f:
                            json.dump(attempt_judge, f, indent=2, ensure_ascii=False)

            # Append index line to simplify lookup
            index_line = {
                "run_dir": run_dir,
                **meta,
            }
            with open(
                os.path.join(self.experiment_path, "runs_index.jsonl"),
                "a",
                encoding="utf-8",
            ) as f:
                f.write(json.dumps(index_line, ensure_ascii=False) + "\n")

        except Exception:
            logger.opt(exception=True).warning("Failed to write run artifacts.")

    def select_node(self) -> ChallengeNode:
        """
        Selects a node to explore based on a probability distribution inversely proportional
        to their values to favor less-explored nodes.

        Returns:
            ChallengeNode: The node selected for simulation.
        """
        scores = [node.value for node in self.tree.nodes]
        surface_counts = self._surface_counts()

        # At the start, select a node randomly as all have zero scores
        if all(value == 0 for value in scores):
            weights = self._surface_balance_weights(self.tree.nodes, surface_counts)
            node = random.choices(self.tree.nodes, weights)[0]
        else:
            inverse_scores = [1 / (score + 1e-10) for score in scores]
            balance_weights = self._surface_balance_weights(self.tree.nodes, surface_counts)
            weighted_scores = [a * b for a, b in zip(inverse_scores, balance_weights)]
            if sum(weighted_scores) <= 0:
                node = random.choice(self.tree.nodes)
            else:
                node = random.choices(self.tree.nodes, weighted_scores)[0]

        # Traverse to a leaf node
        while node.children:
            if self.should_explore():
                weights = self._surface_balance_weights(node.children, surface_counts)
                node = random.choices(node.children, weights)[0]
                logger.debug(f"Randomly selected child node: {node.concepts}")
            else:
                node = self.select_best_child(node)
                logger.debug(f"Selected child node using strategy: {node.concepts}")
        return node

    def _surface_key(self, node: ChallengeNode) -> str:
        label = getattr(node, "condition_label", None) or getattr(node, "difficulty", None)
        normalized = normalize_attack_surface(label)
        return normalized or (label or "unknown")

    def _surface_counts(self) -> Counter:
        counts: Counter = Counter()
        for node in self.tree.nodes:
            counts[self._surface_key(node)] += 1
        return counts

    def _surface_balance_weights(
        self, nodes: list[ChallengeNode], counts: Counter
    ) -> list[float]:
        if self.surface_balance_weight <= 0:
            return [1.0 for _ in nodes]
        weights: list[float] = []
        for node in nodes:
            count = max(1, counts[self._surface_key(node)])
            weights.append(1.0 / (count ** self.surface_balance_weight))
        return weights

    def _surface_distribution_summary(self, max_items: int = 6) -> str:
        counts = self._surface_counts()
        total = sum(counts.values()) or 1
        items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        parts = [f"{name}:{count} ({count / total:.1%})" for name, count in items[:max_items]]
        return " | ".join(parts)

    def should_explore(self) -> bool:
        """
        Determines whether to explore randomly or exploit based on the exploration probability.

        Returns:
            bool: True if exploring, False otherwise.
        """
        return random.random() < self.exploration_probability

    def select_best_child(
        self,
        node: ChallengeNode,
        *,
        children: Optional[list[ChallengeNode]] = None,
    ) -> ChallengeNode:
        """
        Selects the best child node based on UCB1 or other criteria.

        Args:
            node (ChallengeNode): The parent node.

        Returns:
            ChallengeNode: The selected child node.
        """
        return max(children or node.children, key=lambda n: n.ucb1())

    def simulate(
        self,
        node: ChallengeNode,
    ) -> float:
        """
        Simulates the execution of a node by running a coding challenge and calculates the score.

        Args:
            node (ChallengeNode): The node to simulate.

        Returns:
            float: The normalized score obtained from the simulation.
        """
        logger.debug(
            f"Simulating node: Condition={node.condition_label or node.difficulty}, Concepts={node.concepts}"
        )
        challenge_results = self._run_challenge(node)
        self._save_run_artifacts(node, challenge_results, run_index=len(node.run_results) + 1)
        self.update_node_data(node, challenge_results)
        score = self.calculate_score(
            challenge_results,
            node.difficulty,
        )  # different for each phase
        node.run_results.append(challenge_results)
        logger.debug(f"Simulation completed with score: {score:.2f}")
        return score

    def update_node_data(
        self,
        node: ChallengeNode,
        results: Dict,
    ) -> None:
        """
        Updates the node with the results from the challenge simulation.

        Args:
            node (ChallengeNode): The node to update.
            results (Dict): The results from the challenge simulation.
        """
        node.challenge_description = results.get("problem_statement", "")
        data_trail = results.get("data_trail", {})
        for attempt_num, attempt_details in data_trail.items():
            for field in ["problem_statement", "solution_code", "test_cases"]:
                data = attempt_details.get(field, [])
                getattr(node, field).setdefault(attempt_num, []).append(data)

    def backpropagate(
        self,
        node: ChallengeNode,
        reward: float,
        gamma: float = DISCOUNT_FACTOR,
    ) -> None:
        """
        Backpropagates the reward up the tree using a discount factor.

        Args:
            node (ChallengeNode): The node where backpropagation starts.
            reward (float): The reward to propagate.
            gamma (float): The discount factor applied at each step.
        """
        node.update_node_score(reward)
        for parent_node in node.parents or []:
            discounted_reward = reward * gamma
            self.backpropagate(
                parent_node,
                discounted_reward,
                gamma,
            )

    def save_progress(self, path: str, iteration: str) -> None:
        """
        Saves the current state of the tree and its visualization.

        Args:
            path (str): The directory path where the files will be saved.
            iteration (str): The current iteration number or 'final'.
        """
        self.tree.save_tree(file_name=os.path.join(path, f"tree_{iteration}"))
        self.tree.visualize_tree(file_name=os.path.join(path, f"tree_{iteration}"))


class MCTS(BaseMCTS):
    def __init__(
        self,
        environment: CodingChallengeEnvironment,
        tree: Tree,
        max_depth: int = 10,
        iterations: int = 100,
    ) -> None:
        super().__init__(environment, tree, max_depth, iterations)
        self.performance_threshold = PHASE_ONE_PERFORMANCE_THRESHOLD
        self.convergence_threshold = PHASE_ONE_VALUE_DELTA_THRESHOLD
        self.convergence_checks = PHASE_ONE_CONVERGENCE_CHECKS
        self.exploration_probability = PHASE_ONE_EXPLORATION_PROBABILITY
        self.surface_balance_weight = PHASE_ONE_SURFACE_BALANCE_WEIGHT

    def _run_challenge(self, node: ChallengeNode) -> Dict[str, Any]:
        """
        Phase 1 simulation.

        By default we mirror Prism-style capability mapping: one-shot evaluation (no correction loop / fixer)
        when `phase1.one_shot: true` in configs.yml.
        """
        kwargs = {
            "concept": node.concepts,
            "difficulty_level": node.difficulty,
            "max_attempts": PHASE_ONE_MAX_ATTEMPTS,
        }
        run_challenge = self.environment.run_challenge
        try:
            supports_allow_fixer = (
                "allow_fixer" in inspect.signature(run_challenge).parameters
            )
        except (TypeError, ValueError):
            supports_allow_fixer = False

        if supports_allow_fixer:
            return run_challenge(**kwargs, allow_fixer=PHASE_ONE_ALLOW_FIXER)
        return run_challenge(**kwargs)

    def run(self) -> None:
        """
        Runs the MCTS algorithm until convergence based on value changes.

        The algorithm iteratively selects nodes, simulates them, and backpropagates the results.
        It expands nodes when certain criteria are met and stops when the value changes across
        iterations fall below a specified threshold for a number of consecutive checks.
        """
        logger.info("Starting MCTS Phase 1 - run until convergence")
        path = self.experiment_path
        if not path:
            timestamp = datetime.now().strftime("%m%d_%H%M")
            experiment_name = f"{timestamp}_PHASE_ONE_{self.max_depth}"
            path = os.path.join(os.getcwd(), "experiments", experiment_name)
        os.makedirs(path, exist_ok=True)
        self.set_experiment_path(path)

        self.no_change_iterations = 0
        iteration = 0

        while True:
            iteration += 1
            logger.debug(f"Iteration {iteration}")
            try:
                node = self.select_node()
                prev_value = node.value
                reward = self.simulate(node)
                self.backpropagate(node, reward)

                value_delta = abs(node.value - prev_value)
                logger.debug(f"Value delta for node {node.concepts}: {value_delta:.4f}")

                # Check convergence criterion
                if value_delta < self.convergence_threshold:
                    self.no_change_iterations += 1
                    if self.no_change_iterations >= self.convergence_checks:
                        logger.info("Convergence achieved based on value changes")
                        break
                else:
                    self.no_change_iterations = 0

                # Attempt to expand node if criteria met
                self.attempt_node_expansion(node)

                if iteration % 10 == 0:
                    logger.info(
                        f"Surface distribution: {self._surface_distribution_summary()}"
                    )
                    self.save_progress(path, iteration)
            except Exception as e:
                logger.exception(f"An error occurred during iteration {iteration}: {e}")
                continue

        logger.info("MCTS run completed")
        self.save_progress(path, "final")

    def attempt_node_expansion(self, node: ChallengeNode) -> None:
        """
        Attempts to expand the node repeatedly while it meets the criteria.

        Args:
            node (ChallengeNode): The node to attempt expansion on.
        """
        while self.should_expand_node(node):
            node = self.expand_node(node)
            prev_value = node.value
            reward = self.simulate(node)
            self.backpropagate(node, reward)

            value_delta = abs(node.value - prev_value)
            logger.debug(f"Value delta for node {node.concepts}: {value_delta:.4f}")

            # Check convergence during expansion
            if value_delta < self.convergence_threshold:
                self.no_change_iterations += 1
                if self.no_change_iterations >= self.convergence_checks:
                    logger.info("Convergence achieved during expansion")
                    break
            else:
                self.no_change_iterations = 0

    def should_expand_node(self, node: ChallengeNode) -> bool:
        """
        Determines whether a node should be expanded based on its value and depth.

        Args:
            node (ChallengeNode): The node to check.

        Returns:
            bool: True if the node should be expanded, False otherwise.
        """
        return node.value >= self.performance_threshold and node.depth <= self.max_depth

    def expand_node(self, node: ChallengeNode) -> ChallengeNode:
        """
        Expands a node by creating a new child node.

        The expansion can be in two ways:
        - By combining the current node with another node to introduce new concepts.
        - By increasing the difficulty level of the current node.

        Args:
            node (ChallengeNode): The node to expand.

        Returns:
            ChallengeNode: The newly created child node.
        """
        if random.random() < self.exploration_probability:
            logger.info("Expanding node by adding new concepts")
            second_node = self.select_node()
            new_node = self.tree.add_node([node, second_node])
        else:
            logger.info("Expanding node by increasing difficulty")
            new_node = self.tree.add_node([node])
        return new_node

    def calculate_score(self, result: Dict, difficulty_level: str) -> float:
        """
        Calculates a normalized score for a challenge result.

        The score is influenced by the success of the challenge, the number of tests passed,
        penalties for failures, errors, attempts, and whether the problem was fixed by a fixer.

        Args:
            result (Dict): The results from the challenge simulation.
            difficulty_level (str): The difficulty level of the challenge.

        Returns:
            float: The normalized score between 0 and 1.
        """
        difficulty_weights = {
            "very easy": 1,
            "easy": 1.5,
            "medium": 2,
            "hard": 2.5,
            "very hard": 3,
        }

        # Phase 1 one-shot capability mapping (paper-aligned):
        # single attempt, no correction loop; reward depends on correctness + difficulty only.
        # R1(s) = b(s)*w(d) + p(s), with b(s) ∈ {0,1} and p(s) = -1 when failing.
        # We then normalize the raw reward to [0,1] for stable MCTS value updates.
        if PHASE_ONE_ONE_SHOT:
            diff_key = str(difficulty_level or "").strip().lower()
            weight = float(difficulty_weights.get(diff_key, 1))
            max_w = float(max(difficulty_weights.values()))
            raw = weight if result.get("success") else -1.0
            return max(0.0, min(1.0, (raw + 1.0) / (max_w + 1.0)))

        diff_key = str(difficulty_level or "").strip().lower()
        weight = float(difficulty_weights.get(diff_key, 1.0))
        max_w = float(max(difficulty_weights.values()))

        # Prism-style reward with efficiency penalties:
        # R1(s) = b(s) * w(d) + p
        # p = -(r_failed*P_failure + r_error*P_error + (n_attempts-1)*P_attempt + P_fixer*I_fixer)
        passed = int(result.get("cumulative_tests_passed", 0) or 0)
        failed = int(result.get("cumulative_tests_failed", 0) or 0)
        errored = int(result.get("cumulative_tests_errored", 0) or 0)
        total = passed + failed + errored

        if total > 0:
            r_failed = failed / total
            r_error = errored / total
        else:
            # If no tests were recorded, treat a failure as an error-dominated outcome.
            r_failed = 0.0
            r_error = 0.0 if result.get("success") else 1.0

        attempts = int(result.get("attempts_till_success") or PHASE_ONE_MAX_ATTEMPTS or 1)
        attempts = max(1, attempts)
        used_fixer = bool(result.get("used_problem_fixer") or result.get("fixed_by_problem_fixer"))
        i_fixer = 1.0 if used_fixer else 0.0

        penalty = (
            (float(r_failed) * float(PENALTY_PER_FAILURE))
            + (float(r_error) * float(PENALTY_PER_ERROR))
            + (max(0, attempts - 1) * float(PENALTY_PER_ATTEMPT))
            + (float(FIXED_BY_PROBLEM_FIXER_PENALTY) * i_fixer)
        )

        b = 1.0 if result.get("success") else 0.0
        raw = (b * weight) - penalty

        penalty_max = (
            float(PENALTY_PER_FAILURE)
            + float(PENALTY_PER_ERROR)
            + (max(0, int(PHASE_ONE_MAX_ATTEMPTS) - 1) * float(PENALTY_PER_ATTEMPT))
            + float(FIXED_BY_PROBLEM_FIXER_PENALTY)
        )
        denom = max_w + penalty_max
        if denom <= 0:
            return 0.0
        normalized = (raw + penalty_max) / denom
        return max(0.0, min(1.0, float(normalized)))


class ConceptMCTS(BaseMCTS):
    """
    Monte Carlo Tree Search implementation focusing on discovering challenging concept combinations.
    Inherits common functionality from BaseMCTS.
    """

    def __init__(
        self,
        environment: CodingChallengeEnvironment,
        tree: Tree,
        max_depth: int = 10,
        iterations: int = 100,
    ):
        super().__init__(environment, tree, max_depth, iterations)
        self.exploration_weight = EXPLORATION_WEIGHT
        self.challenge_threshold = CHALLENGE_THRESHOLD
        self.exploration_probability = PHASE_TWO_EXPLORATION_PROBABILITY
        self.value_delta_threshold = PHASE_TWO_VALUE_DELTA_THRESHOLD
        self.convergence_checks = PHASE_TWO_CONVERGENCE_CHECKS
        self.challenging_combinations = {}

    def run(self) -> Dict[tuple, Dict]:
        """
        Runs the ConceptMCTS algorithm to find challenging concept combinations.
        The algorithm iteratively selects nodes, simulates them, and backpropagates the results.
        It expands nodes focusing on challenging combinations and stops when convergence is achieved.

        Returns:
            Dict[tuple, Dict]: A dictionary of challenging concept combinations found.
        """
        logger.info("Starting Concept Challenge MCTS")
        path = self.experiment_path
        if not path:
            timestamp = datetime.now().strftime("%m%d_%H%M")
            experiment_name = f"{timestamp}_PHASE_TWO_{self.max_depth}"
            path = os.path.join(os.getcwd(), "experiments", experiment_name)
        os.makedirs(path, exist_ok=True)
        self.set_experiment_path(path)

        # Convergence parameters
        value_delta_threshold = self.value_delta_threshold
        convergence_checks = self.convergence_checks
        no_change_iterations = 0

        iteration = 0
        while True:
            iteration += 1
            try:
                node = self.select_node()

                if not node.run_results:
                    prev_value = node.value
                    score = self.simulate(node)
                    self.backpropagate(node, score)
                    node.phase = 2
                    self.tree.phase_markers[node] = 2
                    value_delta = abs(node.value - prev_value)
                    logger.debug(
                        f"Value delta for node {node.concepts}: {value_delta:.4f}"
                    )
                else:
                    prev_value = node.value
                    new_node = self.expand_node(node)
                    if new_node:
                        score = self.simulate(new_node)
                        self.backpropagate(new_node, score)
                        value_delta = abs(new_node.value - prev_value)
                        logger.debug(
                            f"Value delta for new node {new_node.concepts}: {value_delta:.4f}"
                        )
                    else:
                        value_delta = 0

                # Check convergence criterion
                if value_delta < value_delta_threshold:
                    no_change_iterations += 1
                    if no_change_iterations >= convergence_checks:
                        logger.info("Convergence achieved based on value changes")
                        break
                else:
                    no_change_iterations = 0

                if iteration % 10 == 0:
                    logger.info(
                        f"Iteration {iteration}: Found {len(self.challenging_combinations)} challenging combinations"
                    )
                    self.save_progress(path, iteration)
            except Exception as e:
                logger.exception(f"Error during iteration {iteration}: {e}")
                continue

        self.save_progress(path, "final")
        # Sort and return challenging combinations
        sorted_combinations = dict(
            sorted(
                self.challenging_combinations.items(),
                key=lambda x: (x[1]["score"], x[1]["count"]),
                reverse=True,
            )
        )

        logger.info("MCTS completed. Found challenging concept combinations:")
        for concepts, stats in sorted_combinations.items():
            logger.info(
                f"Concepts: {concepts}, Score: {stats['score']:.2f}, Count: {stats['count']}"
            )

        return sorted_combinations

    def select_node(self) -> ChallengeNode:
        """
        Select node based on UCB but favoring challenging combinations.
        """
        current = random.choice([n for n in self.tree.nodes if n.parents])

        while current.children:
            if random.random() < self.exploration_probability:
                current = random.choice(current.children)
            else:
                # Use UCB with challenge score
                current = max(
                    current.children,
                    key=lambda child: self.calculate_ucb(child),
                )

        return current

    def calculate_ucb(self, node: ChallengeNode) -> float:
        """
        Calculates the UCB value incorporating challenge metrics.
        Higher values are assigned to more challenging combinations.

        Args:
            node (ChallengeNode): The node for which to calculate the UCB value.

        Returns:
            float: The calculated UCB value.
        """
        if node.visits == 0:
            return float("inf")

        # Get average challenge score from node's run results
        challenge_scores = [
            self.calculate_challenge_score(result) for result in node.run_results
        ]
        avg_challenge = (
            sum(challenge_scores) / len(challenge_scores) if challenge_scores else 0
        )

        # UCB formula favoring challenging nodes
        exploitation = avg_challenge  # Higher challenge = higher exploitation
        total_visits = sum(parent.visits for parent in node.parents) or 1
        exploration = math.sqrt(math.log(total_visits) / node.visits)

        ucb_value = exploitation + self.exploration_weight * exploration
        return ucb_value

    def calculate_challenge_score(self, results: Dict) -> float:
        """
        Calculates how challenging a problem was based on:
        - Success rate
        - Number of attempts needed
        - Whether it needed fixes
        Higher score means more challenging.

        Args:
            results (Dict): The results from the challenge simulation.

        Returns:
            float: The challenge score.
        """
        total_tests = (
            int(results.get("cumulative_tests_passed", 0) or 0)
            + int(results.get("cumulative_tests_failed", 0) or 0)
            + int(results.get("cumulative_tests_errored", 0) or 0)
        )

        if total_tests > 0:
            r_success = float(results.get("cumulative_tests_passed", 0) or 0) / float(total_tests)
        else:
            r_success = 0.0

        attempts = int(results.get("attempts_till_success") or MAX_ATTEMPTS or 1)
        attempts = max(1, attempts)
        n_attempts_fix = max(0, attempts - 1)

        used_fixer = bool(results.get("used_problem_fixer") or results.get("fixed_by_problem_fixer"))
        i_fixer = 1.0 if used_fixer else 0.0

        raw = (
            (PHASE_TWO_LAMBDA * (1.0 - r_success))
            + (PHASE_TWO_GAMMA * float(n_attempts_fix))
            + (PHASE_TWO_BETA * i_fixer)
        )
        max_raw = (
            (PHASE_TWO_LAMBDA * 1.0)
            + (PHASE_TWO_GAMMA * float(max(0, int(MAX_ATTEMPTS) - 1)))
            + (PHASE_TWO_BETA * 1.0)
        )
        if max_raw <= 0:
            return 0.0
        return max(0.0, min(1.0, float(raw / max_raw)))

    def simulate(self, node: ChallengeNode) -> float:
        """
        Simulates the execution of a node by running a coding challenge and calculates the score.

        Args:
            node (ChallengeNode): The node to simulate.

        Returns:
            float: The normalized score obtained from the simulation.
        """
        logger.debug(
            f"Simulating node: Condition={node.condition_label or node.difficulty}, Concepts={node.concepts}"
        )
        challenge_results = self.environment.run_challenge(
            concept=node.concepts,
            difficulty_level=node.difficulty,
            max_attempts=MAX_ATTEMPTS,
        )
        self._save_run_artifacts(node, challenge_results, run_index=len(node.run_results) + 1)
        self.update_node_data(node, challenge_results)
        score = self.calculate_challenge_score(challenge_results)
        node.run_results.append(challenge_results)
        logger.debug(f"Simulation completed with score: {score:.2f}")
        return score

    def expand_node(self, node: ChallengeNode) -> Optional[ChallengeNode]:
        """
        Expands a node by creating a new child node focused on exploring challenging concept combinations.
        The expansion can be by increasing difficulty or adding new concepts.

        Args:
            node (ChallengeNode): The node to expand.

        Returns:
            Optional[ChallengeNode]: The newly created child node or None if expansion isn't possible.
        """
        if node.depth >= self.max_depth:
            return None

        # Determine if the combination is challenging
        challenge_score = self.calculate_challenge_score(node.run_results[-1])

        if challenge_score > self.challenge_threshold:
            # Record as a challenging combination
            concept_key = tuple(sorted(node.concepts))
            if concept_key not in self.challenging_combinations:
                self.challenging_combinations[concept_key] = {
                    "score": challenge_score,
                    "count": 1,
                }
            else:
                existing = self.challenging_combinations[concept_key]
                existing["score"] = (
                    existing["score"] * existing["count"] + challenge_score
                ) / (existing["count"] + 1)
                existing["count"] += 1

            # Increase difficulty
            next_difficulty_idx = min(
                self.tree.difficulties.index(node.difficulty) + 1,
                len(self.tree.difficulties) - 1,
            )
            new_difficulty = self.tree.difficulties[next_difficulty_idx]

            # Keep same concepts
            new_concepts = list(node.concepts)
        else:
            # Try adding a new concept or increasing difficulty
            if random.random() < 0.5:
                next_difficulty_idx = min(
                    self.tree.difficulties.index(node.difficulty) + 1,
                    len(self.tree.difficulties) - 1,
                )
            else:
                next_difficulty_idx = max(
                    self.tree.difficulties.index(node.difficulty), 0
                )
            new_difficulty = self.tree.difficulties[next_difficulty_idx]

            new_concepts = list(node.concepts)
            if len(new_concepts) < 4:
                available_concepts = set(self.tree.concepts) - set(new_concepts)
                if available_concepts:
                    new_concepts.append(random.choice(list(available_concepts)))

        return self.tree.add_node(
            parent_nodes=[node],
            concepts=new_concepts,
            difficulty=new_difficulty,
            phase=2,
        )


class CompMCTS(ConceptMCTS):
    """
    Monte Carlo Tree Search implementation focusing on generating comprehensive coding challenges. Phase 3.
    Inherits common functionality from ConceptMCTS.
    """

    def __init__(
        self,
        environment: EnhancedCodingChallengeEnvironment,
        tree: Tree,
        variations_per_concept: int = VARIAITONS_PER_CONCEPT,  # Generate multiple problems per concept combo
    ):
        super().__init__(environment, tree)
        self.challenging_nodes = []
        self.variations_per_concept = variations_per_concept
        self.node_selection_threshold = NODE_SELECTION_THRESHOLD

    def calculate_challenging_combinations(self) -> None:
        """
        Identifies challenging nodes from the tree based on a threshold.
        """
        phase2_nodes = [n for n in self.tree.nodes if n.phase == 2]
        self.challenging_nodes = [
            n for n in phase2_nodes if n.value >= self.node_selection_threshold
        ]

        if self.challenging_nodes:
            return

        # Fallback: if nothing meets the threshold, still run Phase 3 on the top-k
        # most challenging Phase 2 nodes (by value). This avoids a "no-op" Phase 3.
        if not phase2_nodes:
            logger.warning("Phase 3: no Phase 2 nodes found; nothing to evaluate.")
            return

        fallback_k = min(5, len(phase2_nodes))
        top_nodes = sorted(phase2_nodes, key=lambda n: n.value, reverse=True)[:fallback_k]
        self.challenging_nodes = top_nodes
        logger.warning(
            "Phase 3: no nodes met node_selection_threshold="
            f"{self.node_selection_threshold:.2f}; using top-{fallback_k} Phase 2 nodes instead "
            f"(max value={top_nodes[0].value:.3f})."
        )

    def run(self):
        """Run comprehensive benchmark suite"""
        logger.info("Starting Concept Challenge MCTS")
        path = self.experiment_path
        if not path:
            timestamp = datetime.now().strftime("%m%d_%H%M")
            experiment_name = f"{timestamp}_PHASE_THREE"
            path = os.path.join(os.getcwd(), "experiments", experiment_name)
        os.makedirs(path, exist_ok=True)
        self.set_experiment_path(path)

        self.calculate_challenging_combinations()
        logger.info(f"Found {len(self.challenging_nodes)} challenging nodes")
        for i, node in enumerate(self.challenging_nodes):
            try:
                run_results = self.environment.run_challenge(
                    concept=node.concepts,
                    difficulty_level=node.difficulty,
                    max_attempts=MAX_ATTEMPTS,
                    num_problems=self.variations_per_concept,
                )
                for attempt in run_results:
                    new_node = self.tree.add_node(
                        parent_nodes=[node],
                        concepts=node.concepts,
                        difficulty=node.difficulty,
                        phase=3,
                    )
                    new_node.challenge_description = attempt["problem_statement"]
                    for attempt_num, attempt_details in attempt["data_trail"].items():
                        node.problem_statement.setdefault(attempt_num, []).append(
                            attempt_details["problem_statement"]
                            if "problem_statement" in attempt_details
                            else []
                        )
                        node.solution_code.setdefault(attempt_num, []).append(
                            attempt_details["solution_code"]
                            if "solution_code" in attempt_details
                            else []
                        )
                        node.test_cases.setdefault(attempt_num, []).append(
                            attempt_details["test_cases"]
                            if "test_cases" in attempt_details
                            else []
                        )
                    new_node.run_results.append(attempt)
                    new_node.value = self.calculate_challenge_score(
                        new_node.run_results[-1]
                    )
                    self._save_run_artifacts(new_node, attempt, run_index=1)
            except Exception as e:
                logger.exception(f"Error during iteration {i}: {e}")
                pass

            self.tree.save_tree(file_name=path + f"/tree_{i}")
            self.tree.visualize_tree(file_name=path + f"/tree_{i}")

        self.tree.save_tree(file_name=path + "/tree_final")
        self.tree.visualize_tree(file_name=path + "/tree_final")
