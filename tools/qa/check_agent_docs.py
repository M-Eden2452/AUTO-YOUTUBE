from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
CURRENT_DOCS = (
    Path("docs/current/START_HERE.md"),
    Path("docs/current/SYSTEM_MAP.md"),
    Path("docs/current/CURRENT_STATE.md"),
)
REQUIRED_SKILLS = (
    "create-short-video-first",
    "evaluate-render-quality",
    "resume-project",
    "replace-visual-slot",
    "architecture-change",
    "create-handoff",
)
REQUIRED_ARCHIVED_HANDOFFS = (
    "AUTONOMOUS_ARCHITECTURE_AUDIT.md",
    "AUTONOMOUS_IMPLEMENTATION_PLAN.md",
    "AUTONOMOUS_PROGRESS.md",
    "CLI_CHEATSHEET.md",
    "CURRENT_STATE.md",
    "HANDOFF_MANIFEST.json",
    "NEXT_PLAN.md",
    "PRODUCT_VISION_AND_ROADMAP.md",
    "REPO_SNAPSHOT.md",
    "START_HERE.md",
)
LOCAL_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")


def _frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("unterminated YAML frontmatter")
    payload = yaml.safe_load(text[4:end]) or {}
    if not isinstance(payload, dict):
        raise ValueError("frontmatter must be an object")
    return payload


def _local_links(path: Path) -> Iterable[Path]:
    for match in LOCAL_LINK_RE.finditer(path.read_text(encoding="utf-8")):
        raw = match.group(1).strip()
        if not raw or raw.startswith(("#", "http://", "https://", "mailto:")):
            continue
        target = raw.split("#", 1)[0].replace("%20", " ")
        if target:
            yield (path.parent / target).resolve()


def validate_repository(
    root: Path = REPO_ROOT,
    *,
    today: date | None = None,
    max_age_days: int = 120,
) -> list[str]:
    errors: list[str] = []
    today = today or date.today()

    linked_docs = [root / "AGENTS.md", root / "CLAUDE.md"]
    for relative in CURRENT_DOCS:
        path = root / relative
        linked_docs.append(path)
        if not path.is_file():
            errors.append(f"missing current document: {relative.as_posix()}")
            continue
        try:
            metadata = _frontmatter(path)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            errors.append(f"{relative.as_posix()}: {exc}")
            continue
        if metadata.get("status") != "current":
            errors.append(f"{relative.as_posix()}: status must be current")
        commit = str(metadata.get("last_verified_commit", ""))
        if not COMMIT_RE.fullmatch(commit):
            errors.append(f"{relative.as_posix()}: invalid last_verified_commit")
        try:
            verified = date.fromisoformat(str(metadata.get("last_verified_date", "")))
        except ValueError:
            errors.append(f"{relative.as_posix()}: invalid last_verified_date")
        else:
            age = (today - verified).days
            if age < 0:
                errors.append(f"{relative.as_posix()}: verification date is in the future")
            elif age > max_age_days:
                errors.append(
                    f"{relative.as_posix()}: metadata is stale ({age} days; max {max_age_days})"
                )
        sources = metadata.get("source_paths")
        if not isinstance(sources, list) or not sources:
            errors.append(f"{relative.as_posix()}: source_paths must be a non-empty list")
        else:
            for source in sources:
                source_path = root / str(source)
                if not source_path.exists():
                    errors.append(f"{relative.as_posix()}: missing source_path {source}")

    for skill_name in REQUIRED_SKILLS:
        skill_root = root / "skills" / skill_name
        skill_file = skill_root / "SKILL.md"
        agent_file = skill_root / "agents" / "openai.yaml"
        linked_docs.append(skill_file)
        if not skill_file.is_file():
            errors.append(f"missing skill: {skill_name}")
            continue
        try:
            metadata = _frontmatter(skill_file)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            errors.append(f"{skill_name}: {exc}")
            continue
        if set(metadata) != {"name", "description"}:
            errors.append(f"{skill_name}: SKILL.md frontmatter must contain only name/description")
        if metadata.get("name") != skill_name:
            errors.append(f"{skill_name}: frontmatter name mismatch")
        content = skill_file.read_text(encoding="utf-8")
        if "TODO" in content:
            errors.append(f"{skill_name}: unresolved TODO")
        if not agent_file.is_file():
            errors.append(f"{skill_name}: missing agents/openai.yaml")
        else:
            try:
                agent_metadata = yaml.safe_load(agent_file.read_text(encoding="utf-8")) or {}
                prompt = agent_metadata["interface"]["default_prompt"]
            except (KeyError, TypeError, yaml.YAMLError) as exc:
                errors.append(f"{skill_name}: invalid agents/openai.yaml ({exc})")
            else:
                if f"${skill_name}" not in prompt:
                    errors.append(f"{skill_name}: default_prompt must mention ${skill_name}")

    handoff_root = root / "docs" / "handoff"
    if handoff_root.is_dir():
        unexpected = sorted(
            path.name
            for path in handoff_root.iterdir()
            if path.is_file() and path.name != "PROJECT_RESCUE_MASTER_PLAN.md"
        )
        if unexpected:
            errors.append(f"historical files remain in docs/handoff: {', '.join(unexpected)}")
    archive_root = root / "docs" / "archive" / "handoff"
    for filename in REQUIRED_ARCHIVED_HANDOFFS:
        if not (archive_root / filename).is_file():
            errors.append(f"missing archived handoff: {filename}")

    for document in linked_docs:
        if not document.is_file():
            continue
        for target in _local_links(document):
            if not target.exists():
                try:
                    label = document.relative_to(root).as_posix()
                except ValueError:
                    label = str(document)
                errors.append(f"{label}: broken local link to {target}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate current agent docs and skills.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--max-age-days", type=int, default=120)
    args = parser.parse_args(argv)

    errors = validate_repository(args.root.resolve(), max_age_days=args.max_age_days)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Agent documentation and skills are current and internally consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
