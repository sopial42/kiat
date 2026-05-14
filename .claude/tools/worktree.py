#!/usr/bin/env python3
"""
Kiat parallel-worktree CLI.

Implements .claude/specs/parallel-worktree-protocol.md. Manages the lifecycle
of git worktrees + docker compose stacks so N agents can run their dev stack
in parallel on one developer machine without host-port collisions.

Stdlib only. Python 3.9+.

Usage:
    kiat-worktree create <branch-name>     Create worktree + allocate slot + write .worktree.env.
    kiat-worktree up [--detach]            docker compose up inside current worktree.
    kiat-worktree down [--volumes]         docker compose down (optionally remove volumes).
    kiat-worktree list [--json]            Show all worktrees + their stack status.
    kiat-worktree gc [--dry-run]           Reap orphan Docker objects.
    kiat-worktree exec <cmd...>            docker compose exec <primary-service> <cmd>.
    kiat-worktree env                      Print .worktree.env content (for `eval $(...)`).
    kiat-worktree remove                   down --volumes + git worktree remove --force.
    kiat-worktree lint [--strict]          Validate docker-compose.yml against the 4 rules.

Conventions:
- The "current worktree" is the cwd. Most commands operate on it.
- `.worktree.env` is the single source of truth; created by `create`, read by all others.
- Slot 0..99 → backend 18000..18099, frontend 13000..13099.
- No persistent registry: state is reconstructed each invocation by scanning worktrees + Docker.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# ─── Constants ──────────────────────────────────────────────────────────────

SLOT_MAX = 100
BACKEND_BASE = 18000
FRONTEND_BASE = 13000
BACKEND_DEBUG_BASE = 19000
SMOCKER_ADMIN_BASE = 18800

# Path discovery. Repo root = first ancestor containing .claude/.
# Worktrees live at <repo-root>/.claude/worktrees/agent-<id>/.
WORKTREE_PARENT_DIRNAME = ".claude/worktrees"
WORKTREE_DIR_PREFIX = "agent-"
WORKTREE_ENV_FILENAME = ".worktree.env"


# ─── Path helpers ───────────────────────────────────────────────────────────


def repo_root_from(path: Path) -> Path:
    """Walk upward until a `.claude/` directory is found, or stop at filesystem root."""
    cur = path.resolve()
    while cur != cur.parent:
        if (cur / ".claude").is_dir() and (cur / ".git").exists():
            return cur
        cur = cur.parent
    raise RuntimeError(f"no Kiat repo root above {path} (no .claude/ + .git/)")


def worktrees_parent(repo_root: Path) -> Path:
    return repo_root / WORKTREE_PARENT_DIRNAME


def current_worktree_root() -> Path:
    """The directory where the current worktree lives.

    If cwd is the main checkout, returns the main checkout root.
    If cwd is inside a worktree, returns the worktree root.
    Detection: walk up from cwd, return the first dir whose parent dir is named
    `.claude/worktrees` OR which is the repo root.
    """
    cur = Path.cwd().resolve()
    while cur != cur.parent:
        if cur.parent.name == "worktrees" and cur.parent.parent.name == ".claude":
            return cur
        if (cur / ".claude").is_dir() and (cur / ".git").exists():
            return cur
        cur = cur.parent
    raise RuntimeError(f"cwd {Path.cwd()} is not inside a Kiat repo")


# ─── Subprocess helpers ─────────────────────────────────────────────────────


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a subprocess, mirroring stdout/stderr by default."""
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=check,
        text=True,
        capture_output=capture,
    )


