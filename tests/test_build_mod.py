from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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

    def test_target_gui_files_match_vanilla_1145_inventory(self):
        m = self._module()
        self.assertEqual(
            m.TARGET_GUI_FILES,
            (
                "game/gui/build_urban_buildings_menu.gui",
                "game/gui/states_panel.gui",
                "game/gui/states_panel_buildings.gui",
                "game/gui/right_click_menu.gui",
                "game/gui/production_methods.gui",
                "game/gui/building_details_panel.gui",
            ),
        )

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

    def test_patch_requires_at_least_one_queue_click(self):
        m = self._module()
        with self.assertRaisesRegex(ValueError, "QueueConstruction"):
            m.patch_gui_text("button = { onclick = '[Other.Action]' }\n")

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

    def test_build_fails_before_replacing_destination_when_target_missing(self):
        m = self._module()
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            game = td / "game_root"
            out = td / "out"
            out.mkdir()
            sentinel = out / "keep.txt"
            sentinel.write_text("keep", encoding="utf-8")
            for rel in m.TARGET_GUI_FILES[:-1]:
                p = game / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('onclick = "[Execute( Building.QueueConstruction )]"\n', encoding="utf-8")
            with self.assertRaises(FileNotFoundError):
                m.build_mod(game, out)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_build_generates_all_patched_gui_files_and_static_payload(self):
        m = self._module()
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            game = td / "game_root"
            out = td / "out"
            for rel in m.TARGET_GUI_FILES:
                p = game / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('x\n\tonclick = "[Execute( Building.QueueConstruction )]"\ny\n', encoding="utf-8")
            report = m.build_mod(game, out)
            self.assertEqual(set(report["patched_files"]), set(m.TARGET_GUI_FILES))
            for rel in m.TARGET_GUI_FILES:
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


if __name__ == "__main__":
    unittest.main()
