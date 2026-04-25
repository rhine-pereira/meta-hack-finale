"""
Repo organizer / cleanup utility.

Goals:
- Reduce clutter in the repository root (move one-off scripts + docs into folders)
- Remove temporary Python artifacts (__pycache__, *.pyc)
- Be safe by default (dry-run). Use --apply to make changes.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Move:
    src: Path
    dst: Path


def _repo_root() -> Path:
    # This script lives in <repo>/scripts/
    return Path(__file__).resolve().parents[1]


def _iter_moves(root: Path) -> list[Move]:
    return [
        Move(root / "design.md", root / "docs" / "design.md"),
        Move(root / "list_routes.py", root / "tools" / "dev" / "list_routes.py"),
        Move(root / "validate_all.py", root / "tools" / "dev" / "validate_all.py"),
        Move(root / "test_mcp.py", root / "tools" / "dev" / "test_mcp.py"),
        Move(root / "scratch_test.py", root / "tools" / "dev" / "scratch_test.py"),
    ]


def _ensure_parent(path: Path, apply: bool, actions: list[dict]) -> None:
    if path.parent.exists():
        return
    actions.append({"action": "mkdir", "path": str(path.parent)})
    if apply:
        path.parent.mkdir(parents=True, exist_ok=True)


def _move_file(move: Move, apply: bool, actions: list[dict]) -> None:
    if not move.src.exists():
        return
    if move.src.resolve() == move.dst.resolve():
        return

    _ensure_parent(move.dst, apply, actions)
    actions.append({"action": "move", "src": str(move.src), "dst": str(move.dst)})
    if apply:
        shutil.move(str(move.src), str(move.dst))


def _delete_paths(paths: Iterable[Path], apply: bool, actions: list[dict]) -> None:
    for p in paths:
        if not p.exists():
            continue
        actions.append({"action": "delete", "path": str(p)})
        if not apply:
            continue
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        else:
            try:
                p.unlink()
            except FileNotFoundError:
                pass


def _find_python_artifacts(root: Path) -> list[Path]:
    artifacts: list[Path] = []
    for d in root.rglob("__pycache__"):
        artifacts.append(d)
    for f in root.rglob("*.pyc"):
        artifacts.append(f)
    return artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description="Organize repo structure and remove temp files.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually perform changes (default is dry-run).",
    )
    parser.add_argument(
        "--log",
        type=str,
        default=".repo_organize_log.json",
        help="Write a JSON log of planned/performed actions (relative to repo root).",
    )
    parser.add_argument(
        "--no-moves",
        action="store_true",
        help="Skip moving root-level scripts/docs.",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Skip deleting Python temp artifacts (__pycache__, *.pyc).",
    )
    args = parser.parse_args()

    root = _repo_root()
    actions: list[dict] = []

    if not args.no_moves:
        for mv in _iter_moves(root):
            _move_file(mv, apply=args.apply, actions=actions)

    if not args.no_clean:
        _delete_paths(_find_python_artifacts(root), apply=args.apply, actions=actions)

    # Write action log (always, even on dry run)
    log_path = root / args.log
    rel_actions = []
    for a in actions:
        rel = dict(a)
        for key in ("path", "src", "dst"):
            if key in rel:
                try:
                    rel[key] = str(Path(rel[key]).resolve().relative_to(root.resolve()))
                except Exception:
                    rel[key] = rel[key]
        rel_actions.append(rel)

    log_payload = {
        "repo_root": str(root),
        "apply": bool(args.apply),
        "actions": rel_actions,
    }
    log_path.write_text(json.dumps(log_payload, indent=2), encoding="utf-8")

    if args.apply:
        print(f"Applied {len(actions)} actions. Log written to {log_path}")
    else:
        print(f"Planned {len(actions)} actions (dry-run). Log written to {log_path}")
        print("Run again with --apply to perform the changes.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

