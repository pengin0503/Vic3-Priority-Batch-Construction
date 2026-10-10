# Priority Batch Construction — Victoria 3 1.14.x

Adds an experimental pure-mod path for batch **highest-priority** construction:

- Normal click → 1 construction
- Shift+click → 5 constructions
- Ctrl+click → 10 constructions
- Alt+click → 1 construction at highest priority
- Shift+Alt+click → 5 constructions at highest priority (via the AutoHotkey helper, which only repeats vanilla Alt+click; the pure-mod result depends on unverified dispatch)
- Ctrl+Alt+click → 10 constructions at highest priority (same as above)
- Existing cancellation batching is preserved: Shift+cancel = 5, Ctrl+cancel = 10

## Why this package builds from your local game files

Victoria 3's construction buttons live in vanilla `.gui` files. Instead of bundling complete copies of Paradox's GUI files, this package scans `game/gui/**/*.gui` from your own installed **1.14.x** game and writes patched copies of files containing `Building.QueueConstruction` or `Building.CancelConstruction` handlers into a local mod folder. Shared button definitions are patched at their definition; panels that use those definitions do not need duplicate overrides.

The initial reference was a 1.14.5-openbeta extract. Version 0.1.1 also incorporates the supplied five-file `vic3_gui.zip`, whose exact game version is unknown. That archive has queue handlers in a shared button definition and a separate cancellation-only panel. See [the GUI audit](docs/gui-audit-2026-10-04.md) for the comparison and verification evidence.

The builder requires a `game/gui` tree with at least one building queue handler. When those files use `expand_building_button`, its shared definition must also be present in the game or supplied overlays. It processes cancellation-only files, discovers additional call sites, and rejects unsupported target handlers or conflicting click/modifier properties in the same widget before replacing an existing mod. A successful build verifies the supported GUI transformation, not the game version, input dispatch, or completeness of a partial GUI extract. Always build an installed mod from the full game installation. Do not use outside 1.14.x merely because GUI structure matches.

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

GUI script cannot read the keyboard state directly. The data-type dump shipped in Paradox's script docs (mirrored in `cwtools/cwtools-vic3-config/script-docs`) has no Shift/Ctrl/Alt state function; `click_modifiers` (`ondefault`/`onshift`/`onctrl`/`onalt`) is the only modifier hook, and there is no `onshiftalt` / `onctrlalt`. The pure mod therefore works for Shift+Alt / Ctrl+Alt only if Jomini dispatches those clicks to `onshift` / `onctrl`. If it dispatches them to `onalt` or `ondefault`, no GUI file can distinguish them from Alt+click or a normal click. That dispatch cannot be verified without launching Victoria 3.

To determine the dispatcher behavior directly, generate the diagnostic build with:

`powershell -ExecutionPolicy Bypass -File .\tools\install.ps1 -Probe`

Enable only **Priority Batch Construction — Modifier Probe** and follow `docs/modifier-dispatch-probe.md`. The probe maps `ondefault/onshift/onctrl/onalt` to 1/2/3/4 new entries so combined-key routing can be identified from the queue count.

## Shift+Alt / Ctrl+Alt helper (AutoHotkey v2)

`tools/Vic3PriorityBatch.ahk` does not depend on that dispatch. While `victoria3.exe` is the active window, it consumes a Shift+Alt+click or Ctrl+Alt+click, logically releases Shift/Ctrl (Alt stays held), and sends 5 or 10 plain **Alt+clicks** at the cursor. Each one is vanilla Alt+click behavior: one level at the front of the construction queue. It therefore does not depend on this mod, works the same with UI mods such as GORA UI+, and needs no regeneration after game updates. It has not been run in-game here; check it with `docs/runtime-verification.md`.

1. Install [AutoHotkey v2](https://www.autohotkey.com/).
2. Double-click `tools/Vic3PriorityBatch.ahk` (an "H" icon appears in the system tray).
3. In the game, hover a building's construction (+) button and Shift+Alt+click (5) or Ctrl+Alt+click (10).

Normal, Shift, Ctrl and Alt clicks are not touched by the helper. With this mod disabled they keep vanilla behavior (1/5/10/1 at the front). Because the original combined click never reaches the game, it cannot be multiplied by the mod. If fewer entries than expected appear, raise `ClickDelayMs` at the top of the script. Versions before 0.1.4 defined the hotkey as `$LButton::`, which AutoHotkey does not fire while Shift, Ctrl or Alt is held, so that helper never triggered.

On Windows with the Alt+Shift input-language shortcut enabled, pressing Shift+Alt may also switch the keyboard layout; this is independent of the helper.

## Compatibility

The override list is discovered at build time and printed by the builder. In the supplied archive, only these two files need overrides:

- `gui/states_panel_buildings.gui`
- `gui/building_details_panel.gui`

The original six-file layout is still supported when those handlers are present. Files without target handlers, including the supplied construction queue, ship construction panel and building browser, are not copied. `ConstructionQueueElement` reordering/cancellation and `Building.QueueMilitaryConstruction` are not rewritten. Their runtime behavior under the shared define overrides must be checked in-game.

Version 0.1.2 was additionally generated against the user's full installed Victoria 3 1.14.5 (Steam `1.14-openbeta`, build 25629520). That installation has no `building_details_panel.gui`; it has 15 target sites across seven files. See [the installer fix and installed-game audit](docs/installer-fix-2026-10-04.md) for the exact override list.

UI mods that replace any discovered file can conflict by load order. Regenerate after Victoria 3 updates within 1.14.x. The output directory must not overlap the game installation or builder package; the builder replaces that directory after staging and validation. Existing unrelated `.previous` directories are preserved, and a failed publish restores the existing mod.

### GORA UI+ and matching recovery sources (0.1.3)

The builder can read additional GUI directories in load order. Later directories replace earlier files with the same relative path; only files with supported building construction/cancellation handlers are emitted. This is a construction compatibility patch, not a complete copy of the UI mod. Keep the original UI mod enabled and load the generated patch after it.

For the inspected installation, `building_details_panel.gui` is missing although multiple vanilla panels use its shared types. The user's `vic3_gui.zip` supplies that definition; its other four files exactly match the installed game. Read that recovery directory first, then GORA's GUI directory:

```powershell
& .\tools\install.ps1 -GameDir "D:\SteamLibrary\steamapps\common\Victoria 3" -GuiOverlay @("X:\extracted\vic3_gui", "D:\SteamLibrary\steamapps\workshop\content\529340\3724865565\gui")
```

Run this in the current PowerShell session with script execution allowed. The Python CLI accepts repeated `--gui-overlay "directory"` arguments. Sources are read only, and output must not overlap any source directory. Recovery files must match your installed game; arbitrary old GUI definitions are unsafe.

The supplied 0.1.3 GORA-compatible mod-only ZIP contains ten GUI overrides covering 23 action sites, including GORA's overview and expanded building grid. Disable older standard/probe builds, enable GORA UI+ and **Priority Batch Construction — GORA UI+ Compatibility**, and load this patch after GORA. Normal Shift/Ctrl handlers contain 5/10 actions; the separate GORA probe deliberately uses 2/3, and is for diagnostics only. See [the compatibility investigation](docs/gora-compatibility-2026-10-04.md). Runtime behavior remains to be verified in Victoria 3.

## Developer verification

Run `python -m unittest discover -s tests -v` and `python -m py_compile tools/build_mod.py tests/test_build_mod.py`. Tests cover discovery, cancellation-only files, unsupported-handler rejection, unrelated controls, output safety, rollback and normal/probe batching. In-game verification remains separate.
