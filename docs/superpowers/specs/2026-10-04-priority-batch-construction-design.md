# Priority Batch Construction Design

Historical initial design. The fixed six-file inventory and per-file queue requirement below are superseded in v0.1.1 by [the supplied GUI audit](../../gui-audit-2026-10-04.md). The combined-key runtime assumptions remain unverified.

## Goal
For Victoria 3 1.14.x, preserve vanilla construction clicks while adding a path for Shift+Alt+click to create 5 highest-priority building construction entries and Ctrl+Alt+click to create 10 highest-priority entries.

## Constraints
- Target reference: Victoria 3 1.14.5-openbeta vanilla extract.
- Preserve default click = 1, Shift = 5, Ctrl = 10, Alt = 1 highest priority.
- Preserve construction cancellation batching: normal/Alt = 1, Shift = 5, Ctrl = 10.
- Do not ship full vanilla GUI files in source. Build patched copies from the user's installed 1.14.x game files.
- Patch every 1.14.5 GUI call site of `Building.QueueConstruction` identified in the vanilla extract.
- Fail closed if required source files or queue-construction call sites are missing.
- Generate the mod in a staging directory and replace the destination only after validation succeeds.
- Keep a Windows helper fallback for exact combined-key repetition if the Jomini modifier dispatcher resolves combined modifiers to Alt rather than Shift/Ctrl.

## Architecture
The pure-mod path changes the building queue Shift/Ctrl increments to 1, then replaces each GUI queue/cancel `onclick` with `click_modifiers`. QueueConstruction uses 1/5/10/1 calls for default/Shift/Ctrl/Alt; CancelConstruction uses the same counts so lowering the global increments does not regress vanilla batch cancellation. The Shift queue handler invokes `Building.QueueConstruction` five times and the Ctrl handler ten times; default and Alt invoke it once. If Jomini routes Shift+Alt to the Shift handler (and Ctrl+Alt to Ctrl), each invocation still sees Alt held and therefore creates a highest-priority single entry, yielding 5/10 prioritized entries.

Because combined-modifier dispatch priority is not publicly documented and cannot be runtime-tested here, the builder also supports a diagnostic probe mode. Probe mode maps default/Shift/Ctrl/Alt queue handlers to 1/2/3/4 calls and uses separate metadata/output so the runtime result identifies which Jomini handler received Shift+Alt or Ctrl+Alt. A Windows AutoHotkey v2 helper remains the fallback when combined clicks resolve through Alt.

## 1.14.5 GUI targets
- `game/gui/build_urban_buildings_menu.gui`
- `game/gui/states_panel.gui`
- `game/gui/states_panel_buildings.gui`
- `game/gui/right_click_menu.gui`
- `game/gui/production_methods.gui`
- `game/gui/building_details_panel.gui`

## Verification
Static tests verify transformation counts, vanilla-preserving handlers, metadata, define overrides, fail-closed behavior, probe isolation/signatures, and package contents. Runtime verification with the probe remains required for combined-modifier dispatch in the game.
