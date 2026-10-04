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

_QUEUE_CLICK = re.compile(
    r'(?m)^(?P<indent>[ \t]*)onclick\s*=\s*"\[Execute\(\s*Building\.QueueConstruction\s*\)\]"[ \t]*$'
)
_CANCEL_CLICK = re.compile(
    r'(?m)^(?P<indent>[ \t]*)onclick\s*=\s*"\[Execute\(\s*Building\.CancelConstruction\s*\)\]"[ \t]*$'
)


def _handler_block(indent: str, action: str) -> str:
    inner = indent + "\t"
    lines = [
        indent + "# PRIORITY_BATCH_BEGIN",
        indent + "click_modifiers = {",
        inner + f'ondefault = "[Execute( Building.{action} )]"',
    ]
    lines.extend(inner + f'onshift = "[Execute( Building.{action} )]"' for _ in range(5))
    lines.extend(inner + f'onctrl = "[Execute( Building.{action} )]"' for _ in range(10))
    lines.append(inner + f'onalt = "[Execute( Building.{action} )]"')
    lines.extend([
        indent + "}",
        indent + "# PRIORITY_BATCH_END",
    ])
    return "\n".join(lines)


def patch_gui_text(text: str) -> tuple[str, int]:
    """Patch queue clicks and any co-located cancel clicks with modifier blocks."""
    patched, queue_count = _QUEUE_CLICK.subn(
        lambda m: _handler_block(m.group("indent"), "QueueConstruction"), text
    )
    if queue_count == 0:
        raise ValueError("No vanilla Building.QueueConstruction onclick found")
    patched, cancel_count = _CANCEL_CLICK.subn(
        lambda m: _handler_block(m.group("indent"), "CancelConstruction"), patched
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
    _validate_static_payload()


def build_mod(game_dir: Path | str, output_dir: Path | str) -> dict:
    """Build a mod from local vanilla files, replacing destination only after validation."""
    game_dir = Path(game_dir).resolve()
    output_dir = Path(output_dir).resolve()
    _validate_static_payload()
    _validate_sources(game_dir)

    output_parent = output_dir.parent
    output_parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=output_dir.name + ".staging-", dir=output_parent))
    report = {"patched_files": [], "replacement_counts": {}}
    try:
        shutil.copytree(STATIC_MOD_DIR, stage, dirs_exist_ok=True)
        for rel in TARGET_GUI_FILES:
            src = game_dir / rel
            original = src.read_text(encoding="utf-8-sig")
            patched, count = patch_gui_text(original)
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


def _default_output() -> Path:
    return Path.home() / "Documents" / "Paradox Interactive" / "Victoria 3" / "mod" / "Vic3PriorityBatch"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Priority Batch Construction for Victoria 3 1.14.x")
    parser.add_argument("--game-dir", required=True, type=Path, help="Victoria 3 installation directory")
    parser.add_argument("--output", type=Path, default=_default_output(), help="Generated mod directory")
    args = parser.parse_args()
    print(COMPATIBILITY_WARNING)
    report = build_mod(args.game_dir, args.output)
    print(f"Built Priority Batch Construction at: {args.output}")
    for rel in report["patched_files"]:
        print(f"  patched {rel}: {report['replacement_counts'][rel]} action(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
