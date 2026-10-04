# Priority Batch Construction — Victoria 3 1.14.x

Adds an experimental pure-mod path for batch **highest-priority** construction:

- Normal click → 1 construction
- Shift+click → 5 constructions
- Ctrl+click → 10 constructions
- Alt+click → 1 construction at highest priority
- Shift+Alt+click → intended: 5 constructions at highest priority
- Ctrl+Alt+click → intended: 10 constructions at highest priority
- Existing cancellation batching is preserved: Shift+cancel = 5, Ctrl+cancel = 10

## Why this package builds from your local game files

Victoria 3's construction buttons live in vanilla `.gui` files. Instead of bundling complete copies of Paradox's GUI files, this package scans `game/gui/**/*.gui` from your own installed **1.14.x** game and writes patched copies of files containing `Building.QueueConstruction` or `Building.CancelConstruction` handlers into a local mod folder. Shared button definitions are patched at their definition; panels that use those definitions do not need duplicate overrides.

The initial reference was a 1.14.5-openbeta extract. Version 0.1.1 also incorporates the supplied five-file `vic3_gui.zip`, whose exact game version is unknown. That archive has queue handlers in a shared button definition and a separate cancellation-only panel. See [the GUI audit](docs/gui-audit-2026-10-04.md) for the comparison and verification evidence.

The builder requires a `game/gui` tree with at least one building queue handler; no particular GUI filename is mandatory. It processes cancellation-only files, discovers additional call sites, and rejects unsupported target handlers or conflicting click/modifier properties in the same widget before replacing an existing mod. A successful build verifies the supported GUI transformation, not the game version, input dispatch, or completeness of a partial GUI extract. Always build an installed mod from the full game installation. Do not use outside 1.14.x merely because GUI structure matches.

## Install on Windows

1. Extract this package anywhere.
2. Open PowerShell in the extracted folder.
3. Run:

   `powershell -ExecutionPolicy Bypass -File .\tools\install.ps1`

   If Victoria 3 is not auto-detected:

   `powershell -ExecutionPolicy Bypass -File .\tools\install.ps1 -GameDir "K:\SteamLibrary\steamapps\common\Victoria 3"`

4. The generated mod is placed in `Documents\Paradox Interactive\Victoria 3\mod\Vic3PriorityBatch` by default.
5. Enable **Priority Batch Construction** in the Paradox Launcher.
6. Follow `docs/runtime-verification.md`.

The installer tries runnable Python 3.10+ interpreters in order (`py -3`, `python`, `python3`). A stale `py` registration is skipped. To select a known working interpreter, add `-PythonExe "X:\path\python.exe"`. Auto-detection checks Steam's configured libraries and conventional `<drive>:\SteamLibrary` paths using the GUI directory and launcher settings, without requiring `building_details_panel.gui`.

If using a supplied **mod-only ZIP**, extract its `Vic3PriorityBatch` folder directly into `Documents\Paradox Interactive\Victoria 3\mod`, then enable it in the launcher. No Python or installer execution is needed. Such a ZIP contains generated overrides for the particular game build used to create it; regenerate after a game update. The separate probe ZIP contains `Vic3PriorityBatchProbe`; enable only one build at a time.

You can also run the builder directly:

`py -3 .\tools\build_mod.py --game-dir "...\Victoria 3" --output "...\Victoria 3\mod\Vic3PriorityBatch"`

## Important runtime limitation

Jomini exposes `onshift`, `onctrl`, and `onalt`, but no documented `onshiftalt` / `onctrlalt`. The pure mod therefore relies on combined clicks being dispatched to the Shift/Ctrl handler while Alt remains physically held. That dispatch priority cannot be verified without launching Victoria 3.

To determine the dispatcher behavior directly, generate the diagnostic build with:

`powershell -ExecutionPolicy Bypass -File .\tools\install.ps1 -Probe`

Enable only **Priority Batch Construction — Modifier Probe** and follow `docs/modifier-dispatch-probe.md`. The probe maps `ondefault/onshift/onctrl/onalt` to 1/2/3/4 new entries so combined-key routing can be identified from the queue count.

If Shift+Alt or Ctrl+Alt resolves to `onalt`, use the included `tools/Vic3PriorityBatch.ahk` with **AutoHotkey v2**. The helper is restricted to `victoria3.exe` and repeats the native Alt-priority click 5 or 10 times.

The helper retains the held modifiers. Before relying on it, verify that one native combined click creates exactly one entry with the pure mod and probe disabled, then verify that the helper creates exactly 5/10 entries at the front. Do not assume the engine's internal batching behavior from GUI dispatch alone.

Do **not** run the AutoHotkey fallback at the same time as a pure-mod implementation that already works for the combined keys, or one physical click may be multiplied twice.

## Compatibility

The override list is discovered at build time and printed by the builder. In the supplied archive, only these two files need overrides:

- `gui/states_panel_buildings.gui`
- `gui/building_details_panel.gui`

The original six-file layout is still supported when those handlers are present. Files without target handlers, including the supplied construction queue, ship construction panel and building browser, are not copied. `ConstructionQueueElement` reordering/cancellation and `Building.QueueMilitaryConstruction` are not rewritten. Their runtime behavior under the shared define overrides must be checked in-game.

Version 0.1.2 was additionally generated against the user's full installed Victoria 3 1.14.5 (Steam `1.14-openbeta`, build 25629520). That installation has no `building_details_panel.gui`; it has 15 target sites across seven files. See [the installer fix and installed-game audit](docs/installer-fix-2026-10-04.md) for the exact override list.

UI mods that replace any discovered file can conflict by load order. Regenerate after Victoria 3 updates within 1.14.x. The output directory must not overlap the game installation or builder package; the builder replaces that directory after staging and validation. Existing unrelated `.previous` directories are preserved, and a failed publish restores the existing mod.

## Developer verification

Run `python -m unittest discover -s tests -v` and `python -m py_compile tools/build_mod.py tests/test_build_mod.py`. Tests cover discovery, cancellation-only files, unsupported-handler rejection, unrelated controls, output safety, rollback and normal/probe batching. In-game verification remains separate.
