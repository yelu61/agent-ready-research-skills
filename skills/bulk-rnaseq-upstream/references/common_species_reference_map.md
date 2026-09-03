# 常见物种参考映射

本表用于选择参考体系，不代表“永远使用最新 release”。每次运行都要冻结
装配、注释来源、release、下载日期和文件校验值。

| 物种 | 推荐新项目装配 | 常见注释来源 | 标准目录示例 |
| --- | --- | --- | --- |
| 人 | GRCh38 | GENCODE / Ensembl / NCBI | `<REFERENCE_ROOT>/human/GRCh38_<annotation_release>` |
| 小鼠 | GRCm39 | GENCODE / Ensembl / NCBI | `<REFERENCE_ROOT>/mouse/GRCm39_<annotation_release>` |
| 大鼠 | mRatBN7.2 | Ensembl / NCBI | `<REFERENCE_ROOT>/rat/mRatBN7.2_<annotation_release>` |
| 斑马鱼 | GRCz11 | Ensembl / NCBI | `<REFERENCE_ROOT>/zebrafish/GRCz11_<annotation_release>` |
| 果蝇 | BDGP6 | FlyBase / Ensembl Metazoa | `<REFERENCE_ROOT>/fly/BDGP6_<annotation_release>` |
| 线虫 | WBcel235 | WormBase / Ensembl Metazoa | `<REFERENCE_ROOT>/worm/WBcel235_<annotation_release>` |
| 拟南芥 | TAIR10 | Araport / Ensembl Plants | `<REFERENCE_ROOT>/arabidopsis/TAIR10_<annotation_release>` |
| 酿酒酵母 | R64-1-1 | SGD / Ensembl Fungi | `<REFERENCE_ROOT>/yeast/R64-1-1_<annotation_release>` |

## 选择规则

1. FASTA 与 GTF 必须来自可证明兼容的同一装配；不要凭文件名猜测。
2. 不在同一运行中混用 UCSC、Ensembl、GENCODE、NCBI 的 contig 命名。
3. 旧项目若需复现，应继续使用原装配与注释，不因新 release 自动升级。
4. 人鼠异种移植同时准备两套独立 HISAT2 参考，以及一个由两物种序列建立的
   Xengsort 索引；Xengsort 的 RNA-seq 官方示例为每个物种同时提供 genome
   与 transcriptome FASTA，下游注释仍分别使用各物种 GTF。
5. 自定义载体、转基因或 spike-in 应作为带唯一 contig/feature 前缀的附加
   参考，避免与宿主 ID 冲突。
6. 同一 bundle 的 HISAT2 index、FASTA `.fai` 和 `genes.bed12` 只生成一次；
   注释或 FASTA 更新时创建新目录，不原地覆盖旧版本。

每个标准参考目录至少包含 genome.fa、genome.fa.fai、genes.gtf、
genes.bed12、reference.meta.tsv 和 hisat2_index/genome_hisat2_index.*。
