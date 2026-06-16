import argparse
import hashlib
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv
from loguru import logger

from environment import CodingChallengeEnvironment, EnhancedCodingChallengeEnvironment
from mcts import CompMCTS, ConceptMCTS, MCTS
from attack_surface_conditions import (
    get_attack_surface_spec,
    ordered_attack_surfaces,
    seed_attack_surfaces,
)
from tree import Tree

load_dotenv()


def _project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def _ensure_cwd_project_root() -> str:
    root = _project_root()
    os.chdir(root)
    return root


def save_benchmark_params(
    mode: str,
    agent_config_path: str,
    *,
    stop_after_phase: int = 3,
    max_depth: Optional[int] = None,
    iterations: Optional[int] = None,
    cwe_db_path: Optional[str] = None,
    run_label: Optional[str] = None,
) -> Dict[str, Any]:
    timestamp = datetime.now().strftime("%m%d_%H%M")
    with open(os.path.join(os.getcwd(), "configs.yml"), "r", encoding="utf-8") as f:
        benchmark_configs = yaml.safe_load(f) or {}
    models = _extract_llm_model_metadata(agent_config_path)
    primary_model = _primary_model_name(models)
    model_slug = _slugify(run_label or primary_model or "unknown-model")

    with open(f"{timestamp}_params", "w", encoding="utf-8") as f:
        yaml.dump(
            {
                "run": {
                    "mode": mode,
                    "agent_config": agent_config_path,
                    "timestamp": timestamp,
                    "stop_after_phase": int(stop_after_phase),
                    "max_depth": max_depth,
                    "iterations": iterations,
                    "cwe_db": cwe_db_path,
                    "run_label": run_label,
                    "primary_model": primary_model,
                    "model_slug": model_slug,
                },
                "models": models,
                "environment": {
                    "phase 1 performance threshold": benchmark_configs.get("phase1", {}).get(
                        "performance_threshold"
                    ),
                    "phase 1 value threshold": benchmark_configs.get("phase1", {}).get(
                        "value_delta_threshold"
                    ),
                    "phase 1 exploration probability": benchmark_configs.get("phase1", {}).get(
                        "exploration_probability"
                    ),
                    "phase 2 value threshold": benchmark_configs.get("phase2", {}).get(
                        "value_delta_threshold"
                    ),
                    "phase 3 value threshold": benchmark_configs.get("phase3", {}).get(
                        "node_selection_threshold"
                    ),
                },
            },
            f,
            default_flow_style=False,
        )
    return {
        "timestamp": timestamp,
        "models": models,
        "primary_model": primary_model,
        "model_slug": model_slug,
    }


def _should_continue_after_phase(completed_phase: int, stop_after_phase: int) -> bool:
    return int(completed_phase) < int(stop_after_phase)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PrismBench / PrismVul runner")
    parser.add_argument(
        "--mode",
        choices=["bench", "vuln"],
        default="bench",
        help="Run PrismBench (bench) or the SAST-based vulnerability benchmark (vuln).",
    )
    parser.add_argument(
        "--agent-config",
        default=None,
        help="Agent config YAML path (defaults depend on mode).",
    )
    parser.add_argument(
        "--cwe-db",
        default=os.path.join(os.getcwd(), "data", "cwe_database.yml"),
        help="CWE database YAML path (vuln mode only).",
    )
    parser.add_argument("--max-depth", type=int, default=5)
    parser.add_argument("--iterations", type=int, default=70)
    parser.add_argument(
        "--run-label",
        default=None,
        help=(
            "Optional label included in the experiment directory. "
            "Defaults to the primary solver model name."
        ),
    )
    parser.add_argument(
        "--stop-after-phase",
        type=int,
        choices=[1, 2, 3],
        default=3,
        help="Stop the pipeline after the selected phase (default: 3 = full pipeline).",
    )
    return parser


def _unique_dir(parent: str, name: str) -> str:
    """
    Create a unique directory name under `parent` by appending a counter if needed.
    Returns the selected path (does not create it).
    """
    base = os.path.join(parent, name)
    if not os.path.exists(base):
        return base
    for i in range(2, 10_000):
        candidate = os.path.join(parent, f"{name}_{i}")
        if not os.path.exists(candidate):
            return candidate
    raise RuntimeError(f"Could not find a unique directory name for: {base}")


