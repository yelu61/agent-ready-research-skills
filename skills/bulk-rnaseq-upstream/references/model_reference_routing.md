# 实验模型与参考/比对路由

参考选择由“样本中可能存在几种可测序来源”决定，而不是只看体内或体外。

| 实验系统 | 序列来源 | 上游模式 | 能否凭 bulk 比对拆分细胞 |
| --- | --- | --- | --- |
| 单一细胞系、纯细胞球/类器官、单一组织 | 一个物种 | 单物种参考 | 不涉及 |
| 条件培养基/药物处理，只收受体细胞 | 通常一个物种 | 单物种参考 | 不涉及；先确认供体细胞未混入 |
| 人肿瘤 + 人 CAF/免疫直接共培养或 assembloid | 都是人 | same-species mixture | 不能；需要分选、单细胞、空间或谨慎去卷积 |
| Transwell 分仓且分别收样 | 每份样本通常一个来源 | 各 compartment 独立处理 | 依靠实验分仓，不是 alignment |
| 鼠肿瘤细胞移植到鼠 | 都是鼠 | 单物种参考 | 不能区分肿瘤与宿主 |
| 人细胞 + 鼠 feeder/成纤维细胞 | 人 + 鼠 | 人鼠拆分 | 可以分成物种区室 |
| 人 CDX/PDX 移植到鼠 | 人 + 鼠 | 人鼠拆分 | 人约为 graft，鼠约为 host/TME |
| 人源化鼠 + 人肿瘤 | 人肿瘤 + 人免疫 + 鼠宿主 | 人鼠拆分 | 人源肿瘤与人源免疫仍不能互相拆分 |
| 宿主–病原体 dual RNA-seq | 真核宿主 + 病原体 | 专用联合/双参考流程 | 可按来源拆分，但不能直接套用 xenograft 参数 |
| 转基因、CAR、病毒载体或报告基因 | 宿主 + 自定义序列 | 宿主参考追加自定义 contig/GTF | 可定量构建体；需检查同源片段 |
| ERCC/SIRV spike-in | 宿主 + spike-in | 宿主参考追加 spike-in | 单独保留 spike-in 特征 |

无细胞 Matrigel、胶原或合成基质通常不是主动转录来源；若基质中含活的
feeder/CAF，或怀疑可观外源核酸，才把对应来源纳入参考设计和 QC。

## 本 blueprint 支持的运行模式

- single_species：一个物种、一个 HISAT2 index、一个 GTF。
- same_species_mixture：计算上等同单物种，但明确记录不能做细胞来源拆分。
- cross_species_component：已经由 Xengsort 拆出的 graft 或 host FASTQ，
  再分别进入 HISAT2 + featureCounts。
- custom_combined：已经准备好的宿主 + 构建体联合参考。
- spike_in：已经准备好的宿主 + spike-in 联合参考。

未拆分的 cross_species 和 host_pathogen 不允许直接进入单参考脚本。

## 人鼠异种移植推荐流程

Xengsort 的 host/graft 参数都可接收多个 FASTA；其官方 RNA-seq 示例为
每个物种同时使用 genome 和 transcriptome。索引 manifest 必须逐项记录
实际输入，`nobjects` 也要按这组 reference 估计。

paired FASTQ 先做 FastQC/MultiQC，必要时 trimming；随后 Xengsort 分为
graft、host、both、ambiguous、neither。graft FASTQ 使用人参考定量，
host FASTQ 使用鼠参考定量，并生成 species_assignment.tsv。

主分析默认只使用明确归属的 graft 和 host reads。both、ambiguous 和
neither 必须保留用于 QC，不得双重计数到两张矩阵。若需要提高保守同源
基因的回收率，应另建预先声明的敏感性流程，例如双参考独立比对后使用
Disambiguate，而不是临时改变主分析规则。

## 常用人鼠拆分方法

| 方法 | 输入与核心逻辑 | 建议用途 |
| --- | --- | --- |
| Xengsort | FASTQ，k-mer 分类为 host/graft/both/neither/ambiguous | 本 blueprint 默认；速度快，保留五类审计 |
| Xenome | FASTQ，经典 k-mer 五分类 | 复现历史流程或做方法敏感性检查 |
| BBSplit | FASTQ，基于 BBMap 的竞争式 k-mer/mapping | 快速替代方案；固定版本和 ambiguous policy |
| Disambiguate | reads 分别比对两物种，比较 name-sorted BAM 的 score/quality | alignment-based 敏感性分析；计算量约含两次比对 |
| XenofilteR | 两物种 coordinate-sorted BAM，按 mapping/edit distance 过滤 | R/BAM 型历史流程；输出契约与五分类工具不同 |

2025 年对 12 种 PDX 去鼠方案的 benchmark 中，Xengsort 的综合分类表现与
计算效率最好，BBSplit 接近；alignment-based 方法的结果还会受到 STAR、
HISAT2 等 aligner 选择影响。因此主分析固定一种方法，替代方法用于稳健性
评估，不把多个算法的输出临时拼接。

资料：

- [PDX 去鼠流程 benchmark（npj Precision Oncology, 2025）](https://doi.org/10.1038/s41698-025-00902-z)
- [Xengsort 方法论文](https://doi.org/10.1186/s13015-021-00181-w)
- [Disambiguate 方法论文](https://doi.org/10.12688/f1000research.10082.2)
- [Xenome 方法论文](https://doi.org/10.1093/bioinformatics/bts236)
- [XenofilteR 方法论文](https://doi.org/10.1186/s12859-018-2353-5)

## 下游交付契约

单物种至少交付 gene-level integer raw counts、样本清单、比对/计数摘要、
参考与软件版本。人鼠拆分至少交付 human/graft raw-count matrix、
mouse/host raw-count matrix、每个样本五类 read-pair 数及比例、两物种各自
的 HISAT2/featureCounts/MultiQC 记录，以及 ambiguous-read policy。

两个矩阵分别过滤和归一化，不按同名 gene symbol 合并。物种 read 比例是
RNA 组成指标，不是细胞比例。

## 解释边界

普通人源 CDX/PDX 裸鼠模型中，人矩阵主要代表 graft/tumor compartment，
鼠矩阵主要代表 host/TME compartment。若有人源免疫或基质细胞，人矩阵
不再等同于纯肿瘤细胞。鼠侧差异可以表述为处理相关的 TME 响应，但肿瘤
负荷、坏死、取材和物种 RNA composition 都可能参与；仅凭 bulk 结果不能
把它直接归因于某个肿瘤细胞内机制。
