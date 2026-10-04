from __future__ import annotations

import json
import tempfile
import unittest
import os
import shutil
import subprocess
import sys
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY_GUI_FILES = (
    "game/gui/build_urban_buildings_menu.gui",
    "game/gui/states_panel.gui",
    "game/gui/states_panel_buildings.gui",
    "game/gui/right_click_menu.gui",
    "game/gui/production_methods.gui",
    "game/gui/building_details_panel.gui",
)


class BuildModTests(unittest.TestCase):
    def _module(self):
        import importlib.util
        path = ROOT / "tools" / "build_mod.py"
        spec = importlib.util.spec_from_file_location("build_mod", path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def test_build_discovers_shared_queue_and_cancel_only_files(self):
        m = self._module()
        with tempfile.TemporaryDirectory() as td:
            game, out = Path(td) / "game_root", Path(td) / "out"
            gui = game / "game/gui"
            (gui / "nested").mkdir(parents=True)
            (gui / "building_details_panel.gui").write_text(
                'type expand_building_button = widget {\n'
                '  onclick = "[Execute( Building.QueueConstruction )]"\n}\n', encoding="utf-8")
            (gui / "states_panel_buildings.gui").write_text(
                'button = {\n  onclick = "[Execute( Building.CancelConstruction )]"\n}\n'
                'expand_building_button = {}\n', encoding="utf-8")
            (gui / "nested/new_panel.gui").write_text(
                'onclick = "[Execute( Building.QueueConstruction )]"\n', encoding="utf-8")
            (gui / "construction_queue.gui").write_text(
                'onclick = "[Execute( ConstructionQueueElement.CancelConstruction )]"\n', encoding="utf-8")
            report = m.build_mod(game, out)
            self.assertEqual(report["replacement_counts"], {
                "game/gui/building_details_panel.gui": 1,
                "game/gui/nested/new_panel.gui": 1,
                "game/gui/states_panel_buildings.gui": 1,
            })
            self.assertFalse((out / "gui/construction_queue.gui").exists())
            text = (out / "gui/states_panel_buildings.gui").read_text(encoding="utf-8-sig")
            self.assertEqual(text.count('onshift = "[Execute( Building.CancelConstruction )]"'), 5)
            self.assertIn('expand_building_button = {}', text)

    def test_patch_replaces_every_queue_click_with_1_5_10_1_handlers(self):
        m = self._module()
        src = '''button = {\n\tonclick = "[Execute( Building.QueueConstruction )]"\n}\nbutton = {\n    onclick = "[Execute( Building.QueueConstruction )]"\n}\n'''
        out, count = m.patch_gui_text(src)
        self.assertEqual(count, 2)
        self.assertNotIn('onclick = "[Execute( Building.QueueConstruction )]"', out)
        self.assertEqual(out.count('ondefault = "[Execute( Building.QueueConstruction )]"'), 2)
        self.assertEqual(out.count('onshift = "[Execute( Building.QueueConstruction )]"'), 10)
        self.assertEqual(out.count('onctrl = "[Execute( Building.QueueConstruction )]"'), 20)
        self.assertEqual(out.count('onalt = "[Execute( Building.QueueConstruction )]"'), 2)
        self.assertEqual(out.count("# PRIORITY_BATCH_BEGIN"), 2)

    def test_patch_also_preserves_batch_cancel_behavior_after_define_override(self):
        m = self._module()
        src = '''button = {\n\tonclick = "[Execute( Building.QueueConstruction )]"\n}\nbutton = {\n\tonclick = "[Execute( Building.CancelConstruction )]"\n}\n'''
        out, count = m.patch_gui_text(src)
        self.assertEqual(count, 2)
        self.assertNotIn('onclick = "[Execute( Building.CancelConstruction )]"', out)
        self.assertEqual(out.count('ondefault = "[Execute( Building.CancelConstruction )]"'), 1)
        self.assertEqual(out.count('onshift = "[Execute( Building.CancelConstruction )]"'), 5)
        self.assertEqual(out.count('onctrl = "[Execute( Building.CancelConstruction )]"'), 10)
        self.assertEqual(out.count('onalt = "[Execute( Building.CancelConstruction )]"'), 1)

    def test_patch_preserves_unrelated_text(self):
        m = self._module()
        src = 'before\n  onclick = "[Execute( Building.QueueConstruction )]"\nafter\n'
        out, _ = m.patch_gui_text(src)
        self.assertTrue(out.startswith("before\n"))
        self.assertTrue(out.endswith("after\n"))

    def test_patch_requires_at_least_one_building_queue_or_cancel_click(self):
        m = self._module()
        with self.assertRaisesRegex(ValueError, "QueueConstruction"):
            m.patch_gui_text("button = { onclick = '[Other.Action]' }\n")

    def test_patch_accepts_cancel_only_file_in_standard_and_probe_modes(self):
        m = self._module()
        src = 'onclick = "[Execute( Building.CancelConstruction )]"\n'
        for probe in (False, True):
            with self.subTest(probe=probe):
                out, count = m.patch_gui_text(src, probe=probe)
                self.assertEqual(count, 1)
                self.assertEqual(out.count('onshift = "[Execute( Building.CancelConstruction )]"'), 5)
                self.assertEqual(out.count('onctrl = "[Execute( Building.CancelConstruction )]"'), 10)

    def test_patch_preserves_trailing_comments_and_unrelated_hash_strings(self):
        m = self._module()
        src = ('text = "## onshift"\n'
               '  onclick = "[Execute(Building.QueueConstruction)]" # build here\n'
               '# onclick = "[Execute( Building.CancelConstruction )]"\n')
        out, count = m.patch_gui_text(src)
        self.assertEqual(count, 1)
        self.assertIn('text = "## onshift"', out)
        self.assertIn('# build here', out)
        self.assertIn('# onclick = "[Execute( Building.CancelConstruction )]"', out)

    def test_patch_does_not_modify_actions_inside_multiline_quoted_text(self):
        m = self._module()
        src = r'''text = "description
onclick = \"[Execute( Building.CancelConstruction )]\"
end"
onclick = "[Execute( Building.QueueConstruction )]"
'''
        out, count = m.patch_gui_text(src)
        self.assertEqual(count, 1)
        self.assertIn('onclick = \\"[Execute( Building.CancelConstruction )]\\"', out)

    def test_patch_rejects_unhandled_target_handlers_instead_of_partial_patch(self):
        m = self._module()
        valid = 'onclick = "[Execute( Building.QueueConstruction )]"\n'
        for unsupported in (
            'button = { onclick = "[Execute( Building.CancelConstruction )]" }\n',
            'onshift = "[Execute( Building.QueueConstruction )]"\n',
            'onclick = "[Execute( Building.QueueConstruction )][Other.Action]"\n',
        ):
            with self.subTest(unsupported=unsupported):
                with self.assertRaisesRegex(ValueError, "Unsupported"):
                    m.patch_gui_text(valid + unsupported)

    def test_patch_rejects_conflicting_handlers_in_same_widget(self):
        m = self._module()
        for other in (
            'click_modifiers = { onalt = "[Other.Action]" }',
            'onshift = "[Other.Action]"',
            'onclick = "[Execute( Building.QueueConstruction )]"',
            'onclick = "[Other.Action]"',
        ):
            with self.subTest(other=other):
                src = 'button = {\n  onclick = "[Execute( Building.QueueConstruction )]"\n' + other + '\n}\n'
                with self.assertRaisesRegex(ValueError, "Conflicting"):
                    m.patch_gui_text(src)

    def test_patch_allows_modifier_handlers_in_child_and_sibling_widgets(self):
        m = self._module()
        unrelated = ('child = {\n  click_modifiers = { onalt = "[Other.Action]" }\n}\n')
        src = ('button = {\n  onclick = "[Execute( Building.QueueConstruction )]"\n'
               + unrelated + '}\n' + unrelated)
        out, count = m.patch_gui_text(src)
        self.assertEqual(count, 1)
        self.assertEqual(out.count(unrelated), 2)

    def test_build_rejects_unsupported_discovered_action_preserving_destination(self):
        m = self._module()
        with tempfile.TemporaryDirectory() as td:
            game, out = Path(td) / "game_root", Path(td) / "out"
            gui = game / "game/gui"
            gui.mkdir(parents=True)
            (gui / "building_details_panel.gui").write_text(
                'onclick = "[Execute( Building.QueueConstruction )]"\n', encoding="utf-8")
            (gui / "zzz_extra.gui").write_text(
                'onalt = "[Execute( Building.CancelConstruction )]"\n', encoding="utf-8")
            out.mkdir()
            (out / "keep.txt").write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "zzz_extra.gui.*Unsupported"):
                m.build_mod(game, out)
            self.assertEqual((out / "keep.txt").read_text(), "keep")

    def test_build_rejects_output_overlapping_game_or_builder_sources(self):
        m = self._module()
        with tempfile.TemporaryDirectory() as td:
            game = Path(td) / "game_root"
            builder_root = Path(td) / "builder"
            import shutil
            shutil.copytree(ROOT / "mod", builder_root / "mod")
            m.ROOT = builder_root
            m.STATIC_MOD_DIR = builder_root / "mod"
            for rel in LEGACY_GUI_FILES:
                p = game / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('onclick = "[Execute( Building.QueueConstruction )]"\n', encoding="utf-8")
            for out in (game, game.parent, game / "game/gui/output", builder_root, builder_root / "mod/output"):
                with self.subTest(out=out):
                    with self.assertRaisesRegex(ValueError, "overlap"):
                        m.build_mod(game, out)
            self.assertTrue((game / "game/gui/building_details_panel.gui").exists())

    def test_rebuild_preserves_unrelated_previous_directory(self):
        m = self._module()
        with tempfile.TemporaryDirectory() as td:
            game, out = Path(td) / "game_root", Path(td) / "out"
            for rel in LEGACY_GUI_FILES:
                p = game / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('onclick = "[Execute( Building.QueueConstruction )]"\n', encoding="utf-8")
            out.mkdir()
            (out / "old.txt").write_text("old", encoding="utf-8")
            previous = out.with_name("out.previous")
            previous.mkdir()
            (previous / "keep.txt").write_text("keep", encoding="utf-8")
            m.build_mod(game, out)
            self.assertTrue((previous / "keep.txt").exists(), "rebuild deleted unrelated backup")
            self.assertEqual((previous / "keep.txt").read_text(), "keep")
            self.assertFalse((out / "old.txt").exists())

    def test_failed_publish_restores_existing_mod(self):
        m = self._module()
        with tempfile.TemporaryDirectory() as td:
            game, out = Path(td) / "game_root", Path(td) / "out"
            for rel in LEGACY_GUI_FILES:
                p = game / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('onclick = "[Execute( Building.QueueConstruction )]"\n', encoding="utf-8")
            out.mkdir()
            (out / "keep.txt").write_text("keep", encoding="utf-8")
            rename = Path.rename
            def fail_stage_publish(source, destination):
                if ".staging-" in source.name:
                    raise OSError("simulated locked destination")
                return rename(source, destination)
            with patch.object(Path, "rename", fail_stage_publish):
                with self.assertRaisesRegex(OSError, "locked"):
                    m.build_mod(game, out)
            self.assertEqual((out / "keep.txt").read_text(), "keep")
            self.assertFalse(list(Path(td).glob("out.staging-*")))

    def test_patch_preserves_nonbuilding_queue_and_military_actions(self):
        m = self._module()
        other = ('onclick = "[Execute( ConstructionQueueElement.CancelConstruction )]"\n'
                 'onclick = "[Execute( Building.QueueMilitaryConstruction( MilitaryFormation.Self, CombatUnitType.Self ) )]"\n'
                 'click_modifiers = {\n'
                 '  onalt = "[Execute( ConstructionQueueElement.MoveToTop )]"\n}\n')
        src = 'button = {\n  onclick = "[Execute( Building.QueueConstruction )]"\n}\n' + other
        out, count = m.patch_gui_text(src)
        self.assertEqual(count, 1)
        self.assertTrue(out.endswith(other))

    def test_static_payload_has_one_step_defines_and_1145_metadata(self):
        define_text = (ROOT / "mod/common/defines/zzz_priority_batch_defines.txt").read_text(encoding="utf-8")
        self.assertIn("NCountry = {", define_text)
        self.assertNotIn("NGame = {", define_text)
        self.assertIn("CONSTRUCTION_QUEUE_INCREMENT_SHIFT = 1", define_text)
        self.assertIn("CONSTRUCTION_QUEUE_INCREMENT_CONTROL = 1", define_text)
        meta = json.loads((ROOT / "mod/.metadata/metadata.json").read_text(encoding="utf-8"))
        self.assertTrue(meta["supported_game_version"].startswith("1.14"))
        self.assertEqual(meta["name"], "Priority Batch Construction")
        self.assertEqual(meta["game_id"], "victoria3")

    def test_build_fails_before_replacing_destination_when_gui_directory_missing(self):
        m = self._module()
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            game = td / "game_root"
            out = td / "out"
            out.mkdir()
            sentinel = out / "keep.txt"
            sentinel.write_text("keep", encoding="utf-8")
            with self.assertRaises(FileNotFoundError):
                m.build_mod(game, out)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_build_accepts_installed_1145_layout_without_details_panel(self):
        m = self._module()
        with tempfile.TemporaryDirectory() as td:
            game, out = Path(td) / "game_root", Path(td) / "out"
            gui = game / "game/gui"
            gui.mkdir(parents=True)
            (gui / "build_urban_buildings_menu.gui").write_text(
                'onclick = "[Execute( Building.QueueConstruction )]"\n', encoding="utf-8")
            (gui / "goods_state_panel.gui").write_text(
                'onclick = "[Execute( Building.CancelConstruction )]"\n', encoding="utf-8")
            report = m.build_mod(game, out)
            self.assertEqual(report["replacement_counts"], {
                "game/gui/build_urban_buildings_menu.gui": 1,
                "game/gui/goods_state_panel.gui": 1,
            })

    def test_build_rejects_gui_tree_with_no_queue_handler(self):
        m = self._module()
        with tempfile.TemporaryDirectory() as td:
            game, out = Path(td) / "game_root", Path(td) / "out"
            gui = game / "game/gui"
            gui.mkdir(parents=True)
            (gui / "states_panel_buildings.gui").write_text(
                'onclick = "[Execute( Building.CancelConstruction )]"\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "No Building.QueueConstruction"):
                m.build_mod(game, out)
            self.assertFalse(out.exists())

    def test_build_rejects_missing_shared_expansion_type(self):
        m = self._module()
        with tempfile.TemporaryDirectory() as td:
            game, out = Path(td) / "game", Path(td) / "out"
            gui = game / "game/gui"
            gui.mkdir(parents=True)
            (gui / "states_panel.gui").write_text(
                'onclick = "[Execute( Building.QueueConstruction )]"\n'
                'expand_building_button = {}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Missing shared GUI type.*expand_building_button"):
                m.build_mod(game, out)
            self.assertFalse(out.exists())

    def test_build_patches_missing_definition_and_ui_mod_from_read_only_overlays(self):
        m = self._module()
        with tempfile.TemporaryDirectory() as td:
            game, out = Path(td) / "game", Path(td) / "out"
            gui = game / "game/gui"
            gui.mkdir(parents=True)
            (gui / "states_panel.gui").write_text(
                'button = {\n  onclick = "[Execute( Building.QueueConstruction )]"\n}\n'
                'expand_building_button = {}\n', encoding="utf-8")
            recovery, ui_mod = Path(td) / "recovery", Path(td) / "ui_mod"
            recovery.mkdir()
            ui_mod.mkdir()
            definition = recovery / "building_details_panel.gui"
            definition.write_text('type expand_building_button = widget {\n'
                                  '  onclick = "[Execute( Building.QueueConstruction )]"\n}\n', encoding="utf-8")
            custom = ui_mod / "custom_overview.gui"
            custom.write_text('onclick = "[Execute( Building.QueueConstruction )]"\n', encoding="utf-8")
            original = {p: p.read_bytes() for p in (definition, custom, gui / "states_panel.gui")}
            report = m.build_mod(game, out, probe=True, gui_overlay_dirs=[recovery, ui_mod])
            self.assertEqual(report["replacement_counts"], {
                "game/gui/building_details_panel.gui": 1,
                "game/gui/custom_overview.gui": 1,
                "game/gui/states_panel.gui": 1,
            })
            for name in ("building_details_panel.gui", "custom_overview.gui", "states_panel.gui"):
                text = (out / "gui" / name).read_text(encoding="utf-8-sig")
                self.assertEqual(text.count('onshift = "[Execute( Building.QueueConstruction )]"'), 2)
            self.assertTrue(all(p.read_bytes() == contents for p, contents in original.items()))
            self.assertFalse((gui / "building_details_panel.gui").exists())

    def test_gui_overlay_precedence_uses_last_source_for_same_file(self):
        m = self._module()
        with tempfile.TemporaryDirectory() as td:
            game, out, overlay = Path(td) / "game", Path(td) / "out", Path(td) / "ui"
            gui = game / "game/gui"
            gui.mkdir(parents=True)
            overlay.mkdir()
            (gui / "states_panel.gui").write_text('onclick = "[Execute( Building.QueueConstruction )]"\n', encoding="utf-8")
            (overlay / "states_panel.gui").write_text('# UI CUSTOM LAYOUT\n'
                'onclick = "[Execute( Building.QueueConstruction )]"\n', encoding="utf-8")
            m.build_mod(game, out, gui_overlay_dirs=[overlay])
            self.assertTrue((out / "gui/states_panel.gui").read_text(encoding="utf-8-sig").startswith('# UI CUSTOM LAYOUT\n'))

    def test_build_rejects_output_overlapping_gui_overlay(self):
        m = self._module()
        with tempfile.TemporaryDirectory() as td:
            game, overlay = Path(td) / "game", Path(td) / "overlay"
            with self.assertRaisesRegex(ValueError, "overlap"):
                m.build_mod(game, overlay, gui_overlay_dirs=[overlay])

    @unittest.skipUnless(os.name == "nt" and shutil.which("powershell.exe"), "Windows PowerShell integration")
    def test_installer_falls_back_when_python_launcher_is_broken(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            gui = base / "game_root/game/gui"
            gui.mkdir(parents=True)
            # This also proves the builder no longer needs building_details_panel.gui.
            (gui / "states_panel.gui").write_text(
                'onclick = "[Execute( Building.QueueConstruction )]"\n', encoding="utf-8")
            shim = base / "bin"
            shim.mkdir()
            (shim / "py.cmd").write_text('@echo off\nexit /b 101\n', encoding="ascii")
            (shim / "python.cmd").write_text(f'@echo off\n"{sys.executable}" %*\n', encoding="utf-8")
            env = dict(os.environ, PATH=str(shim) + os.pathsep + os.environ.get("PATH", ""))
            out = base / "out"
            result = subprocess.run([
                "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                str(ROOT / "tools/install.ps1"), "-GameDir", str(base / "game_root"), "-OutputDir", str(out),
            ], env=env, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, (result.stdout + result.stderr).decode(errors="replace"))
            self.assertTrue((out / "gui/states_panel.gui").exists())

    @unittest.skipUnless(os.name == "nt" and shutil.which("powershell.exe"), "Windows PowerShell integration")
    def test_installer_detects_steam_library_without_details_panel(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            game = base / "drive/SteamLibrary/steamapps/common/Victoria 3"
            (game / "game/gui").mkdir(parents=True)
            (game / "launcher").mkdir()
            (game / "launcher/launcher-settings.json").write_text('{"gameId":"victoria3"}', encoding="utf-8")
            (game / "game/gui/states_panel.gui").write_text(
                'onclick = "[Execute( Building.QueueConstruction )]"\n', encoding="utf-8")
            shim = base / "bin"
            shim.mkdir()
            (shim / "py.cmd").write_text(f'@echo off\n"{sys.executable}" %2 %3 %4 %5 %6 %7 %8 %9\n', encoding="utf-8")
            env = dict(os.environ, PATH=str(shim) + os.pathsep + os.environ.get("PATH", ""))
            def quote(path):
                return "'" + str(path).replace("'", "''") + "'"
            command = (
                'function global:Get-ItemProperty { param($Path,$ErrorAction) throw "no registry" }; '
                'function global:Get-PSDrive { param($PSProvider) [pscustomobject]@{Root='
                + quote(base / 'drive') + '} }; & ' + quote(ROOT / 'tools/install.ps1')
                + ' -OutputDir ' + quote(base / 'out')
            )
            result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                                     '-Command', command], env=env, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, (result.stdout + result.stderr).decode(errors="replace"))
            self.assertTrue((base / "out/gui/states_panel.gui").exists())

    def test_build_generates_all_patched_gui_files_and_static_payload(self):
        m = self._module()
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            game = td / "game_root"
            out = td / "out"
            for rel in LEGACY_GUI_FILES:
                p = game / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('x\n\tonclick = "[Execute( Building.QueueConstruction )]"\ny\n', encoding="utf-8")
            report = m.build_mod(game, out)
            self.assertEqual(set(report["patched_files"]), set(LEGACY_GUI_FILES))
            for rel in LEGACY_GUI_FILES:
                generated = out / rel.replace("game/", "", 1)
                self.assertTrue(generated.exists(), rel)
                text = generated.read_text(encoding="utf-8")
                self.assertIn("# PRIORITY_BATCH_BEGIN", text)
            self.assertTrue((out / "common/defines/zzz_priority_batch_defines.txt").exists())
            self.assertTrue((out / ".metadata/metadata.json").exists())

    def test_windows_helper_is_scoped_to_victoria3_and_repeats_5_and_10(self):
        text = (ROOT / "tools/Vic3PriorityBatch.ahk").read_text(encoding="utf-8")
        self.assertIn('WinActive("ahk_exe victoria3.exe")', text)
        self.assertIn("Loop 5", text)
        self.assertIn("Loop 10", text)
        self.assertIn('GetKeyState("Alt", "P")', text)


    def test_builder_exposes_explicit_114_only_runtime_warning(self):
        m = self._module()
        warning = m.COMPATIBILITY_WARNING
        self.assertIn("1.14.x", warning)
        self.assertIn("not auto-detected", warning)

    def test_windows_installer_and_runtime_docs_exist(self):
        installer = (ROOT / "tools/install.ps1").read_text(encoding="utf-8")
        self.assertIn("Victoria 3", installer)
        self.assertIn("build_mod.py", installer)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Shift+Alt", readme)
        self.assertIn("Ctrl+Alt", readme)
        runtime = (ROOT / "docs/runtime-verification.md").read_text(encoding="utf-8")
        for phrase in ("Normal click", "Shift+click", "Ctrl+click", "Alt+click", "Shift+Alt+click", "Ctrl+Alt+click"):
            self.assertIn(phrase, runtime)


    def test_probe_queue_handlers_use_distinct_1_2_3_4_counts(self):
        m = self._module()
        src = 'button = {\n\tonclick = "[Execute( Building.QueueConstruction )]"\n}\n'
        out, count = m.patch_gui_text(src, probe=True)
        self.assertEqual(count, 1)
        self.assertEqual(out.count('ondefault = "[Execute( Building.QueueConstruction )]"'), 1)
        self.assertEqual(out.count('onshift = "[Execute( Building.QueueConstruction )]"'), 2)
        self.assertEqual(out.count('onctrl = "[Execute( Building.QueueConstruction )]"'), 3)
        self.assertEqual(out.count('onalt = "[Execute( Building.QueueConstruction )]"'), 4)

    def test_probe_build_is_isolated_and_marks_metadata_and_report(self):
        m = self._module()
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            game = td / "game_root"
            out = td / "probe_out"
            for rel in LEGACY_GUI_FILES:
                p = game / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('onclick = "[Execute( Building.QueueConstruction )]"\n', encoding="utf-8")
            report = m.build_mod(game, out, probe=True)
            self.assertEqual(report["mode"], "probe")
            meta = json.loads((out / ".metadata/metadata.json").read_text(encoding="utf-8"))
            self.assertIn("Modifier Probe", meta["name"])
            generated = (out / "gui/building_details_panel.gui").read_text(encoding="utf-8")
            self.assertEqual(generated.count('onshift = "[Execute( Building.QueueConstruction )]"'), 2)
            self.assertEqual(generated.count('onctrl = "[Execute( Building.QueueConstruction )]"'), 3)
            self.assertEqual(generated.count('onalt = "[Execute( Building.QueueConstruction )]"'), 4)

    def test_probe_windows_installer_uses_separate_output_and_docs_decode_results(self):
        installer = (ROOT / "tools/install.ps1").read_text(encoding="utf-8")
        self.assertIn("[switch]$Probe", installer)
        self.assertIn("Vic3PriorityBatchProbe", installer)
        self.assertIn('"--probe"', installer)
        docs = (ROOT / "docs/modifier-dispatch-probe.md").read_text(encoding="utf-8")
        for phrase in (
            "Shift+Alt",
            "2 new entries",
            "4 new entries",
            "Ctrl+Alt",
            "3 new entries",
            "7 new entries",
        ):
            self.assertIn(phrase, docs)


if __name__ == "__main__":
    unittest.main()
