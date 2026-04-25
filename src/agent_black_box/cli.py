from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


RUNS_DIR = ".agent-black-box/runs"
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*[^\s]+"),
]


def redact(text: str) -> str:
    output = text
    for pattern in SECRET_PATTERNS:
        output = pattern.sub("[REDACTED]", output)
    return output


def git_output(root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), *args],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return ""


def run_id(label: str | None = None) -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    if not label:
        return stamp
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", label).strip("-").lower()
    return f"{stamp}-{safe}" if safe else stamp


def summarize_diff(diff: str) -> dict[str, int]:
    added = 0
    removed = 0
    files = 0
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            files += 1
        elif line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1
    return {"files_changed": files, "lines_added": added, "lines_removed": removed}


def record(
    command: list[str],
    root: str | Path = ".",
    label: str | None = None,
    redact_output: bool = True,
) -> tuple[dict[str, Any], Path]:
    root = Path(root).resolve()
    command = resolve_command(command)
    outdir = root / RUNS_DIR / run_id(label)
    outdir.mkdir(parents=True, exist_ok=False)

    before_status = git_output(root, "status", "--short")
    before_head = git_output(root, "rev-parse", "--short", "HEAD").strip()
    start = time.time()
    proc = subprocess.run(command, cwd=root, text=True, capture_output=True)
    end = time.time()

    after_status = git_output(root, "status", "--short")
    diff = git_output(root, "diff")
    stdout = redact(proc.stdout) if redact_output else proc.stdout
    stderr = redact(proc.stderr) if redact_output else proc.stderr

    (outdir / "stdout.txt").write_text(stdout, encoding="utf-8")
    (outdir / "stderr.txt").write_text(stderr, encoding="utf-8")
    (outdir / "diff.patch").write_text(diff, encoding="utf-8")

    diff_summary = summarize_diff(diff)
    manifest = {
        "id": outdir.name,
        "label": label,
        "command": command,
        "cwd": str(root),
        "exit_code": proc.returncode,
        "duration_seconds": round(end - start, 3),
        "git_head": before_head or None,
        "status_before": before_status.splitlines(),
        "status_after": after_status.splitlines(),
        "diff_summary": diff_summary,
        "stdout_bytes": len(stdout.encode("utf-8")),
        "stderr_bytes": len(stderr.encode("utf-8")),
        "redacted_output": redact_output,
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    (outdir / "summary.md").write_text(render_summary(manifest), encoding="utf-8")
    return manifest, outdir


def resolve_command(command: list[str]) -> list[str]:
    if command and command[0] == "python" and not shutil.which("python"):
        return [sys.executable, *command[1:]]
    return command


def render_summary(manifest: dict[str, Any]) -> str:
    diff = manifest["diff_summary"]
    status = "passed" if manifest["exit_code"] == 0 else "failed"
    return (
        f"# Agent Run {manifest['id']}\n\n"
        f"- Status: {status}\n"
        f"- Exit code: {manifest['exit_code']}\n"
        f"- Duration: {manifest['duration_seconds']}s\n"
        f"- Command: `{' '.join(manifest['command'])}`\n"
        f"- Files changed: {diff['files_changed']}\n"
        f"- Lines added: {diff['lines_added']}\n"
        f"- Lines removed: {diff['lines_removed']}\n"
    )


def runs_root(root: str | Path = ".") -> Path:
    return Path(root).resolve() / RUNS_DIR


def list_runs(root: str | Path = ".") -> list[dict[str, Any]]:
    directory = runs_root(root)
    if not directory.exists():
        return []
    manifests = []
    for path in sorted(directory.glob("*/manifest.json"), reverse=True):
        manifests.append(json.loads(path.read_text(encoding="utf-8")))
    return manifests


def show_run(run: str, root: str | Path = ".") -> dict[str, Any]:
    path = runs_root(root) / run / "manifest.json"
    if not path.exists():
        raise FileNotFoundError(f"No recorded run found at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def print_table(runs: list[dict[str, Any]]) -> None:
    if not runs:
        print("No runs recorded yet.")
        return
    for item in runs:
        diff = item["diff_summary"]
        print(
            f"{item['id']} exit={item['exit_code']} "
            f"files={diff['files_changed']} +{diff['lines_added']} -{diff['lines_removed']}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Flight recorder for AI coding agents and risky commands."
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Record a command.")
    run_parser.add_argument("cmd", nargs=argparse.REMAINDER)
    run_parser.add_argument("--label", help="Human-readable run label.")
    run_parser.add_argument("--root", default=".", help="Repository root.")
    run_parser.add_argument("--json", action="store_true", help="Print JSON manifest.")
    run_parser.add_argument(
        "--no-redact",
        action="store_true",
        help="Do not redact common secrets from stdout/stderr.",
    )

    list_parser = subparsers.add_parser("list", help="List recorded runs.")
    list_parser.add_argument("--root", default=".", help="Repository root.")
    list_parser.add_argument("--json", action="store_true", help="Print JSON.")

    show_parser = subparsers.add_parser("show", help="Show one recorded run.")
    show_parser.add_argument("run_id")
    show_parser.add_argument("--root", default=".", help="Repository root.")
    show_parser.add_argument("--json", action="store_true", help="Print JSON.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    command = args.command or "run"
    if command == "list":
        runs = list_runs(args.root)
        if args.json:
            print(json.dumps({"runs": runs}, indent=2))
        else:
            print_table(runs)
        return

    if command == "show":
        manifest = show_run(args.run_id, args.root)
        if args.json:
            print(json.dumps(manifest, indent=2))
        else:
            print(render_summary(manifest), end="")
        return

    cmd = args.cmd[1:] if getattr(args, "cmd", [])[:1] == ["--"] else getattr(args, "cmd", [])
    if not cmd:
        raise SystemExit("Pass a command after `agent-black-box run --`.")

    manifest, outdir = record(
        cmd,
        root=args.root,
        label=args.label,
        redact_output=not args.no_redact,
    )
    if args.json:
        print(json.dumps({"run_dir": str(outdir), "manifest": manifest}, indent=2))
    else:
        print(f"recorded: {outdir}")
        print(render_summary(manifest), end="")
    raise SystemExit(manifest["exit_code"])


if __name__ == "__main__":
    main()
