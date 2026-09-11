# Resource provenance and maintenance

The scripts, schemas, project templates, decision rules and synthetic test
materials in this collection are Lu Ye's authored resources, distributed under
the repository and package MIT licenses. They synthesize methodological ideas;
they are not copied publisher articles, official guideline implementations, or
certified implementations of any cited standard. Personal researcher profiles
and private project material are excluded.

| Package | Source and dependency ledger |
|---|---|
| manage-research-project | [Runtime and sources](skills/manage-research-project/references/runtime-and-sources.md): FAIR, Workflow Run Crate principles, authored project/portfolio management modules, and the boundary of local contracts |
| bulk-rnaseq-upstream | [Runtime and sources](skills/bulk-rnaseq-upstream/references/runtime-and-sources.md): official tool interfaces, reference builds, Xengsort evidence and executable-validation limits |
| bulk-rnaseq-analysis | [Runtime and sources](skills/bulk-rnaseq-analysis/references/runtime-and-sources.md): official DESeq2/limma/formula documents, actual backend limits and revision-bound execution requirements |
| critical-paper-reading | [Methodology](skills/critical-paper-reading/references/methodology.md): causal inference, pseudoreplication, reporting and biomarker concepts |
| scientific-reasoning | [Source map](skills/scientific-reasoning/references/source-map.md): causal identification, mechanism, replication, prediction and external validity |
| scrna-analysis-core | [Source map](skills/scrna-analysis-core/references/source-map.md): living Single-cell Best Practices chapters and primary/official supporting evidence |

## Authored management material

On 2026-09-11, the local, user-authored `research-program-manager` v0.1 draft
was incorporated into `manage-research-project`. Project review, planning and
acceptance protocols now live in its package-local `project-decisions.md`;
portfolio reasoning lives in `portfolio-review.md`; ownership and state rules
live in `document-contract.md`. The former draft is not a separately installed
dependency of the unified skill.

The draft's project-specific examples and proposed deployment architecture are
not shipped as deployed capabilities. The packaged management fixtures use
synthetic project/task IDs and supplied evidence excerpts. Existing executable
helper interfaces remain independently maintained and tested. Local backups
and evaluation transcripts are not part of the public distribution.

Invocation and discovery guidance follows the [official skill documentation](https://learn.chatgpt.com/docs/build-skills),
checked on 2026-09-11. This check concerns host behavior, not a new verification
of the scientific references in the package ledgers.

External publications, websites, software and datasets retain their original
copyright and license terms. Links and citations do not grant redistribution of
their full text, figures, data or code. The MIT license covers the authored
package material; any future third-party inclusion requires explicit attribution
and a compatible license recorded here and inside the standalone package.

Before a material release, verify affected recommendations against primary
papers or official documentation. Record source URL/DOI, actual checked date,
supported claim and scope limits in the relevant package ledger. For failures,
record attempted retrieval rather than claiming verification. Stable principles
and changing software APIs need different review frequency. An edited date,
method popularity or newer release number alone cannot justify a scientific
recommendation or capability claim.
