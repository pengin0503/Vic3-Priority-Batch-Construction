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

Use the modifier probe to distinguish Alt dispatch from other causes such as caps or failed repeated actions; a one-entry result by itself is not proof of which handler fired. If the probe confirms Alt dispatch, disable both pure mod and probe before testing the fallback. Verify that one native combined click creates exactly one front entry, then install AutoHotkey v2 and run `tools/Vic3PriorityBatch.ahk`. The helper repeats the native combined click 5/10 times while the cursor remains over the construction button, with the original modifiers held. Verify the final counts/order on a disposable save before relying on it.

Record which of the six input cases failed and from which UI entry point; that is enough to revise the pure GUI strategy without guessing.
