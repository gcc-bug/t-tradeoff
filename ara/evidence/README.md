# Evidence Index

This initialization covers the current single demonstration, balanced policy ablation, depth/count diagnostics, semantic/resource contracts, and prior-work audit. Older reports are indexed in the canonical `reports/README.md` but their numerical claims are not recompiled as current evidence.

The sources are Markdown reports with unnumbered tables, not a paper/PDF with numbered figures or tables. Report bodies, including every source table, are preserved verbatim in the files below. No screenshot or digitized plot was supplied, and none is fabricated. Raw circuit/run JSON remains in place and is indexed individually.

| File | Source | Claims | Description |
|---|---|---|---|
| [single-demonstration](results/single-demonstration.md) | reports/single-demonstration.md | C02, C03 | Complete latest report with fixed references and counterfactuals |
| [balanced study](results/iterative-ancilla.md) | reports/iterative-ancilla.md | C01 | Complete policy and portfolio report |
| [depth diagnostic](results/ancilla-depth.md) | reports/ancilla-depth.md | C01, C03 | Complete scratch/depth comparison |
| [count diagnostic](results/ancilla-count.md) | reports/ancilla-count.md | C01, C03 | Complete count-first control |
| [run pointers](logs/log_pointers.md) | results/ | scope varies | All stored run files, including historical records |
| [source hashes](source-manifest.json) | scoped source inputs | all | SHA-256 and compilation revision |
| [environment](environment.json) | runtime and stored run metadata | all | Current dependency inventory and historical run environment |

Reports were inspected and copied; research experiments were not rerun. The lifecycle checker and compiler checklist are structural validation, not an independent rigor review, proof of novelty, or anonymity certification.

| [website feedback](context/website-feedback.md) | User-supplied external AI advice | none | Discussion context, not research evidence |

## HWP Pareto execution milestone

The later HWP experiment was implemented and run, unlike the retrospective initialization above.
[Evidence bundle](hwp-pareto/README.md) contains the final report, plot, results, replayable witness,
validation, source manifest and superseded baseline diagnostic. It supports E05 and N08–N11;
interpretation O03 remains staged.
