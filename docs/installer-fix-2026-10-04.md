# v0.1.2 installer fix and installed-game audit

## Diagnosed failures

The user's installer first reported that the game was not found, then (with `-GameDir` supplied) failed with Python launcher exit code 101. Its registered `Python313/python.exe` does not exist. The installer previously selected `py` solely because the command existed, without checking whether it could start an interpreter.

Read-only inspection of the specified full installation confirmed `launcher/launcher-settings.json` reports `rawVersion: 1.14.5`; the Steam manifest reports `1.14-openbeta`, build 25629520. Its `game/gui` tree has no `building_details_panel.gui`. Both auto-detection and the v0.1.1 builder incorrectly required that filename. The supplied five-file GUI archive and the user's installed tree have different layouts, so the archive's shared-template structure must not be assumed for the installed tree.

## Fixes

- Discover queue/cancel handlers in `game/gui` without requiring an individual GUI filename. Reject a missing GUI directory or a tree with no building queue handler, retaining fail-closed validation of unsupported/conflicting handlers.
- Detect Steam installations through their GUI directory and launcher settings. Check configured Steam libraries and conventional `SteamLibrary` paths on mounted filesystem drives.
- Probe interpreters by actually running Python code and require Python 3.10+. Skip a broken `py -3` and try `python`/`python3`; allow explicit `-PythonExe` selection. If none is runnable, report that clearly before building.
- Offer generated mod-only ZIPs so the user can install by extracting the mod folder, without Python or scripts. Generated vanilla GUI copies are not committed to GitHub.

## Actual installed-game override inventory

Both normal and probe builds converted exactly 15 target sites:

| GUI file | Sites |
|---|---:|
| `build_urban_buildings_menu.gui` | 1 |
| `goods_local_prices_panel.gui` | 1 |
| `goods_state_panel.gui` | 1 |
| `right_click_menu.gui` | 3 |
| `states_panel.gui` | 7 |
| `states_panel_buildings.gui` | 1 |
| `strait_panel.gui` | 1 |

## Validation

Regression tests reproduced the missing-filename rejection, broken-launcher exit 101, and failed auto-detection before the fixes. Final suite: 29 tests passed on Windows, including two PowerShell integration tests that execute the installer with controlled Steam-library and interpreter inputs. Existing normal/probe batching, handler conflict rejection, output safety and rollback checks remain covered.

Both variants were built from the complete installed GUI tree using the bundled interpreter available to Codex. Packaging verification passed for the generated block counts, literal modifier action counts, metadata identity/version and all nine files in each ZIP. The 203 source GUI files were verified byte-for-byte unchanged. The repaired installer also auto-detected the actual D-drive installation and generated the same normal mod using explicit `-PythonExe`. Independent review confirmed the build output and test suite. These are build/install checks; combined-modifier dispatch and engine behavior remain subject to [in-game verification](runtime-verification.md).

## Install the mod-only ZIP

Extract `Vic3PriorityBatch` into `Documents\Paradox Interactive\Victoria 3\mod`, preserving `.metadata`, `common` and `gui`. Enable **Priority Batch Construction** in the Paradox Launcher. For the diagnostic variant, extract `Vic3PriorityBatchProbe` to the same `mod` parent and enable only **Priority Batch Construction — Modifier Probe**. Replacing an older generated mod folder avoids stale overrides from a different GUI layout.

Do not enable both variants at once. No installer or Python command is needed for the generated ZIPs. Regenerate after updating the game.
