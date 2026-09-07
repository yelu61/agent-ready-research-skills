from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAPPER = ROOT / "skills/bulk-rnaseq-analysis/scripts/build_run_registration.py"
REGISTER = ROOT / "skills/manage-research-project/scripts/register_run.py"


def run(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(script), *args], text=True, capture_output=True)


def write_table(path: Path, rows: list[dict], delimiter: str = ",") -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def fixture(root: Path) -> tuple[Path, Path]:
    native = root / "analysis/runs/bulk-rnaseq__main"
    delivery = root / "results"
    for path in (native, delivery, root / "workflows/bulk-rnaseq", root / "data/raw"):
        path.mkdir(parents=True)
    (root / "data/raw/counts.tsv").write_text("gene\tA\nG\t5\n")
    (root / "workflows/bulk-rnaseq/analysis.ipynb").write_text('{"cells":[]}')
    config = root / "workflows/bulk-rnaseq/config.R"
    config.write_text("THRESHOLD_GRID <- list()\n")
    (native / "run_runtime.csv").write_text("component,version\nR,4\n")
    (native / "deg.tsv").write_text("gene\tpvalue\nG\t0.001\n")
    write_table(native / "run_inputs.csv", [{"role": "primary", "path": "../../../data/raw/counts.tsv",
                                             "md5": md5(root / "data/raw/counts.tsv"), "status": "present"}])
    write_table(native / "run_manifest.csv", [{
        "manifest_schema_version": "2", "run_id": native.name, "status": "completed",
        "config_file": "../../../workflows/bulk-rnaseq/config.R", "config_md5": md5(config),
        "input_manifest_file": "run_inputs.csv", "input_manifest_md5": md5(native / "run_inputs.csv"),
        "runtime_manifest_file": "run_runtime.csv", "backend_revision": "a" * 40,
        "completed_at": "2026-09-07T00:00:00Z",
    }])
    (delivery / "deg.tsv").write_bytes((native / "deg.tsv").read_bytes())
    (delivery / "README.html").write_text('<a href="deg.tsv">DEG</a>')
    write_table(delivery / "MANIFEST.tsv", [{"path": "deg.tsv", "source_path": "deg.tsv",
                "source_run_id": native.name, "md5": md5(native / "deg.tsv")}], "\t")
    return native, delivery


def map_run(root: Path) -> subprocess.CompletedProcess:
    return run(MAPPER, str(root), "--run", "analysis/runs/bulk-rnaseq__main", "--delivery", "results",
               "--entry-point", "workflows/bulk-rnaseq/analysis.ipynb", "--analysis-id", "A-main",
               "--output", "workflows/bulk-rnaseq/registration.json")


def append_native_input(native: Path, role: str, path: Path | str, digest: str) -> None:
    with (native / "run_inputs.csv").open() as handle:
        inputs = list(csv.DictReader(handle))
    inputs.append({"role": role, "path": str(path), "md5": digest, "status": "present"})
    write_table(native / "run_inputs.csv", inputs)
    with (native / "run_manifest.csv").open() as handle:
        manifest = list(csv.DictReader(handle))
    manifest[0]["input_manifest_md5"] = md5(native / "run_inputs.csv")
    write_table(native / "run_manifest.csv", manifest)


