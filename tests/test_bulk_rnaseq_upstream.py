from __future__ import annotations

import os
import csv
import gzip
import hashlib
import shlex
import stat
import subprocess
import sys
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
        hashes = {
            "fasta_sha256": reference / "genome.fa",
            "fai_sha256": reference / "genome.fa.fai",
            "gtf_sha256": reference / "genes.gtf",
            "bed12_sha256": reference / "genes.bed12",
            **{f"index_{part}_sha256": index_dir / f"genome_hisat2_index.{part}.ht2" for part in range(1, 9)},
        }
        (reference / "reference.meta.tsv").write_text(
            "key\tvalue\n"
            "bundle_schema_version\t2\n"
            "reference_id\tGRCh38\n"
            "annotation_id\tGENCODE_v49\n"
            "index_prefix\tgenome_hisat2_index\n"
            "index_suffix\tht2\n" +
            "".join(f"{key}\t{hashlib.sha256(path.read_bytes()).hexdigest()}\n" for key, path in hashes.items()),
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
        evidence = path.parent / "strandedness.txt"
        evidence.write_text("Reviewed fixture protocol: unstranded library.\n", encoding="utf-8")
        values = {
            "THREADS": "2",
            "REFERENCE_DIR": str(reference),
            "REFERENCE_ID": "GRCh38",
            "ANNOTATION_ID": "GENCODE_v49",
            "FASTQ_DIR": str(fastq),
            "OUTDIR": str(output),
            "HISAT2_STRANDNESS": "none",
            "FEATURECOUNTS_STRAND": "0",
            "STRANDEDNESS_SOURCE": "library_protocol",
            "STRANDEDNESS_EVIDENCE": str(evidence),
            "DO_TRIM": "no",
            "MODEL_MODE": "single_species",
            "RUN_FASTQC": "no",
            "RUN_MULTIQC": "no",
        }
        values.update(overrides)
        path.write_text(
            "".join(f"{key}={shlex.quote(value)}\n" for key, value in values.items()),
            encoding="utf-8",
        )

    def write_fastq_pair(self, directory: Path, sample: str) -> None:
        directory.mkdir(exist_ok=True)
        for mate in (1, 2):
            with gzip.open(directory / f"{sample}_R{mate}.fastq.gz", "wt") as handle:
                handle.write(f"@read/{mate}\nACGT\n+\nIIII\n")

    def make_pipeline_stubs(self, root: Path) -> dict[str, str]:
        tools = root / "pipeline-tools"
        tools.mkdir()
        # These stubs verify runner arguments/outputs, not aligner numerical accuracy.
        source = f"#!{sys.executable}\n" + r'''
import os
import sys
from pathlib import Path
name = Path(sys.argv[0]).name
args = sys.argv[1:]
if args and args[0] in ['--version', '-version', '-v']:
    print(name + ' test-stub')
    sys.exit(0)
if name == 'trimmomatic':
    for dest in args[6:10]:
        Path(dest).write_bytes(Path(args[4]).read_bytes())
elif name == 'hisat2':
    print('alignment fixture')
elif name == 'samtools':
    if args[0] in ['view', 'sort']:
        sys.stdin.read()
    if args[0] == 'view':
        print('BAM fixture')
    if args[0] == 'sort':
        Path(args[args.index('-o') + 1]).write_text('BAM fixture')
elif name == 'featureCounts':
    bams = [arg for arg in args if arg.endswith('.sorted.bam')]
    if os.environ.get('WRONG_COUNT_SAMPLE'):
        bams[-1] = 'unexpected.sorted.bam'
    Path(args[args.index('-o') + 1]).write_text(
        '# featureCounts fixture\nGeneid\tChr\tStart\tEnd\tStrand\tLength\t' +
        '\t'.join(bams) + '\ng1\tchr1\t1\t4\t+\t4\t' + '\t'.join(['1'] * len(bams)) + '\n')
'''
        for name in ("hisat2", "samtools", "featureCounts", "trimmomatic"):
            write_executable(tools / name, source)
        return {**os.environ, "PATH": str(tools) + os.pathsep + os.environ["PATH"]}

    def make_xengsort_index(self, root: Path) -> Path:
        index = root / "references" / "human_mouse"
        index.parent.mkdir()
        for suffix in ("hash", "info"):
            Path(f"{index}.{suffix}").write_text(suffix + "\n", encoding="utf-8")
        source_digest = hashlib.sha256(b">source\nACGT\n").hexdigest()
        meta = {
            "bundle_schema_version": "2", "host_label": "mouse", "graft_label": "human",
            "host_reference_id": "GRCm39", "graft_reference_id": "GRCh38",
            "host_fasta_count": "1", "graft_fasta_count": "1",
            "host_fasta_1": "mouse.fa", "graft_fasta_1": "human.fa",
            "host_fasta_1_sha256": source_digest, "graft_fasta_1_sha256": source_digest,
            **{f"index_{suffix}_sha256": hashlib.sha256(Path(f"{index}.{suffix}").read_bytes()).hexdigest()
               for suffix in ("hash", "info")},
        }
        Path(f"{index}.manifest.tsv").write_text(
            "key\tvalue\n" + "".join(f"{key}\t{value}\n" for key, value in meta.items()), encoding="utf-8")
        return index

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
            index = self.make_xengsort_index(root)
            config = root / "xengsort.env"
            config.write_text(
                "MODEL_MODE=cross_species\n"
                "HOST_LABEL=mouse\n"
                "GRAFT_LABEL=human\n"
                "HOST_REFERENCE_ID=GRCm39\n"
                "GRAFT_REFERENCE_ID=GRCh38\n"
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

            original = Path(f"{index}.manifest.tsv").read_text()
            for case in ("missing_manifest", "swapped_labels", "wrong_assembly", "hash_drift", "info_drift"):
                with self.subTest(case=case):
                    manifest = Path(f"{index}.manifest.tsv")
                    manifest.write_text(original)
                    if case == "missing_manifest":
                        manifest.unlink()
                    elif case == "swapped_labels":
                        manifest.write_text(original.replace("host_label\tmouse", "host_label\thuman")
                                            .replace("graft_label\thuman", "graft_label\tmouse"))
                    elif case == "wrong_assembly":
                        manifest.write_text(original.replace("GRCm39", "GRCm38"))
                    else:
                        suffix = case.split("_")[0]
                        Path(f"{index}.{suffix}").write_text("changed\n")
                    rejected = self.run_script("split_xenograft_xengsort.sh", config, "--check-only", env=environment)
                    self.assertNotEqual(rejected.returncode, 0, rejected.stdout)
                    self.assertNotIn("Preflight OK", rejected.stdout)
                    self.assertFalse((root / "output").exists())
                    for suffix in ("hash", "info"):
                        Path(f"{index}.{suffix}").write_text(suffix + "\n")

    def test_reference_layout_rejects_real_file_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            reference = self.make_reference(Path(temporary))
            targets = [reference / name for name in ("genome.fa", "genome.fa.fai", "genes.gtf", "genes.bed12")]
            targets += list((reference / "hisat2_index").glob("*.ht2"))
            for path in targets:
                with self.subTest(file=path.name):
                    original = path.read_bytes()
                    # Whitespace/comment changes preserve the layout but change bytes.
                    path.write_bytes(original + b"\n")
                    result = self.run_script("check_reference_layout.sh", reference)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("checksum mismatch", result.stderr)
                    path.write_bytes(original)

    def test_reference_rejects_legacy_duplicate_or_mixed_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            reference = self.make_reference(Path(temporary))
            path = reference / "reference.meta.tsv"
            original = path.read_text()
            for changed in (original.replace("bundle_schema_version\t2", "bundle_schema_version\t1"),
                            original + "reference_id\tWRONG\n"):
                path.write_text(changed)
                result = self.run_script("check_reference_layout.sh", reference)
                self.assertNotEqual(result.returncode, 0)
            path.write_text(original)
            (reference / "hisat2_index" / "genome_hisat2_index.1.ht2l").write_text("other index\n")
            result = self.run_script("check_reference_layout.sh", reference)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Mixed HISAT2", result.stderr)

    def test_complete_large_hisat2_index_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            reference = self.make_reference(Path(temporary))
            for path in (reference / "hisat2_index").glob("*.ht2"):
                path.rename(path.with_suffix(".ht2l"))
            meta = reference / "reference.meta.tsv"
            meta.write_text(meta.read_text().replace("index_suffix\tht2\n", "index_suffix\tht2l\n"))
            result = self.run_script("check_reference_layout.sh", reference)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_unknown_or_missing_strandedness_evidence_blocks_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference = self.make_reference(root)
            fastq = root / "fastq"
            self.write_fastq_pair(fastq, "sample")
            _, environment = self.make_tool_stubs(root)
            config = root / "run.env"
            for settings in ({"STRANDEDNESS_SOURCE": "unknown"},
                             {"STRANDEDNESS_EVIDENCE": str(root / "missing.txt")},
                             {"HISAT2_STRANDNESS": "unknown"},
                             {"STRANDEDNESS_SOURCE": ""},
                             {"HISAT2_STRANDNESS": "RF", "FEATURECOUNTS_STRAND": "1"}):
                with self.subTest(settings=settings):
                    self.write_run_config(config, reference, fastq, root / "output", **settings)
                    result = self.run_script("run_bulk_rnaseq_hisat2.sh", config, "--check-only", env=environment)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse((root / "output").exists())
            self.write_run_config(config, reference, fastq, root / "output",
                                  STRANDEDNESS_SOURCE="rseqc", HISAT2_STRANDNESS="RF", FEATURECOUNTS_STRAND="2")
            result = self.run_script("run_bulk_rnaseq_hisat2.sh", config, "--check-only", env=environment)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_trimmed_leftover_is_not_aligned_or_counted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference = self.make_reference(root)
            fastq = root / "fastq"
            self.write_fastq_pair(fastq, "current")
            output = root / "output"
            trimmed = output / "trimmed"
            trimmed.mkdir(parents=True)
            for mate in (1, 2):
                (trimmed / f"old_R{mate}_paired.fastq.gz").write_bytes(b"retained old file")
            adapter = root / "adapters.fa"
            adapter.write_text(">adapter\nACGT\n")
            config = root / "run.env"
            self.write_run_config(config, reference, fastq, output, DO_TRIM="yes", TRIMMOMATIC_ADAPTERS=str(adapter))
            result = self.run_script("run_bulk_rnaseq_hisat2.sh", config, env=self.make_pipeline_stubs(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Count output verified: 1 genes, 1 manifest-matched samples", result.stdout)
            self.assertNotIn("old.sorted.bam", (output / "counts/gene_counts.txt").read_text())
            self.assertFalse((output / "hisat2/old.sorted.bam").exists())
            self.assertEqual((trimmed / "old_R1_paired.fastq.gz").read_bytes(), b"retained old file")
            with (output / "provenance/sample_manifest.tsv").open() as handle:
                self.assertEqual([row["sample"] for row in csv.DictReader(handle, delimiter="\t")], ["current"])
            manifest = (output / "provenance/run_manifest.tsv").read_text()
            self.assertIn("strandedness_source\tlibrary_protocol", manifest)
            self.assertIn(hashlib.sha256((root / "strandedness.txt").read_bytes()).hexdigest(), manifest)

    def test_runner_rejects_counter_output_for_wrong_sample(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference = self.make_reference(root)
            fastq = root / "fastq"
            self.write_fastq_pair(fastq, "sample")
            config = root / "run.env"
            self.write_run_config(config, reference, fastq, root / "output")
            environment = self.make_pipeline_stubs(root)
            environment["WRONG_COUNT_SAMPLE"] = "1"
            result = self.run_script("run_bulk_rnaseq_hisat2.sh", config, env=environment)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Count sample columns/order", result.stderr)
            self.assertNotIn("Pipeline finished successfully", result.stdout)

    def test_count_contract_rejects_bad_values_and_sample_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            counts = root / "counts.tsv"
            manifest = root / "samples.tsv"
            bams = [str(root / name) for name in ("A.sorted.bam", "B.sorted.bam")]
            manifest.write_text("sample\tr1\tr2\tbam\nA\tA1\tA2\t" + bams[0] + "\nB\tB1\tB2\t" + bams[1] + "\n")
            header = "Geneid\tChr\tStart\tEnd\tStrand\tLength\t" + "\t".join(bams) + "\n"
            row = "g1\tchr1\t1\t4\t+\t4\t0\t12\n"
            def run_table(text: str) -> subprocess.CompletedProcess[str]:
                counts.write_text(text)
                return subprocess.run([sys.executable, str(SCRIPTS / "validate_gene_counts.py"),
                                       "--counts", str(counts), "--sample-manifest", str(manifest)],
                                      capture_output=True, text=True)
            self.assertEqual(run_table(header + row).returncode, 0)
            for bad in ("-1", "1.5", "NaN", "inf", "", "1e3"):
                with self.subTest(value=bad):
                    rejected = run_table(header + row.replace("\t12\n", "\t" + bad + "\n"))
                    self.assertNotEqual(rejected.returncode, 0)
            for table in (header, header + row + row,
                          header.replace(bams[1], bams[0]) + row,
                          header.replace("\t".join(bams), "\t".join(reversed(bams))) + row,
                          header.rstrip() + "\tC.sorted.bam\n" + row.rstrip() + "\t1\n"):
                self.assertNotEqual(run_table(table).returncode, 0)

    def test_xengsort_builder_records_direction_and_index_fingerprints(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = root / "tools"
            tools.mkdir()
            write_executable(tools / "xengsort", f"#!{sys.executable}\n" +
                             "import sys\nfrom pathlib import Path\n"
                             "if sys.argv[1] == '--version':\n    print('xengsort test'); sys.exit(0)\n"
                             "prefix = sys.argv[sys.argv.index('--index') + 1]\n"
                             "for suffix in ['hash', 'info']:\n    Path(prefix + '.' + suffix).write_text(suffix)\n")
            host, graft = root / "mouse.fa", root / "human.fa"
            host.write_text(">mouse\nAAAA\n")
            graft.write_text(">human\nCCCC\n")
            index = root / "index" / "human_mouse"
            args = ["--host-fasta", host, "--graft-fasta", graft, "--host-label", "mouse", "--graft-label", "human",
                    "--host-reference-id", "GRCm39", "--graft-reference-id", "GRCh38", "--index-prefix", index, "--nobjects", "10"]
            environment = {**os.environ, "PATH": str(tools) + os.pathsep + os.environ["PATH"]}
            result = self.run_script("prepare_reference_xengsort.sh", *args, env=environment)
            self.assertEqual(result.returncode, 0, result.stderr)
            with Path(f"{index}.manifest.tsv").open() as handle:
                meta = {row["key"]: row["value"] for row in csv.DictReader(handle, delimiter="\t")}
            self.assertEqual(meta["host_label"], "mouse")
            self.assertEqual(meta["host_fasta_1_sha256"], hashlib.sha256(host.read_bytes()).hexdigest())
            self.assertEqual(meta["graft_fasta_1_sha256"], hashlib.sha256(graft.read_bytes()).hexdigest())
            for suffix in ("hash", "info"):
                self.assertEqual(meta[f"index_{suffix}_sha256"], hashlib.sha256(Path(f"{index}.{suffix}").read_bytes()).hexdigest())
            self.assertNotEqual(self.run_script("prepare_reference_xengsort.sh", *args, env=environment).returncode, 0)


if __name__ == "__main__":
    unittest.main()
