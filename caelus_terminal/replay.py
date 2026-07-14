from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any


_RECIPE_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_CREDENTIAL_PATTERN = re.compile(
    r"(?i)\b(?:api[_-]?key|token|secret|password|authorization)\b\s*[:=]\s*\S+|\bsk-[A-Za-z0-9_-]{12,}\b"
)


class ReplayValidationError(ValueError):
    """Raised when a Replay recipe is unsafe or malformed."""


@dataclass(frozen=True)
class ReplayRecipe:
    name: str
    domains: list[str]
    steps: list[str]
    verification: str
    side_effect_policy: str = "read-only"
    version: int = 1


def default_recipes_dir() -> Path:
    return Path.home() / ".caelus" / "replays"


def _require_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReplayValidationError(f"Replay {field} must be non-empty")
    value = value.strip()
    if _CREDENTIAL_PATTERN.search(value):
        raise ReplayValidationError(f"Replay {field} contains credential-like content")
    return value


def _recipe_name(name: str) -> str:
    name = _require_text(name, "name").lower()
    if not _RECIPE_NAME.fullmatch(name):
        raise ReplayValidationError("Replay name must use lowercase letters, numbers, and hyphens")
    return name


def _recipe_path(recipes_dir: Path, name: str) -> Path:
    return Path(recipes_dir) / f"{_recipe_name(name)}.json"


def create_recipe(
    recipes_dir: Path,
    *,
    name: str,
    domains: list[str],
    steps: list[str],
    verification: str,
) -> ReplayRecipe:
    """Persist a narrow, read-only browser Replay recipe without private state."""
    normalized_name = _recipe_name(name)
    normalized_domains = [_require_text(domain, "domain").lower() for domain in domains]
    normalized_steps = [_require_text(step, "step") for step in steps]
    if not normalized_domains:
        raise ReplayValidationError("Replay requires at least one allowed domain")
    if not normalized_steps:
        raise ReplayValidationError("Replay requires at least one step")
    if any("/" in domain or ":" in domain or " " in domain for domain in normalized_domains):
        raise ReplayValidationError("Replay domains must be hostnames only")
    recipe = ReplayRecipe(
        name=normalized_name,
        domains=list(dict.fromkeys(normalized_domains)),
        steps=normalized_steps,
        verification=_require_text(verification, "verification"),
    )
    path = _recipe_path(recipes_dir, normalized_name)
    if path.exists():
        raise ReplayValidationError(f"Replay already exists: {normalized_name}")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(recipe), indent=2, sort_keys=True) + "\n")
    path.chmod(0o600)
    return recipe


def load_recipe(recipes_dir: Path, name: str) -> ReplayRecipe:
    path = _recipe_path(recipes_dir, name)
    if not path.is_file():
        raise ReplayValidationError(f"Replay not found: {name}")
    try:
        raw: dict[str, Any] = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ReplayValidationError(f"Replay is invalid JSON: {name}") from exc
    if not isinstance(raw, dict) or set(raw) != {
        "domains", "name", "side_effect_policy", "steps", "verification", "version"
    }:
        raise ReplayValidationError(f"Replay has unsupported fields: {name}")
    if raw.get("version") != 1 or raw.get("side_effect_policy") != "read-only":
        raise ReplayValidationError(f"Replay has unsupported policy or version: {name}")
    return ReplayRecipe(
        name=_recipe_name(raw.get("name", "")),
        domains=[_require_text(domain, "domain").lower() for domain in raw.get("domains", [])],
        steps=[_require_text(step, "step") for step in raw.get("steps", [])],
        verification=_require_text(raw.get("verification", ""), "verification"),
        side_effect_policy=raw["side_effect_policy"],
        version=raw["version"],
    )


def render_preview(recipe: ReplayRecipe) -> str:
    steps = "\n".join(f"  {index}. {step}" for index, step in enumerate(recipe.steps, start=1))
    return "\n".join(
        [
            f"PREVIEW — {recipe.name}",
            f"Allowed domains: {', '.join(recipe.domains)}",
            "Read-only policy: no submissions, messages, purchases, deletions, or publishing.",
            "Steps:",
            steps,
            f"Verification: {recipe.verification}",
        ]
    )


def build_run_instruction(recipe: ReplayRecipe) -> str:
    steps = "\n".join(f"{index}. {step}" for index, step in enumerate(recipe.steps, start=1))
    return "\n".join(
        [
            f"Execute the Caelus Replay recipe: {recipe.name}",
            f"Operate only on these domains: {', '.join(recipe.domains)}.",
            "This is a read-only workflow.",
            "Do not submit forms, send messages, make purchases, delete data, publish anything, or change settings.",
            "Do not enter, request, reveal, or store passwords, tokens, API keys, cookies, or other secrets.",
            "If a required page state differs from the recipe or verification cannot be proven, stop and report the mismatch instead of guessing success.",
            "Steps:",
            steps,
            f"Success criterion: {recipe.verification}",
        ]
    )


def receipt_path(recipes_dir: Path, recipe_name: str, run_id: str) -> Path:
    directory = Path(recipes_dir) / "receipts"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    return directory / f"{_recipe_name(recipe_name)}-{_require_text(run_id, 'run ID')}.json"


def write_receipt(
    recipes_dir: Path,
    recipe: ReplayRecipe,
    *,
    run_id: str,
    status: str,
    tool_events: list[str],
    output: str,
) -> Path:
    if status not in {"completed", "failed", "cancelled"}:
        raise ReplayValidationError("Replay receipt has an unsupported status")
    receipt = {
        "recipe": recipe.name,
        "run_id": _require_text(run_id, "run ID"),
        "status": status,
        "verification": recipe.verification,
        "tool_events": tool_events,
        "output": output,
    }
    path = receipt_path(recipes_dir, recipe.name, run_id)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    path.chmod(0o600)
    return path