class RunRegistrationTests(unittest.TestCase):
    def test_legacy_project_relative_paths_use_unique_checksum_match(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            native, _ = fixture(root)
            with (native / "run_inputs.csv").open() as handle:
                inputs = list(csv.DictReader(handle))
            inputs[0]["path"] = "data/raw/counts.tsv"
            write_table(native / "run_inputs.csv", inputs)
            with (native / "run_manifest.csv").open() as handle:
                manifest = list(csv.DictReader(handle))
            manifest[0]["config_file"] = "workflows/bulk-rnaseq/config.R"
            manifest[0]["input_manifest_md5"] = md5(native / "run_inputs.csv")
            write_table(native / "run_manifest.csv", manifest)
            # The run-relative candidate exists, but has the wrong bytes.
            decoy = native / "workflows/bulk-rnaseq/config.R"
            decoy.parent.mkdir(parents=True)
            decoy.write_text("different config")
            result = map_run(root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            document = json.loads((root / "workflows/bulk-rnaseq/registration.json").read_text())
            self.assertEqual(document["run"]["config_path"], "workflows/bulk-rnaseq/config.R")

    def test_legacy_ambiguous_paths_and_lost_reference_basename_are_rejected(self) -> None:
        for ambiguous in (True, False):
            with self.subTest(ambiguous=ambiguous), tempfile.TemporaryDirectory() as temporary:
                base = Path(temporary)
                root = base / "project"
                native, _ = fixture(root)
                if ambiguous:
                    with (native / "run_manifest.csv").open() as handle:
                        manifest = list(csv.DictReader(handle))
                    manifest[0]["config_file"] = "workflows/bulk-rnaseq/config.R"
                    write_table(native / "run_manifest.csv", manifest)
                    duplicate = native / "workflows/bulk-rnaseq/config.R"
                    duplicate.parent.mkdir(parents=True)
                    duplicate.write_bytes((root / "workflows/bulk-rnaseq/config.R").read_bytes())
                else:
                    installed = base / "orgdb.sqlite"
                    installed.write_bytes(b"installed reference")
                    append_native_input(native, "annotation_db", installed.name, md5(installed))
                result = map_run(root)
                self.assertEqual(result.returncode, 1)
                self.assertIn("Ambiguous legacy native path" if ambiguous else "basename-only", result.stdout)

    def test_explicit_run_path_base_inherits_for_inputs_and_has_no_project_fallback(self) -> None:
        for proper_path in (True, False):
            with self.subTest(proper_path=proper_path), tempfile.TemporaryDirectory() as temporary:
                base = Path(temporary)
                root = base / "project"
                native, _ = fixture(root)
                installed = base / "orgdb.sqlite"
                installed.write_bytes(b"installed reference")
                append_native_input(native, "annotation_db", "../../../../orgdb.sqlite", md5(installed))
                with (native / "run_manifest.csv").open() as handle:
                    manifest = list(csv.DictReader(handle))
                manifest[0]["path_base"] = "run"
                if not proper_path:
                    manifest[0]["config_file"] = "workflows/bulk-rnaseq/config.R"
                write_table(native / "run_manifest.csv", manifest)
                result = map_run(root)
                self.assertEqual(result.returncode, 0 if proper_path else 1, result.stdout + result.stderr)
                if not proper_path:
                    self.assertIn("cannot be resolved", result.stdout)

    def test_input_path_base_run_overrides_legacy_candidate_search(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            native, _ = fixture(root)
            with (native / "run_inputs.csv").open() as handle:
                inputs = list(csv.DictReader(handle))
            inputs[0].update(path="data/raw/counts.tsv", path_base="run")
            write_table(native / "run_inputs.csv", inputs)
            with (native / "run_manifest.csv").open() as handle:
                manifest = list(csv.DictReader(handle))
            manifest[0]["input_manifest_md5"] = md5(native / "run_inputs.csv")
            write_table(native / "run_manifest.csv", manifest)
            result = map_run(root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("cannot be resolved", result.stdout)

    def test_external_annotations_and_frozen_run_references_preserve_typed_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "project"
            native, _ = fixture(root)
            annotation = base / "installed-orgdb.sqlite"
            annotation.write_bytes(b"immutable annotation reference")
            (native / "0-Config").mkdir()
            frozen = native / "0-Config/GO_REFERENCE.rds"
            frozen.write_bytes(b"frozen GO terms")
            append_native_input(native, "annotation_db", annotation, md5(annotation))
            # Relative locations outside the project are valid references too.
            append_native_input(native, "ortholog_cache", "../../../../installed-orgdb.sqlite", md5(annotation))
            append_native_input(native, "go_reference", "0-Config/GO_REFERENCE.rds", md5(frozen))
            mapped = map_run(root)
            self.assertEqual(mapped.returncode, 0, mapped.stdout + mapped.stderr)
            metadata_path = root / "workflows/bulk-rnaseq/registration.json"
            document = json.loads(metadata_path.read_text())
            references = [row for row in document["artifacts"] if row["path"].endswith("GO_REFERENCE.rds")]
            self.assertEqual(len(references), 1)
            self.assertEqual(references[0]["role"], "go_reference")
            self.assertEqual(references[0]["direction"], "input")
            self.assertIn("Verified external reference annotation_db", document["run"]["notes"])
            self.assertIn("Verified external reference ortholog_cache", document["run"]["notes"])
            self.assertIn(md5(annotation), document["run"]["notes"])
            self.assertNotIn(str(annotation), metadata_path.read_text())
            self.assertTrue(any(row["path"].endswith("run_inputs.csv") for row in document["artifacts"]))
            imported = run(REGISTER, str(root), "--metadata", "workflows/bulk-rnaseq/registration.json", "--apply")
            self.assertEqual(imported.returncode, 0, imported.stdout + imported.stderr)
            self.assertEqual(annotation.read_bytes(), b"immutable annotation reference")

    def test_external_reference_drift_and_external_primary_are_rejected(self) -> None:
        for role, drift in (("annotation_db", True), ("primary", False)):
            with self.subTest(role=role), tempfile.TemporaryDirectory() as temporary:
                base = Path(temporary)
                root = base / "project"
                native, _ = fixture(root)
                external = base / "external.sqlite"
                external.write_bytes(b"original")
                append_native_input(native, role, external, md5(external))
                if drift:
                    external.write_bytes(b"changed")
                result = map_run(root)
                self.assertEqual(result.returncode, 1)
                self.assertIn("reference checksum mismatch" if drift else "External non-reference", result.stdout)

    def test_nonreference_input_inside_native_run_is_still_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            native, _ = fixture(root)
            append_native_input(native, "primary", "deg.tsv", md5(native / "deg.tsv"))
            result = map_run(root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("input is also inside the output run", result.stdout)

    def test_native_notebook_and_delivery_import_is_idempotent_without_readiness_upgrade(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture(root)
            mapped = map_run(root)
            self.assertEqual(mapped.returncode, 0, mapped.stdout + mapped.stderr)
            args = (str(root), "--metadata", "workflows/bulk-rnaseq/registration.json")
            dry = run(REGISTER, *args)
            self.assertEqual(dry.returncode, 0, dry.stdout + dry.stderr)
            self.assertFalse((root / "provenance").exists())
            applied = run(REGISTER, *args, "--apply")
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
            before = {path.name: path.read_bytes() for path in (root / "provenance").iterdir()}
            again = run(REGISTER, *args, "--apply")
            self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
            self.assertEqual(json.loads(again.stdout)["added"], {"RUNS.tsv": 0, "ARTIFACTS.tsv": 0})
            self.assertEqual(before, {path.name: path.read_bytes() for path in (root / "provenance").iterdir()})
            with (root / "provenance/RUNS.tsv").open() as handle:
                record = list(csv.DictReader(handle, delimiter="\t"))[0]
            self.assertTrue(record["entry_point"].endswith(".ipynb"))
            self.assertEqual(record["technical_validation_status"], "not_assessed")
            self.assertEqual(record["readiness_id"], "")
            self.assertTrue(record["input_artifact_ids"])
            self.assertTrue(record["output_artifact_ids"])
            with (root / "provenance/ARTIFACTS.tsv").open() as handle:
                artifacts = list(csv.DictReader(handle, delimiter="\t"))
            native = next(row for row in artifacts if row["path"] == "analysis/runs/bulk-rnaseq__main/deg.tsv")
            copied = next(row for row in artifacts if row["path"] == "results/deg.tsv")
            self.assertEqual(copied["sha256"], native["sha256"])
            self.assertNotEqual(copied["artifact_id"], native["artifact_id"])
            self.assertEqual(copied["parent_artifact_ids"], native["artifact_id"])
            metadata = root / "workflows/bulk-rnaseq/registration.json"
            doc = json.loads(metadata.read_text())
            doc["run"]["notes"] = "rebind"
            metadata.write_text(json.dumps(doc))
            refused = run(REGISTER, *args, "--apply")
            self.assertEqual(refused.returncode, 1)
            self.assertIn("rebind", refused.stdout)
            self.assertEqual(before, {path.name: path.read_bytes() for path in (root / "provenance").iterdir()})

    def test_mapping_refuses_changed_inputs_and_delivery_bytes(self) -> None:
        for changed in ("data/raw/counts.tsv", "results/deg.tsv"):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                fixture(root)
                (root / changed).write_text("changed")
                mapped = map_run(root)
                self.assertEqual(mapped.returncode, 1, mapped.stdout)
                self.assertFalse((root / "workflows/bulk-rnaseq/registration.json").exists())

    def test_direct_cli_identity_does_not_require_project_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture(root)
            result = run(MAPPER, str(root), "--run", "analysis/runs/bulk-rnaseq__main",
                         "--entry-point", "backend:rnaseq-templates/templates/General/run_analysis.R",
                         "--analysis-id", "A-main", "--output", "workflows/bulk-rnaseq/registration.json")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            metadata = json.loads((root / "workflows/bulk-rnaseq/registration.json").read_text())
            self.assertTrue(metadata["run"]["entry_point"].startswith("backend:rnaseq-templates/"))
            self.assertEqual(metadata["run"]["technical_validation_status"], "not_assessed")

    def test_register_refuses_artifact_drift_after_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture(root)
            self.assertEqual(map_run(root).returncode, 0)
            (root / "analysis/runs/bulk-rnaseq__main/deg.tsv").write_text("changed")
            result = run(REGISTER, str(root), "--metadata", "workflows/bulk-rnaseq/registration.json", "--apply")
            self.assertEqual(result.returncode, 1)
            self.assertIn("checksum mismatch", result.stdout)
            self.assertFalse((root / "provenance").exists())

    def test_mixed_derivative_delivery_requires_registered_parent_and_preserves_origin(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            native, delivery = fixture(root)
            parent_args = (str(root), "--metadata", "workflows/bulk-rnaseq/registration.json", "--apply")
            # Register parent before producing a separate derivative delivery.
            parent_map = run(MAPPER, str(root), "--run", str(native.relative_to(root)),
                             "--entry-point", "workflows/bulk-rnaseq/analysis.ipynb", "--analysis-id", "A-main",
                             "--output", "workflows/bulk-rnaseq/registration.json")
            self.assertEqual(parent_map.returncode, 0, parent_map.stdout)
            derivative = root / "analysis/runs/bulk-rnaseq__plots"
            derivative.mkdir()
            for name in ("run_inputs.csv", "run_runtime.csv"):
                (derivative / name).write_bytes((native / name).read_bytes())
            (derivative / "plot.svg").write_text("<svg/>")
            with (native / "run_manifest.csv").open() as handle:
                meta = list(csv.DictReader(handle))[0]
            meta.update(run_id=derivative.name, parent_run_id=native.name)
            write_table(derivative / "run_manifest.csv", [meta])
            (delivery / "plot.svg").write_bytes((derivative / "plot.svg").read_bytes())
            write_table(delivery / "MANIFEST.tsv", [
                {"path": "deg.tsv", "source_path": "deg.tsv", "source_run_id": native.name, "md5": md5(native / "deg.tsv")},
                {"path": "plot.svg", "source_path": "plot.svg", "source_run_id": derivative.name, "md5": md5(derivative / "plot.svg")},
            ], "\t")
            mapped = run(MAPPER, str(root), "--run", str(derivative.relative_to(root)), "--delivery", "results",
                         "--parent-run-dir", str(native.relative_to(root)), "--analysis-id", "A-main",
                         "--entry-point", "workflows/bulk-rnaseq/analysis.ipynb",
                         "--output", "workflows/bulk-rnaseq/derivative-registration.json")
            self.assertEqual(mapped.returncode, 0, mapped.stdout)
            derivative_args = (str(root), "--metadata", "workflows/bulk-rnaseq/derivative-registration.json", "--apply")
            missing_parent = run(REGISTER, *derivative_args)
            self.assertEqual(missing_parent.returncode, 1)
            self.assertIn("Register the parent run first", missing_parent.stdout)
            self.assertFalse((root / "provenance").exists())
            self.assertEqual(run(REGISTER, *parent_args).returncode, 0)
            before = (root / "provenance/ARTIFACTS.tsv").read_text()
            registered = run(REGISTER, *derivative_args)
            self.assertEqual(registered.returncode, 0, registered.stdout + registered.stderr)
            self.assertTrue((root / "provenance/ARTIFACTS.tsv").read_text().startswith(before))
            with (root / "provenance/ARTIFACTS.tsv").open() as handle:
                artifacts = list(csv.DictReader(handle, delimiter="\t"))
            source = next(row for row in artifacts if row["path"] == str((native / "deg.tsv").relative_to(root)))
            copied = next(row for row in artifacts if row["path"] == "results/deg.tsv")
            self.assertEqual(source["run_id"], native.name)
            self.assertEqual(copied["parent_artifact_ids"], source["artifact_id"])
            self.assertEqual(copied["run_id"], derivative.name)
            again = run(REGISTER, *derivative_args)
            self.assertEqual(again.returncode, 0, again.stdout)
            self.assertEqual(json.loads(again.stdout)["added"], {"RUNS.tsv": 0, "ARTIFACTS.tsv": 0})

    def test_registration_refuses_symlinked_artifact_and_registry(self) -> None:
        for changed in ("results/deg.tsv", "provenance/RUNS.tsv"):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                fixture(root)
                self.assertEqual(map_run(root).returncode, 0)
                target = root / changed
                target.parent.mkdir(exist_ok=True)
                if target.exists():
                    target.unlink()
                target.symlink_to(root / "data/raw/counts.tsv")
                result = run(REGISTER, str(root), "--metadata", "workflows/bulk-rnaseq/registration.json", "--apply")
                self.assertEqual(result.returncode, 1)
                self.assertIn("Symlink", result.stdout)


if __name__ == "__main__":
    unittest.main()
