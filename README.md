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

Victoria 3's construction buttons live in vanilla `.gui` files. Instead of bundling complete copies of Paradox's GUI files, this package patches the six relevant files from your own installed **1.14.x** game and writes the patched copies into a local mod folder.

The 1.14.5-openbeta vanilla extract was used as the reference. The builder fails rather than creating a partial mod if a required file or `Building.QueueConstruction` action is missing. The builder also prints an explicit warning that the installed game version is not auto-detected, so do not use it outside 1.14.x merely because the GUI structure happens to match.

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

You can also run the builder directly:

`py -3 .\tools\build_mod.py --game-dir "...\Victoria 3" --output "...\Victoria 3\mod\Vic3PriorityBatch"`

## Important runtime limitation

Jomini exposes `onshift`, `onctrl`, and `onalt`, but no documented `onshiftalt` / `onctrlalt`. The pure mod therefore relies on combined clicks being dispatched to the Shift/Ctrl handler while Alt remains physically held. That dispatch priority cannot be verified without launching Victoria 3.

If Shift+Alt or Ctrl+Alt still creates only one highest-priority entry, use the included `tools/Vic3PriorityBatch.ahk` with **AutoHotkey v2**. The helper is restricted to `victoria3.exe` and repeats the native Alt-priority click 5 or 10 times.

Do **not** run the AutoHotkey fallback at the same time as a pure-mod implementation that already works for the combined keys, or one physical click may be multiplied twice.

## Compatibility

The generated mod overrides these six 1.14.5 GUI files:

- `gui/build_urban_buildings_menu.gui`
- `gui/states_panel.gui`
- `gui/states_panel_buildings.gui`
- `gui/right_click_menu.gui`
- `gui/production_methods.gui`
- `gui/building_details_panel.gui`

UI mods that replace the same files can conflict by load order. Regenerate the mod after Victoria 3 updates within 1.14.x so the patched copies are based on your current local files.
