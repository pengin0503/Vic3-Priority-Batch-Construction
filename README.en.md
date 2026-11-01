# Priority Batch Construction

[日本語](README.md) | **English**

An experimental Victoria 3 1.14.x mod for adding construction batches at highest priority.

## Controls

| Input | Constructions |
|---|---|
| Click | 1 |
| Shift + click | 5 |
| Ctrl + click | 10 |
| Alt + click | 1 at highest priority |
| Shift + Alt + click | Intended: 5 at highest priority |
| Ctrl + Alt + click | Intended: 10 at highest priority |

Shift and Ctrl cancellation batches of 5 and 10 are preserved. **Combined-key behavior has not been verified in-game.**

## Install on Windows

Python 3.10 or later and a complete Victoria 3 1.14.x installation are required. Extract the package, open PowerShell in its folder and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\install.ps1
```

If the game is not detected, add `-GameDir "K:\SteamLibrary\steamapps\common\Victoria 3"` with your actual path. The default output is `Documents\Paradox Interactive\Victoria 3\mod\Vic3PriorityBatch`. Enable it in the launcher and follow the [runtime verification guide](docs/runtime-verification.md).

If a mod-only ZIP is supplied, extract `Vic3PriorityBatch` directly into the `mod` folder above and enable it; Python is not needed in that case. The generated mod depends on the source game files, so regenerate it after a game update.

## Compatibility and limitations

Other mods changing the same game GUI files can conflict. To accommodate a GUI mod, keep it enabled, generate with the corresponding GUI overlay, and load the generated patch afterward. See the [GUI notes](docs/gui-audit-2026-10-04.md).

If Shift + Alt or Ctrl + Alt does not behave as intended, generate the diagnostic build with `tools/install.ps1 -Probe` and follow the [probe guide](docs/modifier-dispatch-probe.md). The included AutoHotkey v2 helper is an optional fallback; verify a single native click and the 5/10-entry result first. Do not use the helper alongside a working pure-mod implementation, as one click may be multiplied twice.
