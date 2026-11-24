"""Real entry integration and asset binding checks, not aesthetic evaluation."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import visual_assets


class VisualAssetsTest(unittest.TestCase):
    def cli(self, *args):
        run = subprocess.run([sys.executable, str(ROOT / "scripts/studio.py"), *args],
                             capture_output=True, text=True, timeout=20)
        self.assertEqual(run.returncode, 0, run.stderr)
        return json.loads(run.stdout)

    def test_real_catalog_and_recipe_references_are_consumable(self):
        report = self.cli("visual-assets")
        ids = {item["id"] for item in report["assets"]}
        self.assertTrue(ids)
        for recipe in report["recipes"]:
            self.assertLessEqual(set(recipe["asset_ids"]), ids)
        for item in report["assets"]:
            for record in [*item["files"], item["license"]["file"]]:
                path = Path(record["absolute_path"])
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record["sha256"])
        self.assertFalse(report["render_started"])
        self.assertEqual(report["quality_status"], "unassessed")

    def test_search_and_selected_recipe_do_not_return_unrelated_assets(self):
        report = self.cli("visual-assets", "--query", "纸张")
        self.assertIn("texture-paper", {item["id"] for item in report["assets"]})
        self.assertNotIn("icon-clock", {item["id"] for item in report["assets"]})
        selected = self.cli("visual-assets", "--recipe", "causal-diagram")
        self.assertEqual({a["id"] for a in selected["assets"]}, set(selected["recipes"][0]["asset_ids"]))
        with self.assertRaisesRegex(ValueError, "未知视觉配方"):
            visual_assets.inspect(ROOT, recipe="not-a-recipe")

    def test_original_video_libraries_return_real_specs_prompts_and_rights(self):
        report = self.cli("visual-assets", "--query", "水彩")
        libraries = {x["id"]: x for x in report["reference_libraries"]["libraries"]}
        motion = libraries["motion-prompt"]
        self.assertEqual(motion["count"], 240)
        watercolor = next(x for x in motion["matches"] if x["id"] == "193")
        self.assertIn("transparent watercolor", " ".join(watercolor["spec"]["en"]).lower())
        self.assertTrue(watercolor["prompt_text"])
        self.assertEqual(watercolor["code_status"], "specification_only")
        grain = self.cli("visual-assets", "--query", "颗粒")["reference_libraries"]["libraries"][1]
        self.assertEqual(grain["count"], 504)
        self.assertTrue(grain["reference_only"])
        self.assertEqual(grain["matches"][0]["slug"], "film-grain")
        self.assertIn("Keep the original subject", grain["matches"][0]["prompt_text"])
        self.assertEqual(grain["matches"][0]["image_use"], "reference_only_no_artwork_license")
        zoom = self.cli("visual-assets", "--query", "dolly zoom")["reference_libraries"]["libraries"][0]
        selected = next(x for x in zoom["matches"] if x["id"] == "032")
        self.assertTrue(Path(selected["files"]["code"]["absolute_path"]).is_file())
        self.assertTrue(selected["kits"])
        self.assertIn("3.2 m", " ".join(selected["spec"]["en"]))

    def test_changed_or_escaped_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root = parent / "project"
            root.mkdir()
            path = root / "asset.svg"
            path.write_text("original")
            record = {"path": "asset.svg", "sha256": visual_assets.digest(path)}
            path.write_text("changed")
            with self.assertRaisesRegex(ValueError, "已变化"):
                visual_assets.bound_file(root, record)
            outside = parent / "outside.svg"
            outside.write_text("outside")
            with self.assertRaisesRegex(ValueError, "越出项目"):
                visual_assets.bound_file(root, {"path": "../outside.svg", "sha256": visual_assets.digest(outside)})

    def test_image_research_and_video_requests_load_design_without_production(self):
        for request, profile in [("生成一张关于睡眠的图片", "image"),
                                 ("只研究视觉素材如何提高审美，先不制作", "research"),
                                 ("做一个知识短片，解释声波的传播", "explainer")]:
            with self.subTest(request=request):
                report = self.cli("intent", request)
                self.assertEqual(report["profile"], profile)
                self.assertIn("visual-design", report["packs"])
                self.assertEqual(report["packs"]["visual-design"]["missing"], [])
                self.assertFalse(report["execution_authorized_by_route"])
                self.assertFalse(report["render_started"])

    def test_general_and_song_planning_consume_same_real_design_method(self):
        for content_format in ("general", "knowledge-song"):
            report = self.cli("content-plan", "--question", "怎样用动作解释声波传播", "--format", content_format)
            context = report["development_context"]["visual_design"]
            self.assertEqual(context["method"]["text"], (ROOT / visual_assets.METHOD).read_text())
            self.assertTrue(context["assets"])
            self.assertEqual(context["quality_status"], "unassessed")
            self.assertEqual([x["count"] for x in context["reference_libraries"]["libraries"]], [240, 504])
            self.assertTrue(context["reference_libraries"]["query_required"])

    def test_material_entry_preserves_existing_version_and_rejects_read_only_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "existing"
            out.mkdir()
            marker = out / "parent.txt"
            marker.write_text("preserve parent")
            args = ["visual-build", "--engine", "table", "--input",
                    str(ROOT / "resources/visual-library/examples/table-proof.json"), "--out", str(out)]
            for mode in ("design", "research"):
                run = subprocess.run([sys.executable, str(ROOT / "scripts/studio.py"),
                                      "--mode", mode, *args], capture_output=True, text=True, timeout=20)
                self.assertNotEqual(run.returncode, 0)
                self.assertEqual(marker.read_text(), "preserve parent")
                self.assertEqual(list(out.iterdir()), [marker])

    def test_composite_entry_rejects_changed_material_and_preserves_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            material = root / "material"
            material.mkdir()
            # Negative paths stop before decoding; these are integrity fixtures, not rendered media.
            outputs = []
            for name in ("still.png", "material.webm", "native.zip"):
                file = material / name
                file.write_bytes(b"integrity-fixture")
                outputs.append({"path": name, "sha256": visual_assets.digest(file)})
            (material / "receipt.json").write_text(json.dumps({"engine": "overlay", "outputs": outputs}))
            background = material / "still.png"
            out = root / "parent"
            out.mkdir()
            marker = out / "keep.txt"
            marker.write_text("parent")
            args = ["visual-compose", "--material", str(material), "--background", str(background), "--out", str(out)]
            for mode in ("design", "research"):
                run = subprocess.run([sys.executable, str(ROOT / "scripts/studio.py"), "--mode", mode, *args],
                                     capture_output=True, text=True, timeout=20)
                self.assertNotEqual(run.returncode, 0)
                self.assertEqual(list(out.iterdir()), [marker])
            (material / "still.png").write_bytes(b"changed")
            fresh = root / "fresh"
            run = subprocess.run([sys.executable, str(ROOT / "scripts/studio.py"), "--mode", "research",
                                  *args[:-1], str(fresh)], capture_output=True, text=True, timeout=20)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn("图层与原渲染回执不符", run.stderr)
            self.assertFalse(fresh.exists())

    def test_upstream_scene_uses_content_conditions_for_repair_and_dispatch(self):
        script = """
const {createScene}=require('./resources/visual-library/upstream/Table-VideoSOP/assets/motion/production-core/scene.cjs');
const input=require('./resources/visual-library/examples/table-proof.json');
console.log(JSON.stringify([20,0].map(repairCapacity=>createScene({...input,repairCapacity}).render(9).state)));
"""
        run = subprocess.run([str(ROOT / ".studio/bin/node"), "-e", script], cwd=ROOT,
                             capture_output=True, text=True, check=True, timeout=10)
        repaired, rejected = json.loads(run.stdout)
        self.assertEqual(repaired["finalLengths"], [60, 48, 54])
        self.assertEqual(repaired["route"], "accepted")
        self.assertEqual(rejected["finalLengths"], [76, 48, 54])
        self.assertEqual(rejected["route"], "rework")
        self.assertNotEqual(repaired["position"], rejected["position"])


if __name__ == "__main__":
    unittest.main()
