# Runtime verification — Victoria 3 1.14.x

Run this on a disposable save with enough construction capacity and a building that can accept at least 10 additional levels. Pause the game before each check and note the government construction queue size/order.

## Required checks

| Input | Expected result |
|---|---|
| Normal click | exactly 1 new construction, normal queue position |
| Shift+click | exactly 5 new constructions, normal queue position |
| Ctrl+click | exactly 10 new constructions, normal queue position |
| Alt+click | exactly 1 new construction at highest priority / front |
| Shift+Alt+click | exactly 5 new constructions, all placed at highest priority / front |
| Ctrl+Alt+click | exactly 10 new constructions, all placed at highest priority / front |

Repeat the six construction checks from at least two UI entry points, including building details and the state panel (which uses the shared `expand_building_button` definition). Check Buildings/Production Methods and the foreign-investment entry when available. Use the builder's printed file list when investigating UI mod conflicts.

Then queue at least 10 levels on one building and verify cancellation batching: Shift+click the cancel/minus control removes exactly 5 queued levels, and Ctrl+click removes exactly 10. Normal and Alt cancellation must still remove one.

## Boundary checks

1. Test a building with fewer than 5 levels left before its cap. It must not create invalid extra levels.
2. Test a building with fewer than 10 levels left before its cap.
3. Test a building that already has queued construction.
4. Confirm normal/Alt cancellation removes one queued level, Shift cancellation removes 5, and Ctrl cancellation removes 10.
5. Confirm building Downsize and construction-queue reordering/cancellation still work normally. These controls are not rewritten.
6. Check ordinary Shift/Ctrl military-building construction and ship construction against vanilla. `Building.QueueMilitaryConstruction`, `ShipConstruction` and `ConstructionQueueElement` are not rewritten, but the engine's use of the shared construction increment defines is not established by static GUI inspection. If those controls regress, disable the mod and report the entry point and observed count.
7. Exit to desktop and inspect `Documents\Paradox Interactive\Victoria 3\logs\error.log` and `gui.log` for parse/property errors mentioning any of the discovered patched GUI files.

## If combined modifiers still add only one

Use the modifier probe to distinguish Alt or default dispatch from other causes such as caps or failed repeated actions; a one-entry result by itself is not proof of which handler fired. Whatever the probe shows, the AutoHotkey v2 helper `tools/Vic3PriorityBatch.ahk` does not depend on combined-key dispatch: it replaces Shift+Alt+click / Ctrl+Alt+click with 5/10 plain Alt+clicks at the cursor. Verify on a disposable save, with the probe disabled:

1. Alt+click alone (helper running) still adds exactly 1 entry at the front.
2. Shift+Alt+click adds exactly 5 entries at the front; Ctrl+Alt+click adds exactly 10.
3. Normal, Shift and Ctrl clicks are unchanged (1/5/10).
4. If fewer entries appear, raise `ClickDelayMs` in the script and retest.

Record which of the six input cases failed and from which UI entry point; that is enough to revise the pure GUI strategy without guessing.
