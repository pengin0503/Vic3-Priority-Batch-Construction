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

Repeat the six construction checks from at least two UI entry points, including the Buildings/Production Methods panel and a building details/state panel entry.

Then queue at least 10 levels on one building and verify cancellation batching: Shift+click the cancel/minus control removes exactly 5 queued levels, and Ctrl+click removes exactly 10. Normal and Alt cancellation must still remove one.

## Boundary checks

1. Test a building with fewer than 5 levels left before its cap. It must not create invalid extra levels.
2. Test a building with fewer than 10 levels left before its cap.
3. Test a building that already has queued construction.
4. Confirm normal/Alt cancellation removes one queued level, Shift cancellation removes 5, and Ctrl cancellation removes 10.
5. Confirm building Downsize and construction-queue reordering still work normally; Downsize is intentionally not patched.
6. Exit to desktop and inspect `Documents\Paradox Interactive\Victoria 3\logs\error.log` and `gui.log` for parse/property errors mentioning any of the six patched GUI files.

## If combined modifiers still add only one

That means the Jomini click dispatcher resolved the combined click through `onalt` rather than the Shift/Ctrl handler. Disable the pure mod before using the fallback if ordinary Shift/Ctrl behavior is affected, then install AutoHotkey v2 and run `tools/Vic3PriorityBatch.ahk` from this package. The helper repeats the game's native combined Alt click 5/10 times while the cursor remains over the clicked construction button.

Record which of the six input cases failed and from which UI entry point; that is enough to revise the pure GUI strategy without guessing.
