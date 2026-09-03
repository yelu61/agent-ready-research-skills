from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = Path(
    os.environ.get(
        "BULK_RNASEQ_UPSTREAM_SKILL",
        REPO_ROOT / "skills" / "bulk-rnaseq-upstream",
    )
)
SCRIPTS = SKILL_ROOT / "scripts"


def write_executable(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


class BulkRnaSeqUpstreamTests(unittest.TestCase):
    def run_script(
        self,
        script: str,
        *arguments: str | Path,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(SCRIPTS / script), *(str(item) for item in arguments)],
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

    def make_reference(self, root: Path) -> Path:
        reference = root / "GRCh38_GENCODE_v49"
        index_dir = reference / "hisat2_index"
        index_dir.mkdir(parents=True)
        (reference / "genome.fa").write_text(">chr1\nACGT\n", encoding="utf-8")
        (reference / "genome.fa.fai").write_text(
            "chr1\t4\t6\t4\t5\n", encoding="utf-8"
        )
        (reference / "genes.gtf").write_text(
            'chr1\ttest\texon\t1\t4\t.\t+\t.\tgene_id "g1"; transcript_id "t1";\n',
            encoding="utf-8",
        )
        (reference / "genes.bed12").write_text(
            "chr1\t0\t4\tt1\t0\t+\t0\t4\t0\t1\t4,\t0,\n",
            encoding="utf-8",
        )
        for part in range(1, 9):
            (index_dir / f"genome_hisat2_index.{part}.ht2").write_text(
                "index\n", encoding="utf-8"
            )
        digest = "a" * 64
        (reference / "reference.meta.tsv").write_text(
            "key\tvalue\n"
            "reference_id\tGRCh38\n"
            "annotation_id\tGENCODE_v49\n"
            f"fasta_sha256\t{digest}\n"
            f"gtf_sha256\t{digest}\n"
            f"bed12_sha256\t{digest}\n"
            "index_prefix\tgenome_hisat2_index\n",
            encoding="utf-8",
        )
        return reference

    def make_tool_stubs(self, root: Path) -> tuple[Path, dict[str, str]]:
        tools = root / "tools"
        tools.mkdir()
        for command in ("hisat2", "featureCounts"):
            write_executable(tools / command, "#!/bin/sh\nexit 0\n")
        write_executable(
            tools / "samtools",
            "#!/bin/sh\n"
            "if [ \"${1:-}\" = \"faidx\" ]; then\n"
            "  printf 'chr1\\t4\\t6\\t4\\t5\\n' > \"$2.fai\"\n"
            "fi\n"
            "exit 0\n",
        )
        environment = os.environ.copy()
        environment["PATH"] = f"{tools}{os.pathsep}{environment['PATH']}"
        return tools, environment

    def write_run_config(
        self,
        path: Path,
        reference: Path,
        fastq: Path,
        output: Path,
        **overrides: str,
    ) -> None:
        values = {
            "THREADS": "2",
            "REFERENCE_DIR": str(reference),
            "REFERENCE_ID": "GRCh38",
            "ANNOTATION_ID": "GENCODE_v49",
            "FASTQ_DIR": str(fastq),
            "OUTDIR": str(output),
            "HISAT2_STRANDNESS": "none",
            "FEATURECOUNTS_STRAND": "0",
            "DO_TRIM": "no",
            "MODEL_MODE": "single_species",
            "RUN_FASTQC": "no",
            "RUN_MULTIQC": "no",
        }
        values.update(overrides)
        path.write_text(
            "".join(f"{key}={value}\n" for key, value in values.items()),
            encoding="utf-8",
        )

    def test_all_shell_scripts_parse(self) -> None:
        for script in sorted(SCRIPTS.glob("*.sh")):
            result = subprocess.run(
                ["bash", "-n", str(script)], text=True, capture_output=True, check=False
            )
            self.assertEqual(result.returncode, 0, msg=f"{script}: {result.stderr}")

    def test_reference_layout_accepts_complete_versioned_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            reference = self.make_reference(Path(temporary))
            result = self.run_script("check_reference_layout.sh", reference)
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("Reference layout looks usable", result.stdout)

    def test_reference_layout_rejects_partial_hisat2_index(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            reference = self.make_reference(Path(temporary))
            (reference / "hisat2_index" / "genome_hisat2_index.8.ht2").unlink()
            result = self.run_script("check_reference_layout.sh", reference)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Missing or incomplete", result.stderr)

    def test_reference_builder_creates_one_complete_immutable_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_fasta = root / "source.fa"
            source_gtf = root / "source.gtf"
            source_fasta.write_text(">chr1\nACGT\n", encoding="utf-8")
            source_gtf.write_text(
                'chr1\ttest\texon\t1\t4\t.\t+\t.\tgene_id "g1"; transcript_id "t1";\n',
                encoding="utf-8",
            )
            tools = root / "tools"
            tools.mkdir()
            write_executable(
                tools / "hisat2-build",
                "#!/bin/sh\n"
                "if [ \"${1:-}\" = --version ]; then echo 'hisat2-build test'; exit 0; fi\n"
                "for value do prefix=$value; done\n"
                "part=1\n"
                "while [ \"$part\" -le 8 ]; do\n"
                "  printf 'index\\n' > \"${prefix}.${part}.ht2\"\n"
                "  part=$((part + 1))\n"
                "done\n",
            )
            write_executable(
                tools / "samtools",
                "#!/bin/sh\n"
                "if [ \"${1:-}\" = --version ]; then echo 'samtools test'; exit 0; fi\n"
                "if [ \"${1:-}\" = faidx ]; then\n"
                "  printf 'chr1\\t4\\t6\\t4\\t5\\n' > \"$2.fai\"\n"
                "fi\n",
            )
            write_executable(
                tools / "gtfToGenePred",
                "#!/bin/sh\nfor value do output=$value; done\nprintf 'genePred\\n' > \"$output\"\n",
            )
            write_executable(
                tools / "genePredToBed",
                "#!/bin/sh\nprintf 'chr1\\t0\\t4\\tt1\\t0\\t+\\t0\\t4\\t0\\t1\\t4,\\t0,\\n' > \"$2\"\n",
            )
            environment = os.environ.copy()
            environment["PATH"] = f"{tools}{os.pathsep}{environment['PATH']}"
            output = root / "shared" / "GRCh38_GENCODE_v49"

            result = self.run_script(
                "prepare_reference_hisat2.sh",
                "--fasta",
                source_fasta,
                "--gtf",
                source_gtf,
                "--outdir",
                output,
                "--reference-id",
                "GRCh38",
                "--annotation-id",
                "GENCODE_v49",
                "--threads",
                "2",
                "--no-annotation-index",
                env=environment,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertFalse((output / ".build_incomplete").exists())
            self.assertTrue((output / "genes.bed12").is_file())
            self.assertTrue(
                (output / "hisat2_index" / "genome_hisat2_index.8.ht2").is_file()
            )
            metadata = (output / "reference.meta.tsv").read_text(encoding="utf-8")
            self.assertIn("reference_id\tGRCh38", metadata)
            self.assertIn("annotation_id\tGENCODE_v49", metadata)
            self.assertNotIn("UNAVAILABLE", metadata)

    def test_check_only_accepts_paired_fastq_and_matching_reference_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference = self.make_reference(root)
            fastq = root / "fastq"
            fastq.mkdir()
            (fastq / "sample_R1.fastq.gz").write_text("R1\n", encoding="utf-8")
            (fastq / "sample_R2.fastq.gz").write_text("R2\n", encoding="utf-8")
            config = root / "rnaseq.env"
            self.write_run_config(config, reference, fastq, root / "output")
            _, environment = self.make_tool_stubs(root)

            result = self.run_script(
                "run_bulk_rnaseq_hisat2.sh",
                config,
                "--check-only",
                env=environment,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("Preflight OK: 1 samples", result.stdout)

    def test_check_only_rejects_reference_identity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference = self.make_reference(root)
            fastq = root / "fastq"
            fastq.mkdir()
            (fastq / "sample_R1.fastq.gz").write_text("R1\n", encoding="utf-8")
            (fastq / "sample_R2.fastq.gz").write_text("R2\n", encoding="utf-8")
            config = root / "rnaseq.env"
            self.write_run_config(
                config,
                reference,
                fastq,
                root / "output",
                REFERENCE_ID="GRCm39",
            )
            _, environment = self.make_tool_stubs(root)

            result = self.run_script(
                "run_bulk_rnaseq_hisat2.sh",
                config,
                "--check-only",
                env=environment,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("REFERENCE_ID does not match", result.stderr)

    def test_check_only_rejects_orphan_r2(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference = self.make_reference(root)
            fastq = root / "fastq"
            fastq.mkdir()
            (fastq / "sample_R1.fastq.gz").write_text("R1\n", encoding="utf-8")
            (fastq / "sample_R2.fastq.gz").write_text("R2\n", encoding="utf-8")
            (fastq / "orphan_R2.fastq.gz").write_text("R2\n", encoding="utf-8")
            config = root / "rnaseq.env"
            self.write_run_config(config, reference, fastq, root / "output")
            _, environment = self.make_tool_stubs(root)

            result = self.run_script(
                "run_bulk_rnaseq_hisat2.sh",
                config,
                "--check-only",
                env=environment,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("R2 has no matching R1", result.stderr)

    def test_gtf_to_bed12_uses_transcript_bed12_and_rejects_malformed_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = root / "tools"
            tools.mkdir()
            gtf = root / "genes.gtf"
            gtf.write_text(
                'chr1\ttest\texon\t1\t4\t.\t+\t.\tgene_id "g1"; transcript_id "t1";\n',
                encoding="utf-8",
            )
            write_executable(
                tools / "gtfToGenePred",
                "#!/bin/sh\nfor value do output=$value; done\nprintf 'genePred\\n' > \"$output\"\n",
            )
            write_executable(
                tools / "genePredToBed",
                "#!/bin/sh\n"
                "if [ \"${INVALID_BED12:-0}\" = 1 ]; then\n"
                "  printf 'chr1\\t0\\t4\\tt1\\t0\\t+\\t0\\t4\\t0\\t1\\n' > \"$2\"\n"
                "else\n"
                "  printf 'chr1\\t0\\t4\\tt1\\t0\\t+\\t0\\t4\\t0\\t1\\t4,\\t0,\\n' > \"$2\"\n"
                "fi\n",
            )
            environment = os.environ.copy()
            environment["PATH"] = f"{tools}{os.pathsep}{environment['PATH']}"

            output = root / "genes.bed12"
            valid = self.run_script(
                "gtf_to_bed12.sh", gtf, output, env=environment
            )
            self.assertEqual(valid.returncode, 0, msg=valid.stderr)
            self.assertEqual(len(output.read_text(encoding="utf-8").split("\t")), 12)

            environment["INVALID_BED12"] = "1"
            invalid_output = root / "invalid.bed12"
            invalid = self.run_script(
                "gtf_to_bed12.sh", gtf, invalid_output, env=environment
            )
            self.assertNotEqual(invalid.returncode, 0)
            self.assertFalse(invalid_output.exists())

    def test_xengsort_check_only_accepts_paired_fastq_and_frozen_index(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fastq = root / "fastq"
            fastq.mkdir()
            (fastq / "sample_R1.fastq.gz").write_text("R1\n", encoding="utf-8")
            (fastq / "sample_R2.fastq.gz").write_text("R2\n", encoding="utf-8")
            index = root / "references" / "human_mouse"
            index.parent.mkdir()
            Path(f"{index}.hash").write_text("hash\n", encoding="utf-8")
            Path(f"{index}.info").write_text("info\n", encoding="utf-8")
            config = root / "xengsort.env"
            config.write_text(
                "MODEL_MODE=cross_species\n"
                "HOST_LABEL=mouse\n"
                "GRAFT_LABEL=human\n"
                "THREADS=2\n"
                f"XENGSORT_INDEX={index}\n"
                f"FASTQ_DIR={fastq}\n"
                f"OUTDIR={root / 'output'}\n"
                "RUN_FASTQC=no\n"
                "RUN_MULTIQC=no\n",
                encoding="utf-8",
            )
            tools = root / "tools"
            tools.mkdir()
            write_executable(tools / "xengsort", "#!/bin/sh\nexit 0\n")
            environment = os.environ.copy()
            environment["PATH"] = f"{tools}{os.pathsep}{environment['PATH']}"

            result = self.run_script(
                "split_xenograft_xengsort.sh",
                config,
                "--check-only",
                env=environment,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("Preflight OK: 1 samples", result.stdout)


if __name__ == "__main__":
    unittest.main()