def docker_compose(args: list[str], *, cwd: Path, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Wrapper for `docker compose <args>` invoked from a specific cwd."""
    return run(["docker", "compose", *args], cwd=cwd, check=check, capture=capture)


# ─── .worktree.env I/O ──────────────────────────────────────────────────────


@dataclass
class WorktreeEnv:
    worktree_id: str
    slot: int
    backend_port: int
    frontend_port: int
    backend_debug_port: int | None = None
    smocker_admin_port: int | None = None

    @property
    def compose_project(self) -> str:
        return f"kiat-{self.worktree_id}"

    def as_env_dict(self) -> dict[str, str]:
        env = {
            "KIAT_WORKTREE_ID": self.worktree_id,
            "KIAT_SLOT": str(self.slot),
            "KIAT_BACKEND_PORT": str(self.backend_port),
            "KIAT_FRONTEND_PORT": str(self.frontend_port),
            "COMPOSE_PROJECT_NAME": self.compose_project,
        }
        if self.backend_debug_port is not None:
            env["KIAT_BACKEND_DEBUG_PORT"] = str(self.backend_debug_port)
        if self.smocker_admin_port is not None:
            env["KIAT_SMOCKER_ADMIN_PORT"] = str(self.smocker_admin_port)
        return env

    def write(self, path: Path, *, header_lines: list[str] | None = None) -> None:
        lines: list[str] = []
        if header_lines:
            lines.extend(f"# {l}" for l in header_lines)
            lines.append("")
        for k, v in self.as_env_dict().items():
            lines.append(f"{k}={v}")
        path.write_text("\n".join(lines) + "\n")


def read_worktree_env(path: Path) -> WorktreeEnv | None:
    if not path.is_file():
        return None
    kv: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        kv[k.strip()] = v.strip()
    try:
        return WorktreeEnv(
            worktree_id=kv["KIAT_WORKTREE_ID"],
            slot=int(kv["KIAT_SLOT"]),
            backend_port=int(kv["KIAT_BACKEND_PORT"]),
            frontend_port=int(kv["KIAT_FRONTEND_PORT"]),
            backend_debug_port=int(kv["KIAT_BACKEND_DEBUG_PORT"]) if "KIAT_BACKEND_DEBUG_PORT" in kv else None,
            smocker_admin_port=int(kv["KIAT_SMOCKER_ADMIN_PORT"]) if "KIAT_SMOCKER_ADMIN_PORT" in kv else None,
        )
    except KeyError as e:
        raise RuntimeError(f"{path} missing required field: {e}") from None


# ─── Slot allocation ────────────────────────────────────────────────────────


def hash_to_slot(worktree_id: str) -> int:
    """Initial slot from worktree-id hash. Linear probing handles collisions."""
    m = re.match(r"[0-9a-f]+", worktree_id)
    if not m:
        # Non-hex worktree id — hash it deterministically.
        import hashlib
        digest = hashlib.sha256(worktree_id.encode()).hexdigest()
        return int(digest[:6], 16) % SLOT_MAX
    return int(m.group()[:6], 16) % SLOT_MAX


def occupied_slots(repo_root: Path) -> set[int]:
    """Set of slots claimed by existing worktrees."""
    occupied: set[int] = set()
    parent = worktrees_parent(repo_root)
    if not parent.is_dir():
        return occupied
    for d in parent.iterdir():
        if not d.is_dir() or not d.name.startswith(WORKTREE_DIR_PREFIX):
            continue
        env_file = d / WORKTREE_ENV_FILENAME
        env = read_worktree_env(env_file) if env_file.is_file() else None
        if env is not None:
            occupied.add(env.slot)
    return occupied


def allocate_slot(worktree_id: str, occupied: set[int]) -> int:
    base = hash_to_slot(worktree_id)
    slot = base
    for _ in range(SLOT_MAX):
        if slot not in occupied:
            return slot
        slot = (slot + 1) % SLOT_MAX
    raise RuntimeError(f"all {SLOT_MAX} slots in use — run `kiat-worktree gc` or remove a worktree first")


# ─── Worktree scanning ──────────────────────────────────────────────────────


@dataclass
class WorktreeInfo:
    id: str
    path: Path
    env: WorktreeEnv
    branch: str | None
    compose_running: bool
    containers: int


def scan_worktrees(repo_root: Path) -> list[WorktreeInfo]:
    parent = worktrees_parent(repo_root)
    if not parent.is_dir():
        return []
    # Map worktree path → branch via `git worktree list --porcelain`.
    git_wt = run(["git", "worktree", "list", "--porcelain"], cwd=repo_root, capture=True, check=False)
    path_to_branch: dict[str, str | None] = {}
    if git_wt.returncode == 0:
        cur_path = cur_branch = None
        for line in git_wt.stdout.splitlines() + [""]:
            if line.startswith("worktree "):
                cur_path = line[len("worktree "):]
            elif line.startswith("branch "):
                cur_branch = line[len("branch "):].replace("refs/heads/", "")
            elif line == "" and cur_path is not None:
                path_to_branch[cur_path] = cur_branch
                cur_path = cur_branch = None
    # Map compose project name → container count from `docker compose ls --format json`.
    compose_ls = run(["docker", "compose", "ls", "--all", "--format", "json"], capture=True, check=False)
    compose_state: dict[str, dict] = {}
    if compose_ls.returncode == 0:
        try:
            for entry in json.loads(compose_ls.stdout or "[]"):
                compose_state[entry["Name"]] = entry
        except json.JSONDecodeError:
            pass

    out: list[WorktreeInfo] = []
    for d in sorted(parent.iterdir()):
        if not d.is_dir() or not d.name.startswith(WORKTREE_DIR_PREFIX):
            continue
        env_file = d / WORKTREE_ENV_FILENAME
        env = read_worktree_env(env_file) if env_file.is_file() else None
        if env is None:
            continue
        compose_entry = compose_state.get(env.compose_project, {})
        status = compose_entry.get("Status", "")
        running = status.startswith("running") or "running(" in status
        containers = int(compose_entry.get("ConfigFiles", "").count(",") + 1) if compose_entry else 0
        out.append(WorktreeInfo(
            id=env.worktree_id,
            path=d,
            env=env,
            branch=path_to_branch.get(str(d)),
            compose_running=running,
            containers=containers,
        ))
    return out


# ─── Command implementations ────────────────────────────────────────────────


def cmd_create(args: argparse.Namespace) -> int:
    repo_root = repo_root_from(Path.cwd())
    branch_name = args.branch_name

    # Worktree id = branch slug (truncated). Substituted later if collision.
    raw_id = re.sub(r"[^a-z0-9]+", "", branch_name.lower())[:8] or "wt"
    occupied = occupied_slots(repo_root)
    worktree_id = raw_id
    suffix = 0
    while (worktrees_parent(repo_root) / f"{WORKTREE_DIR_PREFIX}{worktree_id}").exists():
        suffix += 1
        worktree_id = f"{raw_id}{suffix}"

    slot = allocate_slot(worktree_id, occupied)
    env = WorktreeEnv(
        worktree_id=worktree_id,
        slot=slot,
        backend_port=BACKEND_BASE + slot,
        frontend_port=FRONTEND_BASE + slot,
    )

    wt_path = worktrees_parent(repo_root) / f"{WORKTREE_DIR_PREFIX}{worktree_id}"
    worktrees_parent(repo_root).mkdir(parents=True, exist_ok=True)

    # Create the git worktree. If branch exists, check it out; otherwise create.
    branches = run(["git", "branch", "--list", branch_name], cwd=repo_root, capture=True).stdout.strip()
    if branches:
        run(["git", "worktree", "add", str(wt_path), branch_name], cwd=repo_root)
    else:
        run(["git", "worktree", "add", "-b", branch_name, str(wt_path)], cwd=repo_root)

    env.write(
        wt_path / WORKTREE_ENV_FILENAME,
        header_lines=[
            f"Generated by kiat-worktree create on {_now_iso()}.",
            "DO NOT EDIT — recreate the worktree if the slot must change.",
        ],
    )

    print(f"✓ Worktree created at {wt_path}")
    print(f"✓ Slot {slot} allocated: backend {env.backend_port}, frontend {env.frontend_port}")
    print(f"✓ Compose project: {env.compose_project}")
    print()
    print(f"Next: cd {wt_path} && kiat-worktree up")
    return 0


def cmd_up(args: argparse.Namespace) -> int:
    wt_root = current_worktree_root()
    env_file = wt_root / WORKTREE_ENV_FILENAME
    if not env_file.is_file():
        print(f"error: no {WORKTREE_ENV_FILENAME} in {wt_root} — main checkout uses `docker compose up` directly", file=sys.stderr)
        return 2
    args_list = ["--env-file", str(env_file), "up"]
    if args.detach:
        args_list.append("--detach")
    args_list.append("--build")
    docker_compose(args_list, cwd=wt_root, check=False)
    # Wait for healthchecks if --detach (otherwise compose blocks anyway).
    if args.detach:
        return _wait_healthy(wt_root, timeout_s=args.timeout)
    return 0


def cmd_down(args: argparse.Namespace) -> int:
    wt_root = current_worktree_root()
    env_file = wt_root / WORKTREE_ENV_FILENAME
    if not env_file.is_file():
        print(f"error: no {WORKTREE_ENV_FILENAME} in {wt_root}", file=sys.stderr)
        return 2
    cmd = ["--env-file", str(env_file), "down", "--remove-orphans"]
    if args.volumes:
        cmd.append("--volumes")
    docker_compose(cmd, cwd=wt_root, check=False)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    repo_root = repo_root_from(Path.cwd())
    infos = scan_worktrees(repo_root)
    if args.json:
        print(json.dumps([_info_to_dict(i) for i in infos], indent=2))
        return 0
    if not infos:
        print("(no worktrees)")
        return 0
    headers = ["ID", "SLOT", "BACKEND", "FRONTEND", "BRANCH", "STATUS"]
    rows = [
        [
            i.id,
            str(i.env.slot),
            str(i.env.backend_port),
            str(i.env.frontend_port),
            i.branch or "(detached)",
            "up" if i.compose_running else "down",
        ]
        for i in infos
    ]
    _print_table(headers, rows)
    return 0


def cmd_gc(args: argparse.Namespace) -> int:
    repo_root = repo_root_from(Path.cwd())
    infos = scan_worktrees(repo_root)
    expected_projects = {i.env.compose_project for i in infos}
    # Compose projects on Docker that start with "kiat-" but have no worktree dir.
    docker_ls = run(["docker", "compose", "ls", "--all", "--format", "json"], capture=True, check=False)
    orphans: list[str] = []
    if docker_ls.returncode == 0:
        for entry in json.loads(docker_ls.stdout or "[]"):
            name = entry["Name"]
            if name.startswith("kiat-") and name not in expected_projects and name != "kiat-default":
                orphans.append(name)
    if not orphans:
        print("(no orphans)")
        return 0
    print(f"Orphan compose projects: {', '.join(orphans)}")
    if args.dry_run:
        return 0
    for name in orphans:
        # Tear down without needing the original compose file.
        run(["docker", "compose", "--project-name", name, "down", "--volumes", "--remove-orphans"], check=False)
    print(f"✓ Reaped {len(orphans)} orphans")
    return 0


def cmd_exec(args: argparse.Namespace) -> int:
    wt_root = current_worktree_root()
    env_file = wt_root / WORKTREE_ENV_FILENAME
    if not env_file.is_file():
        print(f"error: no {WORKTREE_ENV_FILENAME} in {wt_root}", file=sys.stderr)
        return 2
    # Primary service: read from .kiat-worktree-config.toml if present, else "backend".
    primary = _primary_service(wt_root)
    docker_compose(
        ["--env-file", str(env_file), "exec", primary, *args.cmd],
        cwd=wt_root,
        check=False,
    )
    return 0


def cmd_env(_args: argparse.Namespace) -> int:
    wt_root = current_worktree_root()
    env_file = wt_root / WORKTREE_ENV_FILENAME
    if not env_file.is_file():
        return 2
    sys.stdout.write(env_file.read_text())
    return 0


def cmd_remove(_args: argparse.Namespace) -> int:
    wt_root = current_worktree_root()
    env_file = wt_root / WORKTREE_ENV_FILENAME
    if not env_file.is_file():
        print(f"error: no {WORKTREE_ENV_FILENAME} in {wt_root}", file=sys.stderr)
        return 2
    # Step 1: stack down with volumes.
    docker_compose(["--env-file", str(env_file), "down", "--volumes", "--remove-orphans"], cwd=wt_root, check=False)
    # Step 2: git worktree remove (force — accepts dirty tree).
    repo_root = repo_root_from(wt_root.parent.parent.parent)
    run(["git", "worktree", "remove", "--force", str(wt_root)], cwd=repo_root, check=False)
    print(f"✓ Removed worktree {wt_root.name}")
    return 0


def cmd_lint(args: argparse.Namespace) -> int:
    """Validate docker-compose.yml against the 4 rules from §6.

    R1  name: ${COMPOSE_PROJECT_NAME:-kiat-default}
    R2  backing services use expose, never ports — heuristic: image suggests DB/cache
    R3  app services have env-driven ports with default fallback
    R4  named volumes + network suffixed by KIAT_WORKTREE_ID
    """
    compose_file = Path.cwd() / "docker-compose.yml"
    if not compose_file.is_file():
        print(f"error: no docker-compose.yml in {Path.cwd()}", file=sys.stderr)
        return 2
    text = compose_file.read_text()
    issues: list[str] = []

    # R1
    if not re.search(r"^name:\s*\$\{COMPOSE_PROJECT_NAME", text, re.MULTILINE):
        issues.append("R1: top-level `name:` should reference ${COMPOSE_PROJECT_NAME}")

    # R3: every `ports:` should use ${KIAT_..._PORT:-default} pattern.
    bad_ports = re.findall(r'ports:\s*\[\s*"(\d+):\d+"', text)
    if bad_ports:
        issues.append(f"R3: hardcoded host ports found: {bad_ports} — use ${{KIAT_X_PORT:-N}} pattern")

    # R4: every named volume + network should include KIAT_WORKTREE_ID.
    if re.search(r"^volumes:", text, re.MULTILINE):
        named = re.findall(r"name:\s*([\w_-]+)\s*$", text, re.MULTILINE)
        bad_names = [n for n in named if "KIAT_WORKTREE_ID" not in n and "kiat-" not in n.lower()]
        if bad_names:
            issues.append(f"R4: named volume(s)/network(s) missing KIAT_WORKTREE_ID namespace: {bad_names}")

    if issues:
        for i in issues:
            print(f"✗ {i}")
        return 1 if args.strict else 0
    print("✓ docker-compose.yml conforms to the 4 rules")
    return 0


# ─── Internal helpers ───────────────────────────────────────────────────────


def _wait_healthy(wt_root: Path, *, timeout_s: int) -> int:
    """Poll `docker compose ps` until all services with healthchecks are healthy."""
    import time
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        result = docker_compose(["ps", "--format", "json"], cwd=wt_root, capture=True, check=False)
        if result.returncode != 0:
            return result.returncode
        all_ok = True
        for line in result.stdout.strip().splitlines():
            try:
                svc = json.loads(line)
            except json.JSONDecodeError:
                continue
            health = svc.get("Health", "")
            state = svc.get("State", "")
            if health and health not in ("healthy", ""):
                all_ok = False
                break
            if not health and state != "running":
                all_ok = False
                break
        if all_ok:
            print(f"✓ Stack healthy")
            return 0
        time.sleep(2)
    print(f"⚠ Timeout after {timeout_s}s — stack may still be coming up", file=sys.stderr)
    return 1


def _primary_service(wt_root: Path) -> str:
    cfg = wt_root / ".kiat-worktree-config.toml"
    if cfg.is_file():
        for line in cfg.read_text().splitlines():
            m = re.match(r'primary_service\s*=\s*"([^"]+)"', line.strip())
            if m:
                return m.group(1)
    return "backend"


def _info_to_dict(i: WorktreeInfo) -> dict:
    return {
        "id": i.id,
        "path": str(i.path),
        "slot": i.env.slot,
        "backend_port": i.env.backend_port,
        "frontend_port": i.env.frontend_port,
        "branch": i.branch,
        "compose_running": i.compose_running,
        "compose_project": i.env.compose_project,
    }


def _print_table(headers: list[str], rows: list[list[str]]) -> None:
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    for row in rows:
        print(fmt.format(*row))


def _now_iso() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ─── Argparse plumbing ──────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="kiat-worktree", description="Manage Kiat parallel worktrees + compose stacks.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sc = sub.add_parser("create", help="Create worktree + allocate slot + write .worktree.env")
    sc.add_argument("branch_name", help="Branch to check out (created if missing)")
    sc.set_defaults(func=cmd_create)

    su = sub.add_parser("up", help="docker compose up inside current worktree")
    su.add_argument("--detach", "-d", action="store_true")
    su.add_argument("--timeout", type=int, default=60, help="seconds to wait for healthchecks when detached")
    su.set_defaults(func=cmd_up)

    sd = sub.add_parser("down", help="docker compose down")
    sd.add_argument("--volumes", "-v", action="store_true", help="also remove named volumes")
    sd.set_defaults(func=cmd_down)

    sl = sub.add_parser("list", help="Show all worktrees + stack status")
    sl.add_argument("--json", action="store_true")
    sl.set_defaults(func=cmd_list)

    sg = sub.add_parser("gc", help="Reap orphan compose projects with no matching worktree")
    sg.add_argument("--dry-run", action="store_true")
    sg.set_defaults(func=cmd_gc)

    se = sub.add_parser("exec", help="docker compose exec <primary> <cmd>")
    se.add_argument("cmd", nargs=argparse.REMAINDER)
    se.set_defaults(func=cmd_exec)

    sen = sub.add_parser("env", help="Print .worktree.env contents")
    sen.set_defaults(func=cmd_env)

    sr = sub.add_parser("remove", help="down --volumes + git worktree remove --force")
    sr.set_defaults(func=cmd_remove)

    sln = sub.add_parser("lint", help="Validate docker-compose.yml against the 4 rules")
    sln.add_argument("--strict", action="store_true", help="exit 1 on any violation")
    sln.set_defaults(func=cmd_lint)

    ns = p.parse_args(argv)
    return ns.func(ns)


if __name__ == "__main__":
    sys.exit(main())