def _load_yaml_dict(path: Optional[str]) -> Dict[str, Any]:
    if not path:
        return {}
    try:
        with open(os.path.abspath(path), "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    return data if isinstance(data, dict) else {}


def _extract_llm_model_metadata(agent_config_path: str) -> Dict[str, Dict[str, Any]]:
    cfg = _load_yaml_dict(agent_config_path)
    llms = cfg.get("llms") if isinstance(cfg, dict) else {}
    if not isinstance(llms, dict):
        return {}

    models: Dict[str, Dict[str, Any]] = {}
    for role, role_cfg in sorted(llms.items()):
        if not isinstance(role_cfg, dict):
            continue
        entry: Dict[str, Any] = {}
        for key in ("model_name", "provider", "local", "params"):
            if key in role_cfg:
                entry[key] = role_cfg.get(key)
        if entry:
            models[str(role)] = entry
    return models


def _primary_model_name(models: Dict[str, Dict[str, Any]]) -> Optional[str]:
    preferred_roles = (
        "problem_solver",
        "security_fixer",
        "problem_fixer",
        "challenge_designer",
    )
    for role in preferred_roles:
        model_name = (models.get(role) or {}).get("model_name")
        if model_name:
            return str(model_name)
    for role_cfg in models.values():
        model_name = role_cfg.get("model_name")
        if model_name:
            return str(model_name)
    return None


def _slugify(value: Optional[str], *, max_len: int = 72) -> str:
    raw = str(value or "").strip().lower()
    raw = raw.replace("/", "-").replace(":", "-")
    slug = re.sub(r"[^a-z0-9._-]+", "-", raw).strip("-._")
    slug = re.sub(r"-{2,}", "-", slug)
    return (slug[:max_len].strip("-._") or "unknown")


def _capture_command(args: List[str]) -> str:
    return " ".join(shlex.quote(str(a)) for a in args)


def _run_git(root: str, args: List[str]) -> Optional[str]:
    try:
        proc = subprocess.run(
            ["git", "-C", root, *args],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _git_trace(root: str) -> Dict[str, Any]:
    git_root = _run_git(root, ["rev-parse", "--show-toplevel"])
    commit = _run_git(root, ["rev-parse", "HEAD"])
    branch = _run_git(root, ["branch", "--show-current"])
    if not git_root or not commit:
        return {"available": False}

    project_rel = os.path.relpath(root, git_root)
    status = _run_git(root, ["status", "--short", "--", project_rel]) or ""
    diff_stat = _run_git(root, ["diff", "--stat", "--", project_rel]) or ""
    return {
        "available": True,
        "git_root": git_root,
        "commit": commit,
        "branch": branch,
        "project_path": project_rel,
        "dirty": bool(status.strip()),
        "status_short": status,
        "diff_stat": diff_stat,
    }


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iter_trace_source_files(root: str) -> List[str]:
    files: List[str] = []
    source_dirs = ("src", "tests", "scripts")
    source_exts = (".py", ".yml", ".yaml", ".toml", ".md", ".txt")
    skip_dirs = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}

    for rel_dir in source_dirs:
        base = os.path.join(root, rel_dir)
        if not os.path.isdir(base):
            continue
        for current, dirs, names in os.walk(base):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for name in names:
                if name.endswith(source_exts):
                    files.append(os.path.join(current, name))

    top_level_files = (
        "configs.yml",
        "agent_config_vul.yml",
        "agent_config_v7.yml",
        "semgrep_rules.yml",
        "README.md",
        "requirements.txt",
        "pyproject.toml",
    )
    for rel in top_level_files:
        path = os.path.join(root, rel)
        if os.path.isfile(path):
            files.append(path)

    cwe_db = os.path.join(root, "data", "cwe_database.yml")
    if os.path.isfile(cwe_db):
        files.append(cwe_db)

    return sorted(set(files), key=lambda p: os.path.relpath(p, root))


def _build_source_manifest(root: str, source_files: Optional[List[str]] = None) -> Dict[str, Any]:
    entries: Dict[str, Dict[str, Any]] = {}
    overall = hashlib.sha256()
    for path in source_files or _iter_trace_source_files(root):
        rel = os.path.relpath(path, root)
        file_hash = _sha256_file(path)
        size = os.path.getsize(path)
        entries[rel] = {"sha256": file_hash, "bytes": size}
        overall.update(rel.encode("utf-8"))
        overall.update(b"\0")
        overall.update(file_hash.encode("ascii"))
        overall.update(b"\n")
    return {
        "source_digest": overall.hexdigest(),
        "file_count": len(entries),
        "files": entries,
    }


def _copy_source_snapshot(root: str, trace_dir: str, source_files: List[str]) -> str:
    snapshot_dir = os.path.join(trace_dir, "source_snapshot")
    os.makedirs(snapshot_dir, exist_ok=True)
    for path in source_files:
        rel = os.path.relpath(path, root)
        dest = os.path.join(snapshot_dir, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(path, dest)
    return snapshot_dir


def write_run_traceability(
    run_root: str,
    *,
    mode: str,
    timestamp: str,
    agent_config: str,
    cwe_db_path: Optional[str],
    max_depth: int,
    iterations: int,
    stop_after_phase: int,
    run_label: Optional[str],
    models: Dict[str, Dict[str, Any]],
    primary_model: Optional[str],
    model_slug: str,
) -> None:
    root = _project_root()
    trace_dir = os.path.join(run_root, "_trace")
    os.makedirs(trace_dir, exist_ok=True)

    snapshots: Dict[str, str] = {}
    for label, src in {
        "agent_config": agent_config,
        "benchmark_config": os.path.join(root, "configs.yml"),
        "cwe_database": cwe_db_path,
    }.items():
        if not src or not os.path.isfile(os.path.abspath(src)):
            continue
        dest = os.path.join(trace_dir, f"{label}{os.path.splitext(src)[1] or '.yml'}")
        shutil.copy2(os.path.abspath(src), dest)
        snapshots[label] = os.path.relpath(dest, run_root)

    source_files = _iter_trace_source_files(root)
    source_manifest = _build_source_manifest(root, source_files)
    source_snapshot_dir = _copy_source_snapshot(root, trace_dir, source_files)
    manifest_path = os.path.join(trace_dir, "source_manifest.yml")
    with open(manifest_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(source_manifest, f, sort_keys=True)

    metadata = {
        "run": {
            "mode": mode,
            "timestamp": timestamp,
            "run_root": os.path.abspath(run_root),
            "run_label": run_label,
            "primary_model": primary_model,
            "model_slug": model_slug,
            "max_depth": int(max_depth),
            "iterations": int(iterations),
            "stop_after_phase": int(stop_after_phase),
            "command": _capture_command(sys.argv),
            "cwd": os.getcwd(),
            "python": sys.version,
            "platform": platform.platform(),
        },
        "models": models,
        "inputs": {
            "agent_config": os.path.abspath(agent_config),
            "cwe_db": os.path.abspath(cwe_db_path) if cwe_db_path else None,
            "snapshots": snapshots,
        },
        "code": {
            "git": _git_trace(root),
            "source_digest": source_manifest.get("source_digest"),
            "source_manifest": os.path.relpath(manifest_path, run_root),
            "source_snapshot": os.path.relpath(source_snapshot_dir, run_root),
        },
    }
    with open(os.path.join(run_root, "run_metadata.yml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(metadata, f, sort_keys=False)


def _run_bench(
    agent_config: str,
    max_depth: int,
    iterations: int,
    *,
    run_root: Optional[str],
    stop_after_phase: int = 3,
) -> None:
    environment = CodingChallengeEnvironment(config_path=agent_config)
    tree = Tree(
        concepts=[
            "loops",
            "conditionals",
            "functions",
            "data_structures",
            "algorithms",
            "error_handling",
            "recursion",
            "sorting",
            "searching",
            "dynamic_programming",
        ],
        difficulties=["very easy", "easy", "medium", "hard", "very hard"],
    )
    tree.initialize_tree()

    phase_one_agent = MCTS(environment, tree, max_depth=max_depth, iterations=iterations)
    if run_root:
        phase_one_agent.set_experiment_path(os.path.join(run_root, f"PHASE_ONE_{max_depth}"))
    phase_one_agent.run()
    logger.info("MCTS Phase 1 completed")
    if not _should_continue_after_phase(1, stop_after_phase):
        logger.info("Stopping after Phase 1 as requested")
        return

    phase_two_agent = ConceptMCTS(
        environment, phase_one_agent.tree, max_depth=max_depth + 5, iterations=iterations
    )
    if run_root:
        phase_two_agent.set_experiment_path(os.path.join(run_root, f"PHASE_TWO_{max_depth + 5}"))
    for node in phase_two_agent.tree.nodes:
        if node.run_results:
            node.score = phase_two_agent.calculate_challenge_score(node.run_results[-1])
            phase_two_agent.backpropagate(node, node.score)

    phase_two_agent.run()
    logger.info("MCTS Phase 2 completed")
    if not _should_continue_after_phase(2, stop_after_phase):
        logger.info("Stopping after Phase 2 as requested")
        return

    phase_three_environment = EnhancedCodingChallengeEnvironment(config_path=agent_config)
    phase_three_agent = CompMCTS(phase_three_environment, phase_two_agent.tree)
    if run_root:
        phase_three_agent.set_experiment_path(os.path.join(run_root, "PHASE_THREE"))
    phase_three_agent.run()
    logger.info("MCTS Phase 3 completed")


def _run_vuln(
    agent_config: str,
    cwe_db_path: str,
    max_depth: int,
    iterations: int,
    *,
    run_root: Optional[str],
    stop_after_phase: int = 3,
) -> None:
    from vulnerability_environment import (
        EnhancedVulnerabilityChallengeEnvironment,
        VulnerabilityChallengeEnvironment,
    )
    from vulnerability_mcts import (
        VulnerabilityCompMCTS,
        VulnerabilityConceptMCTS,
        VulnerabilityMapElitesPhaseOne,
        VulnerabilityMCTS,
    )

    with open(cwe_db_path, "r", encoding="utf-8") as f:
        cwe_db = yaml.safe_load(f) or {}
    with open(os.path.join(os.getcwd(), "configs.yml"), "r", encoding="utf-8") as f:
        benchmark_cfg = yaml.safe_load(f) or {}

    cwes = cwe_db.get("cwes") or []
    attack_surfaces = cwe_db.get("attack_surfaces") or ordered_attack_surfaces()
    if not cwes:
        raise RuntimeError(f"No CWEs found in {cwe_db_path}")
    if not attack_surfaces:
        raise RuntimeError(f"No attack surfaces found in {cwe_db_path}")

    normalized_surfaces = [str(surface) for surface in attack_surfaces]

    def _surface_node_kwargs(value: str) -> dict[str, object]:
        spec = get_attack_surface_spec(value)
        if not spec:
            return {}
        label = str(spec["label"])
        try:
            rank = normalized_surfaces.index(label) + 1
        except ValueError:
            rank = int(spec["rank"])
        return {
            "condition_axis": label,
            "condition_label": label,
            "condition_rank": rank,
        }

    environment = VulnerabilityChallengeEnvironment(config_path=agent_config)
    tree = Tree(
        concepts=cwes,
        difficulties=attack_surfaces,
        condition_meta_resolver=_surface_node_kwargs,
    )
    phase1_cfg = benchmark_cfg.get("phase1", {}) if isinstance(benchmark_cfg, dict) else {}
    phase1_algorithm = str(phase1_cfg.get("algorithm", "mcts")).strip().lower()
    phase1_init_cfg = (
        phase1_cfg.get("initialization", {}) if isinstance(phase1_cfg, dict) else {}
    )
    seed_all_attack_surfaces = bool(phase1_init_cfg.get("seed_all_attack_surfaces", True))
    initial_pair_seeds_per_surface = int(
        phase1_init_cfg.get("initial_pair_seeds_per_surface", 2)
    )
    seed_surfaces = attack_surfaces if seed_all_attack_surfaces else seed_attack_surfaces(attack_surfaces)
    tree.initialize_tree(
        seed_difficulties=seed_surfaces,
        create_initial_combinations=False,
    )
    tree.add_initial_pair_seeds(
        per_difficulty=initial_pair_seeds_per_surface,
        same_difficulty_only=True,
        log_creation=False,
    )
    phase1_cls = (
        VulnerabilityMapElitesPhaseOne if phase1_algorithm == "map_elites" else VulnerabilityMCTS
    )
    phase_one_agent = phase1_cls(environment, tree, max_depth=max_depth, iterations=iterations)
    if run_root:
        phase_one_agent.set_experiment_path(os.path.join(run_root, f"PHASE_ONE_{max_depth}"))
    phase_one_agent.run()
    logger.info("Vulnerability Phase 1 completed")
    if not _should_continue_after_phase(1, stop_after_phase):
        logger.info("Stopping after Vulnerability Phase 1 as requested")
        return

    phase_two_agent = VulnerabilityConceptMCTS(
        environment, phase_one_agent.tree, max_depth=max_depth + 5, iterations=iterations
    )
    if run_root:
        phase_two_agent.set_experiment_path(os.path.join(run_root, f"PHASE_TWO_{max_depth + 5}"))
    for node in phase_two_agent.tree.nodes:
        if node.run_results:
            node.score = phase_two_agent.calculate_challenge_score(node.run_results[-1])
            phase_two_agent.backpropagate(node, node.score)

    phase_two_agent.run()
    logger.info("Vulnerability MCTS Phase 2 completed")
    if not _should_continue_after_phase(2, stop_after_phase):
        logger.info("Stopping after Vulnerability Phase 2 as requested")
        return

    phase_three_environment = EnhancedVulnerabilityChallengeEnvironment(config_path=agent_config)
    phase_three_agent = VulnerabilityCompMCTS(phase_three_environment, phase_two_agent.tree)
    if run_root:
        phase_three_agent.set_experiment_path(os.path.join(run_root, "PHASE_THREE"))
    phase_three_agent.run()
    logger.info("Vulnerability MCTS Phase 3 completed")

    # Prism-style Phase 3 aggregation: write pattern_summary.json + detailed_report.json
    # to the PHASE_THREE directory for easy triage and study.
    if run_root:
        try:
            from phase3_patterns import write_phase3_reports

            write_phase3_reports(os.path.join(run_root, "PHASE_THREE"))
            logger.info("Phase 3 pattern reports written")
        except Exception:
            logger.opt(exception=True).warning("Failed to write Phase 3 pattern reports")


if __name__ == "__main__":
    _ensure_cwd_project_root()

    parser = build_arg_parser()
    args = parser.parse_args()

    default_agent_config = os.path.join(
        os.getcwd(),
        "agent_config_v7.yml" if args.mode == "bench" else "agent_config_vul.yml",
    )
    agent_config = args.agent_config or default_agent_config

    run_trace = save_benchmark_params(
        mode=args.mode,
        agent_config_path=agent_config,
        stop_after_phase=args.stop_after_phase,
        max_depth=args.max_depth,
        iterations=args.iterations,
        cwe_db_path=args.cwe_db if args.mode == "vuln" else None,
        run_label=args.run_label,
    )
    timestamp = str(run_trace["timestamp"])
    model_slug = str(run_trace.get("model_slug") or "unknown-model")
    experiments_dir = os.path.join(os.getcwd(), "experiments")
    os.makedirs(experiments_dir, exist_ok=True)
    run_root = _unique_dir(experiments_dir, f"exp_{timestamp}_{args.mode}_{model_slug}")
    os.makedirs(run_root, exist_ok=True)
    write_run_traceability(
        run_root,
        mode=args.mode,
        timestamp=timestamp,
        agent_config=agent_config,
        cwe_db_path=args.cwe_db if args.mode == "vuln" else None,
        max_depth=args.max_depth,
        iterations=args.iterations,
        stop_after_phase=args.stop_after_phase,
        run_label=args.run_label,
        models=run_trace.get("models") or {},
        primary_model=run_trace.get("primary_model"),
        model_slug=model_slug,
    )

    if args.mode == "bench":
        _run_bench(
            agent_config=agent_config,
            max_depth=args.max_depth,
            iterations=args.iterations,
            run_root=run_root,
            stop_after_phase=args.stop_after_phase,
        )
    else:
        _run_vuln(
            agent_config=agent_config,
            cwe_db_path=args.cwe_db,
            max_depth=args.max_depth,
            iterations=args.iterations,
            run_root=run_root,
            stop_after_phase=args.stop_after_phase,
        )
