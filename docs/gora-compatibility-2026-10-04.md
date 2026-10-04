# GORA UI+ compatibility investigation — 2026-10-04

## Evidence and diagnosis

The user tested the construction screen with GORA UI+ and this mod enabled: every modifier combination added one construction, while Alt combinations moved it to the front. The user subsequently disabled this mod. Therefore the current playset record containing only GORA does not establish which mods were active during that test.

GORA UI+ 1.0.0 (Workshop 3724865565) has four queue handlers in `gui/0_gora_state_panel_overview.gui` and one cancellation handler in `gui/gora_expanded_building_grid.gui`. Previous builds scanned only vanilla GUI and did not patch these files. Since this mod sets the engine's Shift/Ctrl increments to one and implements batching in GUI handlers, an unpatched UI-mod button can produce the observed one-entry result. This is a concrete coverage defect; it does not prove that every reported click used one of those particular handlers.

The inspected Victoria 3 1.14.5 installation lacks `game/gui/building_details_panel.gui`, including the shared `expand_building_button` definition used elsewhere. The local GUI log reports unknown shared widgets and duplicate definitions involving GORA. The supplied `D:/vic3_gui.zip` contains the missing definition. Its four other files bytewise match the installed game, providing strong evidence that the supplied shared definition belongs to this layout. It is included only in generated mod output; no game file is restored or edited.

Repeated event properties are used by the game's bundled `jomini/gui/tweaker/tweaker.gui` (multiple `ondefault` and `onalt` actions). The observed all-one result therefore does not justify concluding that Jomini universally discards repeated handlers. Whether repeated building actions and combined modifiers work as intended still requires in-game verification.

GORA's metadata declares a Community Mod Framework dependency. This patch does not replace that dependency; follow GORA's own installation requirements. No causal claim about that dependency follows from the available test.

## Implementation

- `build_mod(..., gui_overlay_dirs=...)`, repeated CLI `--gui-overlay`, and installer `-GuiOverlay` read matching recovery and UI-mod sources after vanilla, with last-file precedence.
- Output overlap checks include every overlay directory. Inputs remain read only.
- Used `expand_building_button` without any corresponding definition causes a failed build before output replacement, rather than silently shipping incomplete shared buttons.
- Supported construction and cancellation handlers in the effective GUI are patched. Other GORA files remain supplied by the enabled original mod.
- Normal queue handlers contain default/Shift/Ctrl/Alt counts 1/5/10/1. Probe queue counts are 1/2/3/4. Cancellation remains 1/5/10/1 in both builds.

## Verification and limits

Four regression tests failed before implementation and pass afterward: missing shared definition, read-only recovery and custom UI overlays, last-overlay precedence, and output overlap rejection. The complete suite contains 33 passing tests, including Windows installer integration checks.

Actual game + supplied recovery + GORA sources generate ten GUI files, with 14 queue and nine cancellation sites. At each of the 23 sites, both generated builds have the expected action multiplicities. Reversing only the generated blocks restores the corresponding effective input text exactly. All 260 input GUI files retain their SHA-256 hashes. Both mod-only ZIPs pass CRC checking and bytewise comparison against generated files.

No in-game success is claimed. Enable the normal compatibility build after GORA, with old standard/probe builds disabled. On a paused save with enough room/resources, test normal=1, Shift=5, Ctrl=10, Alt=1 at the front, then combined Shift+Alt and Ctrl+Alt. If single modifiers still produce one, test the separately labeled GORA probe (normal=1, Shift=2, Ctrl=3, Alt=4) and inspect fresh GUI logs before interpreting combined routing. The previous all-one test was not a valid probe signature.
