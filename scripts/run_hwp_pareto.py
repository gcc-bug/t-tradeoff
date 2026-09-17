#!/usr/bin/env python3
"""Run the frozen development study; all output circuits use existing schemas."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import resource
import subprocess
import sys
import time
from datetime import datetime, timezone

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from collective_phase.adapters.pyzx import PyZXAdapter
from collective_phase.baselines.common import CompilationConstraints
from collective_phase.baselines.hwp import compile_hwp_adder_unitary
from collective_phase.hwp_pareto import Plan, baseline_frontiers, build_library, emit, frontier
from collective_phase.inputs.manifest import acquire_manifest, load_case, load_manifest
from collective_phase.ir import AngleBinding, ParityTerm, PhaseBlock, PhaseProgram, make_program
from collective_phase.lowering import LoweredCircuit, RotationSynthesizer
from collective_phase.circuit import Candidate
from collective_phase.verification import verify_lowered_circuit
from collective_phase.resources import estimate_resources
from collective_phase.preprocessing import preprocess
from collective_phase.selection import dominates_resources
from collective_phase.verification.lowered import verify_optimized_lowered_circuit


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".gz":
        with gzip.open(path, "wt", encoding="utf-8") as f:
            json.dump(value, f, sort_keys=True)
    else:
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def load_program(case):
    if case["kind"] == "native":
        return make_program(case["id"], case["n"], [1 << i for i in range(case["n"])],
                            AngleBinding("theta", case["angle"]))
    if case["kind"] == "masks":
        return make_program(case["id"], case["n"], case["masks"], AngleBinding("theta", case["angle"]))
    if case["kind"] == "groups":
        angles, terms = [], []
        for i, group in enumerate(case["groups"]):
            angles.append(AngleBinding(f"a{i}", group["angle"]))
            for _ in range(group["size"]):
                j = len(terms)
                terms.append(ParityTerm(f"t{j}", 1 << j, f"a{i}"))
        return PhaseProgram(case["id"], len(terms), tuple(angles), (PhaseBlock("block", tuple(terms)),))
    if case["kind"] == "qedc":
        manifest = load_manifest(ROOT / case["manifest"])
        source = next(c for c in manifest["cases"] if c["id"] == case["id"])
        assert source["sha256"] == case["sha256"]
        acquire_manifest({"cases": [source]}, ROOT)
        assert sha(ROOT / source["local_path"]) == case["sha256"]
        return load_case(source, AngleBinding("theta", case["angle"]), ROOT)
    raise ValueError(case["kind"])


def base_plans(library, max_ancilla):
    """Recover base-constructor batches, then use the shared block precision policy."""
    result = []
    index = {t.id: i for i, t in enumerate(library.terms)}
    option = {(o.terms, o.layout): o for o in library.options}
    for cap in range(1, library.max_batch + 1):
        base = compile_hwp_adder_unitary(library.program,
                CompilationConstraints(max_ancilla, "unitary_clifford_t", hwp_search_cap=cap),
                batch_limit=cap)
        chosen = []
        for step in base.transformation_trace:
            action = step["action"]
            if action == "hwp_adder_unitary_batch":
                mask = sum(1 << index[i] for i in step["term_ids"])
                chosen.append(option[mask, step["layout"]])
            elif action in {"direct_group_fallback", "direct_singleton_fallback"}:
                chosen.extend(option[1 << index[i], "direct"] for i in step["term_ids"])
        plan = Plan((sum(o.resources[0] for o in chosen), sum(o.resources[1] for o in chosen),
                     max((o.resources[2] for o in chosen), default=0)), tuple((o.id,) for o in chosen))
        lowered, _ = emit(library, plan)
        if lowered.candidate.operations != base.operations:
            raise AssertionError("base reference does not reproduce existing constructor")
        result.append(plan)
    return result


def nondominated_records(records, key):
    eligible = [r for r in records if r.get(key) is not None]
    return [r for r in eligible if not any(dominates_resources(tuple(s[key]), tuple(r[key])) for s in eligible)]


def constrained(points, ancilla, depth):
    return min((tuple(p) for p in points if p[2] <= ancilla and p[1] <= depth), default=None)


def compare(points, reference, ancillas, depths):
    rows = []
    for a in ancillas:
        for d in depths:
            p, b = constrained(points, a, d), constrained(reference, a, d)
            rows.append({"ancilla_cap": a, "depth_cap": d, "proposed": p, "baseline": b,
                         "outcome": "both_infeasible" if p is None and b is None else
                         "newly_feasible" if b is None else "proposed_infeasible" if p is None else
                         "T_win" if p[0] < b[0] else "T_loss" if p[0] > b[0] else "T_tie",
                         "delta_T": None if p is None or b is None else b[0] - p[0]})
    return rows


def run_case(case, config, output, synth):
    program = load_program(case)
    print(f"{program.id}: building library", flush=True)
    library = build_library(program, config["total_error"], synth,
                            max_terms=config["max_terms"], max_batch=config["max_batch"])
    max_a = max(config["ancilla_caps"])
    model = frontier(library, max_a, timeout_seconds=config["search_seconds"])
    baselines = baseline_frontiers(library, max_a, timeout_seconds=config["baseline_seconds"])
    print(f"{program.id}: {len(library.options)} options/{library.stats['templates']} templates; "
          f"{len(model.plans)} frontier points; baselines complete={baselines['complete']}", flush=True)
    template_ids = {}
    templates = []
    entries = []
    for opt in library.options:
        identity = id(opt.lowered)
        if identity not in template_ids:
            template_ids[identity] = len(templates)
            templates.append({"program": opt.lowered.candidate.program.to_dict(),
                              "candidate": opt.lowered.candidate.to_dict(), "lowering": opt.lowered.to_dict()})
        entries.append({**opt.summary(), "template": template_ids[identity]})
    library_path = output / f"{program.id}-library.json.gz"
    dump(library_path, {"program": program.to_dict(), "options": entries, "templates": templates,
                        "precision_policy": config["precision_policy"], "total_error": config["total_error"]})
    families = {"proposed": model.plans, **baselines["frontiers"], "base_hwp": base_plans(library, max_a)}
    plans = {}
    for family, values in families.items():
        for plan in values:
            plans.setdefault(plan.waves, {"plan": plan, "families": []})["families"].append(family)
    records, artifacts = [], []
    emission_seconds = optimization_seconds = 0.0
    adapter = PyZXAdapter(seed=config["seed"])
    for number, item in enumerate(plans.values()):
        started = time.perf_counter()
        lowered, proof = emit(library, item["plan"], memory_cap_bytes=256 * 1024)
        emission_seconds += time.perf_counter() - started
        resource_before = estimate_resources(lowered)
        measured = (resource_before.t_count, resource_before.t_depth, resource_before.peak_workspace)
        record = {"id": f"p{number}", "families": sorted(set(item["families"])),
                  "model": item["plan"].resources, "waves": item["plan"].waves,
                  "emitted": measured, "post": measured, "verification": proof["status"],
                  "cliffords": resource_before.clifford_count}
        artifact = {"id": record["id"], "program": program.to_dict(),
                    "candidate": lowered.candidate.to_dict(), "lowering": lowered.to_dict(),
                    "verification": proof, "resources": resource_before.to_dict()}
        started = time.perf_counter()
        result = adapter.optimize(lowered, config["optimization"]["action"],
                                  timeout_seconds=config["optimization"]["seconds"])
        record["optimization_status"] = result.status
        if result.lowered is not None and result.status == "verified":
            post_proof = verify_optimized_lowered_circuit(
                lowered, result.lowered, config["total_error"], memory_cap_bytes=256 * 1024,
                timeout_seconds=config["optimization"]["verification_seconds"])
            record["post_verification"] = post_proof.status
            if post_proof.status.startswith("verified_lowered_"):
                r = estimate_resources(result.lowered)
                record["optimized"] = (r.t_count, r.t_depth, r.peak_workspace)
                # Keep both endpoints: a rewrite can exchange T for depth.
                record["post"] = record["optimized"]
                artifact["optimized"] = {"lowering": result.lowered.to_dict(),
                                          "verification": post_proof.to_dict(), "resources": r.to_dict()}
        else:
            record["optimization_reason"] = result.reason
        optimization_seconds += time.perf_counter() - started
        artifacts.append(artifact)
        records.append(record)
        if (number + 1) % 10 == 0:
            print(f"{program.id}: verified/optimized {number+1}/{len(plans)} circuits", flush=True)
    artifact_path = output / f"{program.id}-circuits.json.gz"
    dump(artifact_path, artifacts)
    family_points = {}
    for family in families:
        subset = [r for r in records if family in r["families"]]
        # Post frontier includes each unoptimized parent and every verified child.
        post = [{**r, "post": r["emitted"]} for r in subset] + [r for r in subset if "optimized" in r]
        family_points[family] = {"model": sorted({tuple(p.resources) for p in families[family]}),
                                "emitted": sorted({tuple(r["emitted"]) for r in nondominated_records(subset, "emitted")}),
                                "post": sorted({tuple(r["post"]) for r in nondominated_records(post, "post")})}
    comparisons = {}
    for stage in ["model", "emitted", "post"]:
        references = [p for family in ("direct", "uniform", "per_group", "base_hwp")
                      for p in family_points[family][stage]]
        comparisons[stage] = compare(family_points["proposed"][stage], references,
                                     config["ancilla_caps"], config["depth_caps"])
    model_reference = [p for f in ("direct", "uniform", "per_group") for p in family_points[f]["model"]]
    novel = [p for p in family_points["proposed"]["model"]
             if not any(all(x <= y for x, y in zip(r, p)) for r in model_reference)]
    summary = {"case": program.id, "program": program.to_dict(), "library": library.stats,
               "solver_status": model.status, "model_complete": model.complete, "search": model.stats,
               "baseline_complete": baselines["complete"], "baseline_partitions": baselines["partitions"],
               "baseline_seconds": baselines["seconds"], "emission_seconds": emission_seconds,
               "optimization_seconds": optimization_seconds, "peak_process_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               "family_points": family_points, "comparisons": comparisons, "new_model_points": novel,
               "records": records, "library_artifact": str(library_path.relative_to(ROOT)),
               "circuit_artifact": str(artifact_path.relative_to(ROOT)),
               "artifact_sha256": {library_path.name: sha(library_path), artifact_path.name: sha(artifact_path)}}
    dump(output / f"{program.id}-summary.json", summary)
    print(f"{program.id}: done; {len(novel)} new model points", flush=True)
    return summary


def render_report(summary, config):
    lines = ["# HWP Pareto Synthesis Study", "", "Development evidence; deterministic unitary Clifford+T only.", "",
             f"Source fingerprint: `{summary['source_fingerprint']}`. Config SHA-256: `{summary['config_sha256']}`.",
             "", "Exactness is restricted to all compatible subsets up to the declared batch cap, fixed normalized-term error budgets, and complete-block waves. Every reported circuit was emitted and checked. Measurement-assisted, catalytic, and accumulated-weight HWP are not in this library.",
             "", "## Construction audit", "",
             "Direct singleton phases and the existing staged-compressor in-place/copied HWP constructors are reused. Sources: Kivlichan et al., arXiv:1902.10673v4 Appendix A.1; the exact unitary Toffoli template uses Amy et al., arXiv:1206.0758v4. Appendix A.2 accumulation is a different construction requiring recomputation/addition and explicit unitary cleanup; it is deferred, not represented by published measured costs.",
             "", "## Coverage and cost", "",
             "| Case | Options / templates | Exact points | New model points | Search s | Baseline s | Library s | Postprocessing s |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for c in summary["cases"]:
        lines.append(f"| {c['case']} | {c['library']['options']} / {c['library']['templates']} | {len(c['family_points']['proposed']['model'])} | {len(c['new_model_points'])} | {c['search']['seconds']:.3f} | {c['baseline_seconds']:.3f} | {c['library']['seconds']:.3f} | {c['optimization_seconds']:.3f} |")
    lines += ["", "## Constrained comparisons", "", "Baseline = union of direct, best uniform cap, best per-group cap/layout, and existing HWP reference. Uniform/per-group baselines enumerate subset memberships, balanced and full-plus-remainder batches, direct fallback per batch, automatic eligible layouts or fixed layouts, and exact wave schedules. The base reference uses its existing serial batch emission, with the same per-block precision allocation. All parents and verified PyZX children remain available after optimization.",
              "", f"Ancilla caps: `{config['ancilla_caps']}`. Depth caps: `{config['depth_caps']}`. Counts below are grid queries, not independent experimental samples. T ties may still differ in depth or workspace.",
              "", "| Case | Stage | T wins | Newly feasible | T ties | T losses / proposed infeasible | Both infeasible |", "|---|---|---:|---:|---:|---:|---:|"]
    for c in summary["cases"]:
        for stage, rows in c["comparisons"].items():
            counts = {name: sum(r['outcome'] == name for r in rows) for name in ['T_win','newly_feasible','T_tie','T_loss','proposed_infeasible','both_infeasible']}
            lines.append(f"| {c['case']} | {stage} | {counts['T_win']} | {counts['newly_feasible']} | {counts['T_tie']} | {counts['T_loss'] + counts['proposed_infeasible']} | {counts['both_infeasible']} |")
    figure = ROOT / "reports/hwp-pareto-frontier.png"
    if figure.exists():
        lines += ["", "![Model frontier at fixed ancilla caps](hwp-pareto-frontier.png)"]
    lines += ["", "## Exact model frontiers", "", "Each tuple is `(T, wave T-depth, clean ancillas)`. Circuit IDs and schedules are in the compact result JSON; full existing-schema circuit/rotation evidence is in the compressed raw artifacts.", ""]
    for c in summary["cases"]:
        lines += [f"### {c['case']}", "", f"Status: `{c['solver_status']}`; baseline enumeration complete: `{c['baseline_complete']}`.", "", f"`{c['family_points']['proposed']['model']}`", ""]
    candidates = [(c, r) for c in summary['cases'] for r in c['records'] if 'proposed' in r['families'] and tuple(r['model']) in [tuple(p) for p in c['new_model_points']]]
    if not candidates:
        candidates = [(c, r) for c in summary['cases'] for r in c['records'] if 'proposed' in r['families'] and r['model'][2] > 0]
    if candidates:
        c, r = candidates[0]
        lines += ["## Explanatory witness", "", f"Case `{c['case']}`, circuit `{r['id']}`: model `{r['model']}`, emitted `{r['emitted']}`, optimized child `{r.get('optimized', 'unavailable')}`.", "", f"Waves of library option IDs: `{r['waves']}`. Full replayable witness: `results/hwp-pareto-witness.json`.", ""]
        with gzip.open(ROOT / c['library_artifact'], "rt") as f:
            library = json.load(f)
        with gzip.open(ROOT / c['circuit_artifact'], "rt") as f:
            artifact = next(a for a in json.load(f) if a['id'] == r['id'])
        lines += ["| Wave | Option | Parity masks | Construction | `(T,D,A)` | Scratch wires |", "|---:|---:|---|---|---|---|"]
        for w, ids in enumerate(r['waves']):
            for j, opt_id in enumerate(ids):
                opt = library['options'][opt_id]
                terms = [t.mask for i, t in enumerate(preprocess(PhaseProgram.from_dict(c['program'])).terms) if opt['terms'] >> i & 1]
                scratch = artifact['candidate']['parameters']['wave_schedule'][w]['blocks'][j]['scratch']
                lines.append(f"| {w+1} | {opt_id} | {terms} | {opt['layout']} | {opt['resources']} | {scratch} |")
        lines += ["", "The schedule reserves each block for a complete wave; scratch wire IDs repeat only after certified cleanup. The optimized child remains optional if its depth exceeds a query's limit.", ""]
        for query in c['comparisons']['model']:
            if query['proposed'] == r['model'] and query['outcome'] == 'T_win':
                lines += [f"At A <= {query['ancilla_cap']} and D <= {query['depth_cap']}, the best combined reference is `{query['baseline']}` and this circuit saves {query['delta_T']} T gates. All selected blocks share the same total error policy.", ""]
                break
        dump(ROOT / 'results/hwp-pareto-witness.json', {"case": c['case'], "record": r,
             "artifact": artifact, "options": [library['options'][i] for wave in r['waves'] for i in wave]})
    total_new = sum(len(c['new_model_points']) for c in summary['cases'])
    lines += ["## Interpretation and limits", "",
              f"The exact model contains {total_new} points not weakly dominated by the combined uniform/per-group references across this fixed study. This is a model-relative observation, not a published-method frontier or held-out result.",
              "", "An initial diagnostic forced HWP on every baseline batch and reported eight new model points. Allowing direct fallback removes seven of those points; that superseded run is preserved privately under `results/raw/hwp-pareto-study-initial-baseline/`. Those seven are baseline artifacts, not synthesis gains. The final baseline also permits automatic per-batch in-place/copied layout selection.",
              "", "Model-dominated reconstructions and resource-tied alternatives are discarded before whole-circuit optimization. Consequently, emitted and post-optimization frontiers are candidate frontiers, not exact optima. They can lose to a baseline whose particular reconstruction was retained. Wave barriers may overestimate unconstrained emitted depth.",
              "", "All data are development cases. Equal-angle native wires reuse compact templates, but subset DP remains exponential; the study measures its behavior through eight terms and does not claim large-instance scalability. Peak RSS in the JSON is the cumulative process peak, not per-case exclusive memory. Synthesis cache state is recorded; first-run and warm-cache timings differ.",
              "", "The study includes infeasible queries and no-gain cases. No heuristic is inferred from a single witness. Further work should first explain any repeatable gain and check whether it survives a stronger construction library and matched physical assumptions.",
              "", "## Reproduce", "", "```bash", "python scripts/run_hwp_pareto.py --config configs/hwp-pareto-study.yaml --plot", "python scripts/run_hwp_pareto.py --config configs/hwp-pareto-study.yaml --verify", "```", "", "Plotting requires the optional `study` dependency extra. The tracked summary stores frontier points and query counts; complete grid records and circuits remain in the raw artifact directory.", "",
              "The runner checkpoints each case. `--resume` checks the config/source fingerprint before reusing checkpoints; output circuits are never treated as feasible without verification in the original run."]
    return '\n'.join(lines) + '\n'


def render_plot(summary):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = ["native_5", "native_8", "overlapping_6"]
    fig, axes = plt.subplots(len(names), 2, figsize=(10, 10), constrained_layout=True)
    for row, name in enumerate(names):
        case = next(c for c in summary['cases'] if c['case'] == name)
        for col, cap in enumerate([1, 3]):
            ax = axes[row, col]
            for family, marker, color, label in [("per_group", "o", "#b55b37", "Strong per-group baseline"),
                                                  ("proposed", "x", "#2166ac", "Exact model")]:
                points = [p for p in case['family_points'][family]['model'] if p[2] <= cap]
                # Project at the fixed budget and remove dominated projections.
                points = [p for p in points if not any(q[0] <= p[0] and q[1] <= p[1]
                           and (q[0], q[1]) != (p[0], p[1]) for q in points)]
                ax.scatter([p[1] for p in points], [p[0] for p in points], marker=marker,
                           color=color, s=90 if marker == 'o' else 60, alpha=.75, label=label,
                           facecolors='none' if marker == 'o' else color)
            ax.set(title=f"{name}: ancillas <= {cap}", xlabel="Wave T-depth", ylabel="T-count")
            ax.grid(alpha=.2)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Attainable model points under fixed workspace caps\nUnitary HWP, fixed error allocation; no convex interpolation")
    fig.savefig(ROOT / 'reports/hwp-pareto-frontier.png', dpi=160)
    plt.close(fig)


def verify_saved(config, config_path):
    summary = json.loads((ROOT / config['summary_path']).read_text())
    if sha(config_path) != summary['config_sha256']:
        raise ValueError("config checksum mismatch")
    for rel, digest in summary['source_hashes'].items():
        if sha(ROOT / rel) != digest:
            raise ValueError(f"source checksum mismatch: {rel}")
    roots = children = templates = 0
    for case in summary['cases']:
        for key in ['library_artifact', 'circuit_artifact']:
            path = ROOT / case[key]
            assert sha(path) == case['artifact_sha256'][path.name]
        with gzip.open(ROOT / case['library_artifact'], 'rt') as f:
            library = json.load(f)
        for template_index, entry in enumerate(library['templates']):
            program = PhaseProgram.from_dict(entry['program'])
            candidate = Candidate.from_dict(entry['candidate'], program)
            lowered = LoweredCircuit.from_dict(entry['lowering'], candidate)
            # The allowance is the template's full-circuit requested budget.
            opt = next(o for o in library['options'] if o['template'] == template_index)
            proof = verify_lowered_circuit(lowered, opt['allowance'], memory_cap_bytes=1)
            assert proof.status.startswith('verified_lowered_'), proof.message
            templates += 1
        with gzip.open(ROOT / case['circuit_artifact'], 'rt') as f:
            entries = json.load(f)
        for entry in entries:
            program = PhaseProgram.from_dict(entry['program'])
            candidate = Candidate.from_dict(entry['candidate'], program)
            lowered = LoweredCircuit.from_dict(entry['lowering'], candidate)
            proof = verify_lowered_circuit(lowered, config['total_error'], memory_cap_bytes=1)
            assert proof.status.startswith('verified_lowered_'), proof.message
            assert estimate_resources(lowered).to_dict() == entry['resources']
            roots += 1
            if 'optimized' in entry:
                child = LoweredCircuit.from_dict(entry['optimized']['lowering'], candidate)
                proof = verify_optimized_lowered_circuit(lowered, child, config['total_error'],
                                                       memory_cap_bytes=1, timeout_seconds=15)
                assert proof.status.startswith('verified_lowered_'), proof.message
                assert estimate_resources(child).to_dict() == entry['optimized']['resources']
                children += 1
        print(f"{case['case']}: saved evidence replayed", flush=True)
    witness = json.loads((ROOT / 'results/hwp-pareto-witness.json').read_text())
    case = next(c for c in summary['cases'] if c['case'] == witness['case'])
    with gzip.open(ROOT / case['circuit_artifact'], 'rt') as f:
        stored = next(e for e in json.load(f) if e['id'] == witness['record']['id'])
    assert stored == witness['artifact'], "witness differs from replayed circuit artifact"
    print(f"Verified {templates} templates, {roots} complete parents, {children} optimized children and the tracked witness.", flush=True)


def compact_summary(summary):
    """Keep detailed budget sweeps in raw checkpoints, not a large tracked table."""
    compact = {**summary, "cases": []}
    for case in summary['cases']:
        row = {k: v for k, v in case.items() if k != 'comparisons'}
        row['comparison_counts'] = {
            stage: {outcome: sum(r['outcome'] == outcome for r in queries)
                    for outcome in sorted({r['outcome'] for r in queries})}
            for stage, queries in case['comparisons'].items()}
        row['constrained_differences'] = {
            stage: [r for r in queries if r['outcome'] not in {'T_tie', 'both_infeasible'}]
            for stage, queries in case['comparisons'].items()}
        compact['cases'].append(row)
    return compact


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/hwp-pareto-study.yaml")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--plot", action="store_true", help="requires the study extra (matplotlib)")
    parser.add_argument("--verify", action="store_true", help="replay stored circuit evidence without running the study")
    args = parser.parse_args()
    config_path = ROOT / args.config
    config = yaml.safe_load(config_path.read_text())
    if config["model_profile"] != "unitary_clifford_t" or config["precision_policy"] != "normalized_term_blocks_v1":
        raise ValueError("unsupported study model")
    output = ROOT / config["results_dir"]
    output.mkdir(parents=True, exist_ok=True)
    source_paths = sorted((ROOT / 'src/collective_phase').rglob('*.py')) + [Path(__file__), ROOT / 'pyproject.toml']
    source_paths += [ROOT / c['manifest'] for c in config['cases'] if 'manifest' in c]
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in source_paths}
    fingerprint = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    if args.verify:
        verify_saved(config, config_path)
        return
    metadata = {"run_date": datetime.now(timezone.utc).isoformat(), "config_sha256": sha(config_path), "source_fingerprint": fingerprint,
                "source_hashes": hashes, "revision": subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                "versions": {p: importlib.metadata.version(p) for p in ['numpy','pyzx','pygridsynth','PyYAML']}}
    metadata_path = output / 'metadata.json'
    if args.resume and metadata_path.exists():
        old = json.loads(metadata_path.read_text())
        if any(old[k] != metadata[k] for k in ['config_sha256','source_fingerprint']):
            raise ValueError("resume fingerprint mismatch; rerun without --resume")
    cache = output / 'rotation-cache.json'
    metadata['warm_rotation_cache'] = cache.exists()
    dump(metadata_path, metadata)
    synth = RotationSynthesizer(cache, seed=config['seed'])
    results = []
    for case in config['cases']:
        checkpoint = output / f"{case['id']}-summary.json"
        if args.resume and checkpoint.exists():
            results.append(json.loads(checkpoint.read_text()))
        else:
            results.append(run_case(case, config, output, synth))
        summary = {**metadata, "cases": results}
        dump(ROOT / config['summary_path'], compact_summary(summary))
        (ROOT / config['report_path']).write_text(render_report(summary, config))
    if args.plot:
        render_plot(summary)
        (ROOT / config['report_path']).write_text(render_report(summary, config))
    print(f"Report: {config['report_path']}", flush=True)


if __name__ == '__main__':
    main()
