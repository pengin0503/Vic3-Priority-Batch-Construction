# Priority Batch Construction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Victoria 3 1.14.x mod generator that preserves vanilla construction controls and adds 5/10 repeated priority construction paths.

**Architecture:** A standard-library Python builder patches the six 1.14.5 GUI files from the local game install into a generated mod, writes a define override and metadata, and validates before replacing the destination. A PowerShell launcher and AutoHotkey fallback make the package practical on Windows.

**Tech Stack:** Python 3 standard library, Victoria 3 Jomini GUI, Paradox mod metadata, PowerShell 5+, AutoHotkey v2 fallback.

**Spec:** `docs/superpowers/specs/2026-10-04-priority-batch-construction-design.md`

## Global Constraints
- Target Victoria 3 1.14.x; reference source is 1.14.5-openbeta.
- Default=1, Shift=5, Ctrl=10, Alt=1 priority must remain.
- Construction cancellation batching must remain normal/Alt=1, Shift=5, Ctrl=10.
- Patch all six known 1.14.5 `Building.QueueConstruction` GUI call sites.
- Fail closed; no partial destination on validation failure.
- Do not bundle full vanilla GUI files in source.

## Review Focus
- A target GUI file renamed or its action changed: builder must stop, not silently make a partial mod.
- Multiple queue action occurrences in one target: every occurrence must be patched.
- Existing destination: replacement must occur only after staged build validates.
- Non-1.14 install: metadata/version warning must be explicit.
- Combined Shift+Alt/Ctrl+Alt dispatch may resolve to Alt: fallback helper and runtime checklist must be included.

### Task 1: Patch engine and validation
**Files:** Create `tools/build_mod.py`; Test `tests/test_build_mod.py`.
**Interfaces:** Produces `patch_gui_text(text)`, `build_mod(game_dir, output_dir)`, `TARGET_GUI_FILES`.
- [x] Write failing tests for targets, 1/5/10/1 handler counts, preservation, missing action failure, staging validation.
- [x] Run tests and observe failure.
- [x] Implement minimal patch/build logic.
- [x] Run tests green.

### Task 2: Mod payload and Windows helpers
**Files:** Create `mod/common/defines/zzz_priority_batch_defines.txt`, `mod/.metadata/metadata.json`, `tools/install.ps1`, `tools/Vic3PriorityBatch.ahk`, `README.md`, `docs/runtime-verification.md`; extend tests.
**Interfaces:** Builder copies `mod/` static payload and patched GUI files.
- [x] Add failing package-content tests.
- [x] Run tests and observe failure.
- [x] Add payload/helpers/docs.
- [x] Run full tests green.

### Task 3: Package verification
**Files:** Create release ZIP.
- [x] Run full test suite.
- [x] Run builder against a synthetic 1.14.5 fixture and inspect generated tree.
- [x] Zip source package and verify archive entries.

### Task 4: Modifier-dispatch probe
**Files:** Modify `tools/build_mod.py`, `tools/install.ps1`, `README.md`; create `docs/modifier-dispatch-probe.md`; extend `tests/test_build_mod.py`.
**Interfaces:** `patch_gui_text(text, probe=False)` and `build_mod(game_dir, output_dir, probe=False)` preserve standard mode; probe mode uses queue handler signatures default=1, Shift=2, Ctrl=3, Alt=4 and a separate generated mod identity/output.
- [x] Add failing tests for probe handler counts, isolated metadata/output, installer switch, and result-decoding docs.
- [x] Run tests and observe the missing probe interfaces.
- [x] Implement `--probe` / `-Probe` and diagnostic metadata/docs without changing standard mode.
- [x] Run full tests green.
