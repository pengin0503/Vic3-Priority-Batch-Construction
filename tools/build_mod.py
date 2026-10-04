from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC_MOD_DIR = ROOT / "mod"

COMPATIBILITY_WARNING = (
    "Compatibility warning: this builder targets only Victoria 3 1.14.x; "
    "the installed game version is not auto-detected and combined-key behavior requires an in-game probe."
)

REQUIRED_QUEUE_TEMPLATE = "game/gui/building_details_panel.gui"

STANDARD_COUNTS = {"default": 1, "shift": 5, "ctrl": 10, "alt": 1}
PROBE_QUEUE_COUNTS = {"default": 1, "shift": 2, "ctrl": 3, "alt": 4}

_GUI_TOKEN = re.compile(r'#[^\r\n]*|"(?:\\.|[^"\\])*"|[A-Za-z_]\w*|[^\s]')
_TARGET_ACTION = re.compile(r'\bBuilding\.(QueueConstruction|CancelConstruction)\b')
_PLAIN_ACTION = re.compile(
    r'"\[Execute\([ \t]*Building\.(QueueConstruction|CancelConstruction)[ \t]*\)\]"'
)


def _gui_assignments(text: str) -> list[tuple[int, int, str, str, int]]:
    """Read property assignments and their brace scopes without interpreting strings."""
    tokens = [token for token in _GUI_TOKEN.finditer(text) if not token.group().startswith("#")]
    scopes = [0]
    assignments = []
    for index, token in enumerate(tokens):
        if token.group() == "{":
            scopes.append(token.start() + 1)
        elif token.group() == "}":
            if len(scopes) > 1:
                scopes.pop()
        elif (index + 2 < len(tokens) and
              re.fullmatch(r"[A-Za-z_]\w*", token.group()) and tokens[index + 1].group() == "="):
            value = tokens[index + 2]
            assignments.append((token.start(), value.end(), token.group(), value.group(), scopes[-1]))
    return assignments


def _target_handlers(text: str) -> list[tuple[int, int, str, str]]:
    """Find executable handler assignments, skipping comments and quoted GUI text."""
    handlers = []
    for start, end, key, value, _ in _gui_assignments(text):
        if not key.startswith("on") or not value.startswith('"'):
            continue
        action = _TARGET_ACTION.search(value)
        if action:
            handlers.append((start, end, key, action.group(1)))
    return handlers


def _handler_block(indent: str, action: str, counts: dict[str, int]) -> str:
    inner = indent + "\t"
    lines = [
        indent + "# PRIORITY_BATCH_BEGIN",
        indent + "click_modifiers = {",
    ]
    for modifier in ("default", "shift", "ctrl", "alt"):
        lines.extend(
            inner + f'on{modifier} = "[Execute( Building.{action} )]"'
            for _ in range(counts[modifier])
        )
    lines.extend([
        indent + "}",
        indent + "# PRIORITY_BATCH_END",
    ])
    return "\n".join(lines)


def patch_gui_text(text: str, probe: bool = False) -> tuple[str, int]:
    """Patch all building queue/cancel clicks, rejecting unsupported handlers."""
    queue_counts = PROBE_QUEUE_COUNTS if probe else STANDARD_COUNTS
    handlers = _target_handlers(text)
    if not handlers:
        raise ValueError("No vanilla Building.QueueConstruction or Building.CancelConstruction onclick found")
    replacements = []
    for start, end, key, action in handlers:
        line_start = text.rfind("\n", 0, start) + 1
        line_end = text.find("\n", end)
        if line_end == -1:
            line_end = len(text)
        indent = text[line_start:start]
        trailing = text[end:line_end]
        value = text[start:end].split("=", 1)[1].strip()
        if (key != "onclick" or indent.strip() or
                not _PLAIN_ACTION.fullmatch(value) or
                (trailing.strip() and not trailing.lstrip().startswith("#"))):
            line = text.count("\n", 0, start) + 1
            raise ValueError(f"Unsupported Building.{action} handler at line {line}; expected standalone onclick")
        counts = queue_counts if action == "QueueConstruction" else STANDARD_COUNTS
        # Keep the original trailing comment next to the generated block.
        replacement = _handler_block(indent, action, counts) + trailing
        replacements.append((line_start, line_end, replacement))
    assignments = _gui_assignments(text)
    scope_by_start = {start: scope for start, _, _, _, scope in assignments}
    click_properties = {"onclick", "click_modifiers", "ondefault", "onshift", "onctrl", "onalt"}
    for start, _, _, _ in handlers:
        scope = scope_by_start[start]
        if any(other_start != start and other_scope == scope and key in click_properties
               for other_start, _, key, _, other_scope in assignments):
            line = text.count("\n", 0, start) + 1
            raise ValueError(f"Conflicting click handlers in construction widget at line {line}")
    for start, end, replacement in reversed(replacements):
        text = text[:start] + replacement + text[end:]
    return text, len(replacements)


def _validate_static_payload() -> None:
    define_file = STATIC_MOD_DIR / "common/defines/zzz_priority_batch_defines.txt"
    metadata_file = STATIC_MOD_DIR / ".metadata/metadata.json"
    if not define_file.is_file() or not metadata_file.is_file():
        raise FileNotFoundError("Static mod payload is incomplete")
    defines = define_file.read_text(encoding="utf-8")
    if "NCountry = {" not in defines or "NGame = {" in defines:
        raise ValueError("Construction queue define overrides must be under NCountry")
    if "CONSTRUCTION_QUEUE_INCREMENT_SHIFT = 1" not in defines:
        raise ValueError("Shift construction define override missing")
    if "CONSTRUCTION_QUEUE_INCREMENT_CONTROL = 1" not in defines:
        raise ValueError("Control construction define override missing")
    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    if not str(metadata.get("supported_game_version", "")).startswith("1.14"):
        raise ValueError("Metadata is not targeted at Victoria 3 1.14")


