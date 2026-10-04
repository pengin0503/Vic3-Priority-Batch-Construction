# Modifier dispatch probe — Victoria 3 1.14.x

This diagnostic build determines which Jomini `click_modifiers` handler receives a combined modifier click. It does **not** use the normal 5/10 production counts.

## Build and enable the probe

1. Disable **Priority Batch Construction** if it is enabled.
2. From the repository root, run:
   `powershell -ExecutionPolicy Bypass -File .\tools\install.ps1 -Probe`
3. In the Paradox Launcher, enable **Priority Batch Construction — Modifier Probe** and keep the normal mod disabled.
4. Load a disposable save, pause the game, and choose a building that can accept at least 10 more levels.

The probe deliberately maps handlers to distinct counts:

| Handler | Probe signature |
|---|---:|
| `ondefault` | 1 new entry |
| `onshift` | 2 new entries |
| `onctrl` | 3 new entries |
| `onalt` | 4 new entries |

First verify the four single-modifier signatures: normal click = 1, Shift+click = 2, Ctrl+click = 3, Alt+click = 4. If those do not match, stop and capture `error.log` / `gui.log` before testing combined keys.

## Decode Shift+Alt

Click once with **Shift+Alt** held and count only the newly-added construction entries:

- **2 new entries** → Jomini dispatched the click to `onshift`. This is the result needed by the normal pure-mod strategy.
- **4 new entries** → Jomini dispatched the click to `onalt`. The normal pure-mod strategy cannot create five entries from that combined click without another mechanism.
- **6 new entries** → both `onshift` and `onalt` effectively fired; this is unexpected and needs a revised implementation.
- Any other count → record the exact count and queue ordering; treat it as an unknown dispatch path.

Also note whether the new entries appear at the front of the construction queue. That separately tells us whether `Building.QueueConstruction` still observes Alt while an `onshift` handler is executing.

## Decode Ctrl+Alt

Click once with **Ctrl+Alt** held:

- **3 new entries** → Jomini dispatched the click to `onctrl`. This is the result needed by the normal pure-mod strategy.
- **4 new entries** → Jomini dispatched the click to `onalt`.
- **7 new entries** → both `onctrl` and `onalt` effectively fired; unexpected.
- Any other count → record the exact count and queue ordering.

## What to report back

For each of Shift+Alt and Ctrl+Alt, report:

1. Number of new entries.
2. Whether all new entries appeared at the queue front.
3. Which UI entry point you clicked (Production Methods/Buildings, building details, state panel, etc.).
4. Any parse/property errors in `Documents\Paradox Interactive\Victoria 3\logs\error.log` or `gui.log`.

After the test, disable the probe. Do not enable the probe and normal mod at the same time because both replace the same six GUI files.
