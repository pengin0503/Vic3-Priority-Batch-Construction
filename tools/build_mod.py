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
    "Compatibility warning: this builder is validated only for Victoria 3 1.14.x; "
    "the installed game version is not auto-detected."
)

TARGET_GUI_FILES = (
    "game/gui/build_urban_buildings_menu.gui",
    "game/gui/states_panel.gui",
    "game/gui/states_panel_buildings.gui",
    "game/gui/right_click_menu.gui",
    "game/gui/production_methods.gui",
    "game/gui/building_details_panel.gui",
)

STANDARD_COUNTS = {"default": 1, "shift": 5, "ctrl": 10, "alt": 1}
PROBE_QUEUE_COUNTS = {"default": 1, "shift": 2, "ctrl": 3, "alt": 4}

_QUEUE_CLICK = re.compile(
    r'(?m)^(?P<indent>[ \t]*)onclick\s*=\s*"\[Execute\(\s*Building\.QueueConstruction\s*\)\]"[ \t]*$'
)
_CANCEL_CLICK = re.compile(
    r'(?m)^(?P<indent>[ \t]*)onclick\s*=\s*"\[Execute\(\s*Building\.CancelConstruction\s*\)\]"[ \t]*$'
)


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
    """Patch queue clicks and any co-located cancel clicks with modifier blocks."""
    queue_counts = PROBE_QUEUE_COUNTS if probe else STANDARD_COUNTS
    patched, queue_count = _QUEUE_CLICK.subn(
        lambda m: _handler_block(m.group("indent"), "QueueConstruction", queue_counts), text
    )
    if queue_count == 0:
        raise ValueError("No vanilla Building.QueueConstruction onclick found")
    patched, cancel_count = _CANCEL_CLICK.subn(
        lambda m: _handler_block(m.group("indent"), "CancelConstruction", STANDARD_COUNTS), patched
    )
    return patched, queue_count + cancel_count


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


def _validate_sources(game_dir: Path) -> None:
    missing = [rel for rel in TARGET_GUI_FILES if not (game_dir / rel).is_file()]
    if missing:
        raise FileNotFoundError("Missing Victoria 3 GUI files: " + ", ".join(missing))


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


def _validate_generated(stage: Path, report: dict) -> None:
    if set(report["patched_files"]) != set(TARGET_GUI_FILES):
        raise ValueError("Not all known 1.14.5 QueueConstruction GUI files were patched")
    for rel in TARGET_GUI_FILES:
        out = stage / rel.replace("game/", "", 1)
        text = out.read_text(encoding="utf-8-sig")
        if "# PRIORITY_BATCH_BEGIN" not in text:
            raise ValueError(f"Generated file was not patched: {rel}")
        if _QUEUE_CLICK.search(text):
            raise ValueError(f"Vanilla QueueConstruction onclick remains in generated file: {rel}")
        if _CANCEL_CLICK.search(text):
            raise ValueError(f"Vanilla CancelConstruction onclick remains in generated file: {rel}")
    metadata = json.loads((stage / ".metadata/metadata.json").read_text(encoding="utf-8"))
    if report["mode"] == "probe" and "Modifier Probe" not in metadata.get("name", ""):
        raise ValueError("Probe build metadata was not marked as a diagnostic build")
    _validate_static_payload()


def build_mod(game_dir: Path | str, output_dir: Path | str, probe: bool = False) -> dict:
    """Build a mod from local vanilla files, replacing destination only after validation."""
    game_dir = Path(game_dir).resolve()
    output_dir = Path(output_dir).resolve()
    _validate_static_payload()
    _validate_sources(game_dir)

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
        for rel in TARGET_GUI_FILES:
            src = game_dir / rel
            original = src.read_text(encoding="utf-8-sig")
            patched, count = patch_gui_text(original, probe=probe)
            target = stage / rel.replace("game/", "", 1)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(patched, encoding="utf-8-sig", newline="")
            report["patched_files"].append(rel)
            report["replacement_counts"][rel] = count

        _validate_generated(stage, report)

        backup = None
        if output_dir.exists():
            backup = output_parent / (output_dir.name + ".previous")
            if backup.exists():
                if backup.is_dir():
                    shutil.rmtree(backup)
                else:
                    backup.unlink()
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