def _discover_sources(game_dir: Path) -> dict[str, str]:
    required = game_dir / REQUIRED_QUEUE_TEMPLATE
    if not required.is_file():
        raise FileNotFoundError(f"Missing Victoria 3 GUI file: {REQUIRED_QUEUE_TEMPLATE}")
    sources = {}
    for source in sorted((game_dir / "game/gui").rglob("*.gui")):
        text = source.read_text(encoding="utf-8-sig")
        if _target_handlers(text):
            sources[source.relative_to(game_dir).as_posix()] = text
    if REQUIRED_QUEUE_TEMPLATE not in sources or not any(
        action == "QueueConstruction"
        for _, _, _, action in _target_handlers(sources[REQUIRED_QUEUE_TEMPLATE])
    ):
        raise ValueError(f"No Building.QueueConstruction handler in {REQUIRED_QUEUE_TEMPLATE}")
    return sources


def _validate_output(game_dir: Path, output_dir: Path) -> None:
    for source in (game_dir, ROOT.resolve()):
        if output_dir == source or output_dir in source.parents or source in output_dir.parents:
            raise ValueError(f"Output must not overlap game or builder sources: {source}")


def _configure_probe_metadata(stage: Path) -> None:
    metadata_file = stage / ".metadata/metadata.json"
    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    metadata["name"] = "Priority Batch Construction — Modifier Probe"
    metadata["version"] = f"{metadata.get('version', '0.1.0')}-probe"
    metadata["short_description"] = (
        "Diagnostic build that uses distinct queue counts to identify Jomini combined-modifier dispatch."
    )
    metadata_file.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _validate_generated(stage: Path, report: dict, sources: dict[str, str]) -> None:
    if set(report["patched_files"]) != set(sources):
        raise ValueError("Not all discovered construction GUI files were patched")
    for rel in sources:
        out = stage / rel.replace("game/", "", 1)
        text = out.read_text(encoding="utf-8-sig")
        if "# PRIORITY_BATCH_BEGIN" not in text:
            raise ValueError(f"Generated file was not patched: {rel}")
        if any(key == "onclick" for _, _, key, _ in _target_handlers(text)):
            raise ValueError(f"Vanilla construction onclick remains in generated file: {rel}")
    metadata = json.loads((stage / ".metadata/metadata.json").read_text(encoding="utf-8"))
    if report["mode"] == "probe" and "Modifier Probe" not in metadata.get("name", ""):
        raise ValueError("Probe build metadata was not marked as a diagnostic build")
    _validate_static_payload()


def build_mod(game_dir: Path | str, output_dir: Path | str, probe: bool = False) -> dict:
    """Build a mod from local vanilla files, replacing destination only after validation."""
    game_dir = Path(game_dir).resolve()
    output_dir = Path(output_dir).resolve()
    _validate_output(game_dir, output_dir)
    _validate_static_payload()
    sources = _discover_sources(game_dir)
    patched_sources = {}
    for rel, original in sources.items():
        try:
            patched_sources[rel] = patch_gui_text(original, probe=probe)
        except ValueError as error:
            raise ValueError(f"{rel}: {error}") from error

    output_parent = output_dir.parent
    output_parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=output_dir.name + ".staging-", dir=output_parent))
    report = {
        "mode": "probe" if probe else "standard",
        "patched_files": [],
        "replacement_counts": {},
    }
    try:
        shutil.copytree(STATIC_MOD_DIR, stage, dirs_exist_ok=True)
        if probe:
            _configure_probe_metadata(stage)
        for rel, (patched, count) in patched_sources.items():
            target = stage / rel.replace("game/", "", 1)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(patched, encoding="utf-8-sig", newline="")
            report["patched_files"].append(rel)
            report["replacement_counts"][rel] = count

        _validate_generated(stage, report, sources)

        backup = None
        if output_dir.exists():
            # Never delete a pre-existing sibling directory owned by the user.
            backup = Path(tempfile.mkdtemp(prefix=output_dir.name + ".backup-", dir=output_parent))
            backup.rmdir()
            output_dir.rename(backup)
        try:
            stage.rename(output_dir)
        except Exception:
            if backup is not None and backup.exists() and not output_dir.exists():
                backup.rename(output_dir)
            raise
        if backup is not None and backup.exists():
            shutil.rmtree(backup)
        return report
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)


def _default_output(probe: bool = False) -> Path:
    mod_name = "Vic3PriorityBatchProbe" if probe else "Vic3PriorityBatch"
    return Path.home() / "Documents" / "Paradox Interactive" / "Victoria 3" / "mod" / mod_name


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Priority Batch Construction for Victoria 3 1.14.x")
    parser.add_argument("--game-dir", required=True, type=Path, help="Victoria 3 installation directory")
    parser.add_argument("--output", type=Path, default=None, help="Generated mod directory")
    parser.add_argument(
        "--probe",
        action="store_true",
        help="Generate the distinct-count modifier-dispatch diagnostic build",
    )
    args = parser.parse_args()
    output = args.output or _default_output(args.probe)
    print(COMPATIBILITY_WARNING)
    report = build_mod(args.game_dir, output, probe=args.probe)
    label = "Modifier Probe" if args.probe else "Priority Batch Construction"
    print(f"Built {label} at: {output}")
    for rel in report["patched_files"]:
        print(f"  patched {rel}: {report['replacement_counts'][rel]} action(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
