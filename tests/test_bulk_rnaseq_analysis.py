from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
ROUTER_PATH = (
    ROOT
    / "skills"
    / "bulk-rnaseq-analysis"
    / "scripts"
    / "backend_router.py"
)

SPEC = importlib.util.spec_from_file_location("bulk_rnaseq_backend_router", ROUTER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load router from {ROUTER_PATH}")
ROUTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ROUTER)


class BulkRnaSeqRouterTests(unittest.TestCase):
    def test_routes_local_counts_to_rnaseq_templates(self) -> None:
        result = ROUTER.route("local", "raw-counts", {"deg", "gsea"})
        self.assertEqual(result["backends"], ["rnaseq-templates"])
        self.assertEqual(result["warnings"], [])

    def test_routes_tcga_source_to_tcga_toolkit(self) -> None:
        result = ROUTER.route("tcga", "clinical", {"survival", "subtype"})
        self.assertEqual(result["backends"], ["tcga-toolkit"])

    def test_routes_specialized_cancer_tasks_to_tcga_toolkit(self) -> None:
        result = ROUTER.route("local", "maf", {"mutation", "tmb"})
        self.assertEqual(result["backends"], ["tcga-toolkit"])

    def test_routes_mixed_specialized_request_to_both_backends(self) -> None:
        result = ROUTER.route("local", "raw-counts", {"deg", "cnv"})
        self.assertEqual(result["backends"], ["rnaseq-templates", "tcga-toolkit"])

    def test_keeps_geo_survival_in_generic_backend(self) -> None:
        result = ROUTER.route("geo", "normalized", {"survival"})
        self.assertEqual(result["backends"], ["rnaseq-templates"])

    def test_unknown_request_requires_clarification(self) -> None:
        result = ROUTER.route("unknown", "unknown", set())
        self.assertTrue(result["needs_clarification"])
        self.assertIsNone(result["primary_backend"])

    def test_reports_incompatible_expression_scales(self) -> None:
        tpm = ROUTER.route("local", "tpm", {"deseq2"})
        vst = ROUTER.route("local", "vst", {"tme"})
        self.assertTrue(any("raw-counts" in item for item in tpm["blocks"]))
        self.assertTrue(tpm["blocked"])
        self.assertTrue(any("vst" in item for item in vst["blocks"]))
        self.assertTrue(vst["blocked"])

    def test_unknown_analysis_terms_warn_instead_of_silent_drop(self) -> None:
        result = ROUTER.route("local", "raw-counts", {"deg", "gsa"})
        self.assertEqual(result["backends"], ["rnaseq-templates"])
        self.assertTrue(any("gsa" in item for item in result["warnings"]))
        self.assertFalse(result["blocked"])

    def test_blocked_route_exits_3(self) -> None:
        with patch("sys.argv", ["backend_router.py", "route", "--source", "local",
                                "--input-type", "tpm", "--analyses", "deg"]):
            self.assertEqual(ROUTER.main(), 3)

    def test_clean_route_exits_0(self) -> None:
        with patch("sys.argv", ["backend_router.py", "route", "--source", "local",
                                "--input-type", "raw-counts", "--analyses", "deg"]):
            self.assertEqual(ROUTER.main(), 0)

    def test_discovers_configured_backend_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rnaseq = root / "RNAseq-Templates"
            tcga = root / "TCGA"

            for relative in ROUTER.RNASEQ_SENTINELS:
                target = rnaseq / relative
                if Path(relative).suffix:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("template\n", encoding="utf-8")
                else:
                    target.mkdir(parents=True, exist_ok=True)
            (rnaseq / "README.md").write_text(
                "![Version](https://img.shields.io/badge/version-0.9.0-blue)\n",
                encoding="utf-8",
            )

            for relative in ROUTER.TCGA_SENTINELS:
                target = tcga / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("placeholder\n", encoding="utf-8")
            (tcga / "tcga_toolkit" / "VERSION").write_text(
                "0.3.0\n", encoding="utf-8"
            )

            environment = {
                "RNASEQ_TEMPLATES_ROOT": str(rnaseq),
                "TCGA_TOOLKIT_ROOT": str(tcga),
            }
            with patch.dict(os.environ, environment, clear=False):
                result = ROUTER.discover(root)

            self.assertEqual(
                Path(result["rnaseq-templates"]["root"]).resolve(), rnaseq.resolve()
            )
            self.assertEqual(
                Path(result["tcga-toolkit"]["root"]).resolve(), tcga.resolve()
            )
            self.assertEqual(result["rnaseq-templates"]["version"], "0.9.0")
            self.assertEqual(result["tcga-toolkit"]["version"], "0.3.0")
            self.assertFalse(result["rnaseq-templates"]["execution_ready"])
            self.assertFalse(result["tcga-toolkit"]["execution_ready"])

    def test_count_engine_scale_whitelist_covers_every_scale(self):
        for task in ("deg", "deseq2", "limma-voom", "time-course"):
            for scale in ("raw-counts", "tpm", "log-tpm", "vst", "rlog", "normalized", "other", "unknown"):
                with self.subTest(task=task, scale=scale):
                    self.assertEqual(ROUTER.route("local", scale, {task})["blocked"], scale != "raw-counts")

    def test_accepts_tcga_toolkit_directory_as_configured_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "TCGA"
            toolkit = repo / "tcga_toolkit"
            for relative in ROUTER.TCGA_SENTINELS:
                target = repo / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("placeholder\n", encoding="utf-8")

            with patch.dict(
                os.environ, {"TCGA_TOOLKIT_ROOT": str(toolkit)}, clear=False
            ):
                result = ROUTER.discover_one(
                    "TCGA",
                    "TCGA_TOOLKIT_ROOT",
                    ROUTER.TCGA_SENTINELS,
                    Path(temporary),
                )

            self.assertTrue(result["found"])
            self.assertEqual(Path(result["root"]).resolve(), repo.resolve())


if __name__ == "__main__":
    unittest.main()
