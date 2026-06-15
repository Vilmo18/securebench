import pickle
import os
from itertools import combinations
from typing import Callable, Union, Dict, Any
from datetime import datetime
from graphviz import Digraph

from node import ChallengeNode
import html
from loguru import logger
from scenario_conditions import get_condition_spec, normalize_condition
from attack_surface_conditions import normalize_attack_surface


def _default_condition_node_kwargs(value: str) -> Dict[str, Any]:
    spec = get_condition_spec(value)
    if not spec:
        return {}
    normalized = normalize_condition(value)
    return {
        "condition_axis": str(spec["axis_label"]),
        "condition_label": normalized,
        "condition_rank": int(spec["rank"]),
    }


class Tree:
    def __init__(
        self,
        concepts: list,
        difficulties: list,
        condition_meta_resolver: Callable[[str], Dict[str, Any]] | None = None,
    ) -> None:
        self.concepts = concepts
        self.difficulties = difficulties
        self.condition_meta_resolver = condition_meta_resolver or _default_condition_node_kwargs

        self.nodes = []
        self._initialize_phase_markers()

    def _initialize_phase_markers(self):
        """Initialize phase_markers dictionary and mark existing nodes as phase 1"""
        if not hasattr(self, "phase_markers"):
            self.phase_markers = {}
            # Mark any existing nodes as phase 1
            for node in self.nodes:
                self.phase_markers[node] = 1

    def initialize_tree(
        self,
        *,
        seed_difficulties: list[str] | None = None,
        combine_same_difficulty_only: bool = False,
        create_initial_combinations: bool = True,
    ) -> None:
        """
        Initializes the tree with the given concepts.

        Args:
            concepts (list): list of concepts to initialize the tree with.
        """
        root_difficulties = list(seed_difficulties or [])
        if not root_difficulties:
            root_difficulties = [self.difficulties[0] if self.difficulties else "very easy"]

        root_nodes = []
        for root_difficulty in root_difficulties:
            for concept in self.concepts:
                root_nodes.append(
                    ChallengeNode(
                        difficulty=root_difficulty,
                        concepts=concept,
                        challenge_description="",
                        log_creation=False,
                        **self.condition_meta_resolver(root_difficulty),
                    )
                )
        self.nodes = root_nodes

        if not create_initial_combinations:
            logger.debug(
                f"Initialized tree with {len(root_nodes)} root nodes and no initial pair nodes"
            )
            self._initialize_phase_markers()
            return

        initial_pair_count = 0
        if combine_same_difficulty_only:
            roots_by_difficulty = {}
            for node in root_nodes:
                key = node.difficulty
                roots_by_difficulty.setdefault(key, []).append(node)
            for nodes in roots_by_difficulty.values():
                for pair in list(combinations(nodes, 2)):
                    self.add_node(
                        pair,
                        difficulty=pair[0].difficulty,
                        concepts=set(pair[0].concepts + pair[1].concepts),
                        log_creation=False,
                    )
                    initial_pair_count += 1
        else:
            for node in list(combinations(self.nodes, 2)):
                self.add_node(node, log_creation=False)
                initial_pair_count += 1
        logger.debug(
            f"Initialized tree with {len(root_nodes)} root nodes and {initial_pair_count} initial pair nodes"
        )
        self._initialize_phase_markers()

    def add_initial_pair_seeds(
        self,
        *,
        per_difficulty: int = 0,
        same_difficulty_only: bool = True,
        log_creation: bool = False,
    ) -> int:
        """
        Add a small number of initial pair nodes after root-node initialization.

        This is useful when we want:
        - all root nodes to exist from the start
        - a few seeded 2-concept combinations
        - without creating the full O(n^2) initial pair explosion
        """
        if per_difficulty <= 0:
            return 0

        root_nodes = [node for node in self.nodes if node.depth == 0]
        if not root_nodes:
            return 0

        seeded_pairs = 0

        if same_difficulty_only:
            roots_by_difficulty = {}
            for node in root_nodes:
                roots_by_difficulty.setdefault(node.difficulty, []).append(node)

            for difficulty_nodes in roots_by_difficulty.values():
                local_count = 0
                for pair in combinations(difficulty_nodes, 2):
                    self.add_node(
                        list(pair),
                        difficulty=pair[0].difficulty,
                        concepts=set(pair[0].concepts + pair[1].concepts),
                        log_creation=log_creation,
                    )
                    seeded_pairs += 1
                    local_count += 1
                    if local_count >= per_difficulty:
                        break
        else:
            for pair in combinations(root_nodes, 2):
                self.add_node(
                    list(pair),
                    concepts=set(pair[0].concepts + pair[1].concepts),
                    log_creation=log_creation,
                )
                seeded_pairs += 1
                if seeded_pairs >= per_difficulty:
                    break

        logger.debug(
            f"Added {seeded_pairs} limited initial pair seeds "
            f"(per_difficulty={per_difficulty}, same_difficulty_only={same_difficulty_only})"
        )
        return seeded_pairs

    def add_root_nodes(
        self,
        root_difficulty: str,
        *,
        concepts: list[str] | None = None,
        log_creation: bool = False,
    ) -> list[ChallengeNode]:
        root_nodes: list[ChallengeNode] = []
        for concept in concepts or self.concepts:
            node = ChallengeNode(
                difficulty=root_difficulty,
                concepts=concept,
                challenge_description="",
                log_creation=log_creation,
                **self.condition_meta_resolver(root_difficulty),
            )
            self.nodes.append(node)
            self.phase_markers[node] = 1
            root_nodes.append(node)
        logger.debug(
            f"Opened condition `{root_difficulty}` with {len(root_nodes)} new root nodes"
        )
        return root_nodes

    def add_node(
        self,
        parent_nodes: Union[ChallengeNode, list[ChallengeNode]],
        **kwargs,
    ) -> None:
        """
        Adds a new node to the tree based on the given parent nodes.

        Args:
            - parent_nodes (Union[ChallengeNode, list[ChallengeNode]]): The parent nodes to add the new node to.
            - kwargs: Additional keyword arguments to pass to the new node.
                - concepts (list): The concepts of the new node.
                - difficulty (str): The difficulty of the new node.
                - phase (int): The phase of the new node. Only used for Phases 2 and 3.
        """

        if "concepts" in kwargs:
            new_node_concepts = kwargs["concepts"]
            new_node_difficulty = kwargs["difficulty"]
        else:
            # calculate the concepts of the new node
            if isinstance(parent_nodes, ChallengeNode):
                new_node_concepts = parent_nodes.concepts
            else:
                new_node_concepts = set(
                    [
                        concept
                        for parent_node in parent_nodes
                        for concept in parent_node.concepts
                    ]
                )

            # calculate the difficulty of the new node
            new_node_difficulty = self.assign_difficulty(parent_nodes)

        condition_meta = self.condition_meta_resolver(new_node_difficulty)
        max_concepts = max(1, int(kwargs.get("max_concepts", 4) or 4))
        new_node = ChallengeNode(
            difficulty=new_node_difficulty,
            concepts=list(new_node_concepts)[:max_concepts],
            challenge_description="",
            parents=parent_nodes,
            depth=parent_nodes[0].depth + 1,
            phase=kwargs["phase"] if "phase" in kwargs else 1,
            condition_axis=kwargs.get("condition_axis")
            or condition_meta.get("condition_axis"),
            condition_label=kwargs.get("condition_label")
            or condition_meta.get("condition_label"),
            condition_rank=kwargs.get("condition_rank")
            or condition_meta.get("condition_rank"),
            log_creation=kwargs.get("log_creation", True),
        )

        for parent_node in parent_nodes:
            parent_node.children.append(new_node)

        self.nodes.append(new_node)

        self.phase_markers[new_node] = kwargs["phase"] if "phase" in kwargs else 1

        return new_node

    def assign_difficulty(self, parent_nodes: list[ChallengeNode]) -> str:
        """
        Assigns the difficulty of the new node based on the parent nodes.

        Args:
            parent_nodes (list[ChallengeNode]): list of parent nodes to assign the difficulty from.

        Returns:
            str: the difficulty of the new node.
        """
        parents_max_difficulty = max(
            [self.difficulties.index(parent.difficulty) for parent in parent_nodes]
        )
        parents_min_score = min([parent.value for parent in parent_nodes])

        if parents_min_score > 0.3:
            try:
                new_node_difficulty = self.difficulties[parents_max_difficulty + 1]
            except IndexError:
                new_node_difficulty = self.difficulties[parents_max_difficulty]
        else:
            new_node_difficulty = (
                self.difficulties[parents_max_difficulty - 1]
                if parents_max_difficulty > 0
                else (self.difficulties[0] if self.difficulties else "very easy")
            )

        return new_node_difficulty

    def calculate_performance_score(self, results: Dict) -> float:
        """
        Calculate performance score for a node's results

        Args:
            results (Dict): The results of the node's run.
        returns:
            float: The performance score for the node.
        """
        if not isinstance(results, dict):
            return 0.0

        # Original PrismBench (unit-test based) schema
        # Use `.get` so this never raises KeyError for vuln-mode results.
        passed = results.get("cumulative_tests_passed")
        failed = results.get("cumulative_tests_failed")
        errored = results.get("cumulative_tests_errored")

        if passed is not None and failed is not None and errored is not None:
            try:
                passed_i = int(passed)
                failed_i = int(failed)
                errored_i = int(errored)
            except Exception:
                passed_i, failed_i, errored_i = 0, 0, 0

            total_tests = passed_i + failed_i + errored_i
            success_rate = passed_i / total_tests if total_tests > 0 else 0
            attempt_penalty = (
                0.2 * (results.get("attempts_till_success", 1) - 1)
                if results.get("attempts_till_success")
                else 0.6
            )
            fixer_penalty = 0.3 if results.get("fixed_by_problem_fixer") else 0

            return (
                success_rate * 0.6
                + (1 - attempt_penalty) * 0.25
                + (1 - fixer_penalty) * 0.15
            )

        # Vulnerability / SAST schema
        total_issues = results.get("total_issues")
        if total_issues is None:
            sast = results.get("sast")
            if isinstance(sast, dict):
                total_issues = sast.get("total_issues")
        if total_issues is None:
            total_issues = 0

        # Convert issues -> "security success rate" in [0,1]
        if results.get("success") and int(total_issues) == 0:
            security_rate = 1.0
        else:
            security_rate = 1.0 / (1.0 + max(int(total_issues), 0))

        attempt_penalty = (
            0.2 * (results.get("attempts_till_success", 1) - 1)
            if results.get("attempts_till_success")
            else 0.6
        )
        fixer_penalty = 0.3 if results.get("fixed_by_security_fixer") else 0

        return (
            security_rate * 0.6
            + (1 - attempt_penalty) * 0.25
            + (1 - fixer_penalty) * 0.15
        )

    def visualize_tree(self, file_name: str = "tree") -> None:
        """
        Visualizes the tree using Graphviz with color coding for different phases.

        Args:
            file_name (str): The name of the file to save the tree visualization to. Defaults to "tree".
        """
        dot = Digraph(comment="MCTS Tree")
        dot.attr(rankdir="TB")
        dot.attr(
            "node",
            shape="box",
            style="rounded, filled",
            fontname="Helvetica",
            fontsize="12",
            penwidth="2",
        )
        # Define color schemes for different phases
        phase_colors = {
            1: {
                "fillcolor": "lightyellow",
                "color": "darkblue",
                "label_prefix": "Phase 1",
            },
            2: {
                "fillcolor": "lightgreen",
                "color": "darkgreen",
                "label_prefix": "Phase 2",
            },
            3: {
                "fillcolor": "lightblue",
                "color": "darkblue",
                "label_prefix": "Phase 3",
            },
        }

        # Add legend
        with dot.subgraph(name="cluster_legend") as legend:
            legend.attr(label="Legend")
            for phase, style in phase_colors.items():
                legend_node_name = f"legend_phase_{phase}"
                legend.node(
                    legend_node_name,
                    f"Phase {phase} Node",
                    style="filled",
                    fillcolor=style["fillcolor"],
                    color=style["color"],
                )

        # Add nodes with phase-specific styling
        nodes_by_depth = {}
        for node in self.nodes:
            phase = int(node.phase)  # Default to phase 1 if not marked
            style = phase_colors[phase]
            nodes_by_depth.setdefault(int(node.depth), []).append(node)

            # Format concepts deterministically for stable graph labels.
            sorted_concepts = sorted(html.escape(str(c)) for c in node.concepts)
            formatted_concepts = "\\l    ".join(sorted_concepts)

            condition_value = str(node.condition_label or node.difficulty)
            condition_label_name = (
                "SURFACE" if normalize_attack_surface(condition_value) != "unknown" else "CONDITION"
            )

            label = (
                f"{style['label_prefix']}\\n"
                f"\\nCONCEPTS:\\l    {formatted_concepts}\\l\\n"
                f"{condition_label_name}:\\l    {html.escape(condition_value)}\\l\\n"
                f"SCORE:\\l    {html.escape(str(f'{node.value:.2f}'))}\\l\\n"
                f"VISITS:\\l    {html.escape(str(node.visits))}\\l\\n"
            )

            dot.node(
                str(id(node)),
                label,
                style="filled",
                fillcolor=style["fillcolor"],
                color=style["color"],
            )

        for depth, depth_nodes in sorted(nodes_by_depth.items()):
            with dot.subgraph(name=f"depth_rank_{depth}") as depth_graph:
                depth_graph.attr(rank="same")
                for node in depth_nodes:
                    depth_graph.node(str(id(node)))

        for node in self.nodes:
            # Add edges to children
            for child in node.children:
                # Color edges based on performance improvement
                edge_color = "green"
                if node.value and child.value:
                    if child.value < node.value:
                        edge_color = "red"
                    elif child.value == node.value:
                        edge_color = "gray"

                dot.edge(
                    str(id(node)), str(id(child)), color=edge_color, penwidth="2.0"
                )

        # Add graph title with timestamp
        experiment_label = os.path.basename(os.path.dirname(file_name)) or os.path.basename(
            file_name
        )
        dot.attr(label=f"MCTS Tree Visualization-----{experiment_label}")

        # Save in multiple formats
        for fmt in ["svg", "pdf", "png"]:
            dot.render(f"{file_name}", format=fmt, cleanup=True)

    def save_tree(self, file_name: str = "tree") -> None:
        """
        Saves the current tree structure to a file in pickle format.

        Args:
            file_name (str): The name of the file to save the tree to. Defaults to "tree".

        Returns:
            None
        """
        with open(f"{file_name}.pkl", "wb") as f:
            pickle.dump(self.nodes, f)
        with open(f"{file_name}_phases.pkl", "wb") as f:
            pickle.dump(self.phase_markers, f)

    def load_tree(self, file_name: str = "tree") -> None:
        """
        Load the tree structure from a pickle file.

        Args:
            file_name (str): The base name of the file to load the tree from.
                             Defaults to "tree".

        Returns:
            None
        """
        with open(f"{file_name}.pkl", "rb") as f:
            self.nodes = pickle.load(f)
        # with open(f"{file_name}_phases.pkl", "rb") as f:
        #     self.phase_markers = pickle.load(f)
        # self._initialize_phase_markers()


if __name__ == "__main__":
    tree = Tree(
        concepts=["concept1", "concept2", "concept3", "concept4"],
        difficulties=["very easy", "easy", "medium", "hard", "very hard"],
    )
    tree.initialize_tree()
    tree.save_tree(file_name="initial_tree_2")
    tree.visualize_tree(file_name="initial_tree_2")
