"""Generate the chunking tables in evals/ABLATION.md from the ablation runs (plan step 2.9).

Run: python -m evals.make_ablation    (golden version from evals/golden/VERSION, dev split)

Which runs: MLflow runs tagged ablation=true for this golden version and split.
Which numbers: the results JSON each run points to (tag results_file), because the JSON is
the committed source of truth (D-036). If MLflow cannot be read, every results JSON of this
golden version and split is used instead, and the output says so.
Only the text between the two markers is rewritten; the hand-written notes around it stay.
"""

import json
from pathlib import Path

from evals.common import GOLDEN_VERSION, RESULTS_DIR

ABLATION_FILE = Path(__file__).resolve().parent / "ABLATION.md"
START = "<!-- make_ablation:start -->"
END = "<!-- make_ablation:end -->"
SPLIT = "dev"
METRICS = ("recall@1", "recall@3", "recall@5", "strict_recall@5", "mrr", "ndcg@5")
DOMAINS = ("docs", "learning", "interview")


def files_from_mlflow(golden_version: str, split: str) -> list[str]:
    """Result file names of the runs tagged ablation=true for this exam and split."""
    import mlflow  # imported here, so the JSON fallback works without MLflow

    from evals.tracking import EXPERIMENT_PREFIX, get_experiment_id

    experiment_id = get_experiment_id(EXPERIMENT_PREFIX + "retrieval")
    runs = mlflow.search_runs(
        experiment_ids=[experiment_id],
        filter_string=(
            f"tags.ablation = 'true' and tags.split = '{split}' "
            f"and params.golden_version = '{golden_version}'"
        ),
        output_format="list",
    )
    return sorted({run.data.tags["results_file"] for run in runs})


def load_records(names: list[str], results_dir: Path = RESULTS_DIR) -> list[dict]:
    """Read the named result files; a name with no file is reported, not hidden."""
    records = []
    for name in names:
        path = results_dir / name
        if not path.exists():
            print(f"warning: MLflow lists {name}, but the file is missing; skipped")
            continue
        records.append(json.loads(path.read_text(encoding="utf-8")))
    return records


def all_records(results_dir: Path = RESULTS_DIR) -> list[dict]:
    """Fallback: every retrieval result file, whatever its ablation tag."""
    paths = sorted(results_dir.glob("*_retrieval.json"))
    return [json.loads(path.read_text(encoding="utf-8")) for path in paths]


def latest_per_config(records: list[dict], golden_version: str, split: str) -> list[dict]:
    """One record per config id (the newest date), same exam and split only, sorted by id.

    Filtering again here means a row from another golden version can never slip in.
    """
    latest: dict[str, dict] = {}
    for record in records:
        settings = record["settings"]
        if settings.get("golden_version") != golden_version or record["split"] != split:
            continue
        current = latest.get(record["config_id"])
        if current is None or record["date"] > current["date"]:
            latest[record["config_id"]] = record
    return [latest[config_id] for config_id in sorted(latest)]


def best_values(records: list[dict], group: str = "overall") -> dict[str, float]:
    """The highest value of each metric, so the table can bold it (ties: all bold)."""
    return {name: max(r[group][name] for r in records) for name in METRICS}


def cell(value: float, best: float) -> str:
    text = f"{value:.3f}"
    return f"**{text}**" if value == best else text


def recipe(settings: dict) -> tuple[str, str, str]:
    """(strategy, size, cleaned / includes) in words, read from the collection manifest."""
    strategy = settings.get("chunk_strategy", "n/a")
    if "base_strategy" in settings:
        strategy += f" on {settings['base_strategy']}"
    size = f"{settings.get('chunk_size', 'n/a')}/{settings.get('chunk_overlap', 'n/a')}"
    size += f" {settings.get('chunk_unit', '')}".rstrip()
    if "parent_max_tokens" in settings:
        size += f", parents <= {settings['parent_max_tokens']}"
    flags = f"{yes_no(settings.get('cleaned'))} / {yes_no(settings.get('includes'))}"
    return strategy, size, flags


def yes_no(flag: bool | None) -> str:
    """True/False as words; None (an old manifest without the field) as n/a."""
    return "n/a" if flag is None else ("yes" if flag else "no")


def main_table(records: list[dict]) -> list[str]:
    best = best_values(records)
    lines = [
        "| Config | Strategy | Size / overlap | Clean / incl. | Chunks | Ingest s | R@1 | R@3 "
        "| R@5 | strict R@5 | MRR | nDCG@5 | Search p50 / p95 ms | Result file (commit) |",
        "|---" * 14 + "|",
    ]
    for r in records:
        settings, latency = r["settings"], r["search_latency_ms"]
        strategy, size, flags = recipe(settings)
        scores = " | ".join(cell(r["overall"][name], best[name]) for name in METRICS)
        lines.append(
            f"| {r['config_id']} | {strategy} | {size} | {flags} "
            f"| {settings.get('chunk_count', 'n/a')} | {settings.get('ingest_seconds', 'n/a')} "
            f"| {scores} | {latency['p50']} / {latency['p95']} "
            f"| `{r['date']}_{r['config_id']}_{r['split']}_retrieval.json` (`{r['git_commit']}`) |"
        )
    return lines


def per_type_table(records: list[dict]) -> list[str]:
    """Recall@5 per question type: code questions may favour a different strategy."""
    types = sorted({name for r in records for name in r["per_type"]})
    sizes = {name: max(r["per_type"].get(name, {}).get("n", 0) for r in records) for name in types}
    lines = [
        "| Config | " + " | ".join(f"{name} (n={sizes[name]})" for name in types) + " |",
        "|---" * (len(types) + 1) + "|",
    ]
    for r in records:
        values = [r["per_type"].get(name) for name in types]
        cells = [f"{v['recall@5']:.3f}" if v else "n/a" for v in values]
        lines.append(f"| {r['config_id']} | " + " | ".join(cells) + " |")
    return lines


def per_domain_table(records: list[dict]) -> list[str]:
    """Recall@5 / MRR per domain (D-030): a per-domain winner may justify mixed strategies."""
    sizes = {d: max(r["per_domain"].get(d, {}).get("n", 0) for r in records) for d in DOMAINS}
    lines = [
        "| Config | " + " | ".join(f"{d} (n={sizes[d]}) R@5 / MRR" for d in DOMAINS) + " |",
        "|---" * (len(DOMAINS) + 1) + "|",
    ]
    for r in records:
        values = [r["per_domain"].get(d) for d in DOMAINS]
        cells = [f"{v['recall@5']:.3f} / {v['mrr']:.3f}" if v else "n/a" for v in values]
        lines.append(f"| {r['config_id']} | " + " | ".join(cells) + " |")
    return lines


def render(records: list[dict], source: str) -> str:
    """The whole generated block: a header line and the three tables."""
    n = records[0]["overall"]["n"]
    header = (
        f"Generated by `python -m evals.make_ablation` from {source}. Golden {GOLDEN_VERSION}, "
        f"{SPLIT}, n={n} answerable questions: 1 question = {1 / n:.3f}, so gaps of 1-2 "
        "questions are ties. **Bold** = best in the column. Do not edit by hand."
    )
    parts = [
        header,
        "**Main table**",
        "\n".join(main_table(records)),
        "**Recall@5 per question type** (small n: read as a list of questions to open)",
        "\n".join(per_type_table(records)),
        "**Recall@5 / MRR per domain**",
        "\n".join(per_domain_table(records)),
    ]
    return "\n\n".join(parts)


def replace_block(text: str, block: str) -> str:
    """Swap what sits between the markers; fail loudly if they are missing."""
    if START not in text or END not in text:
        raise ValueError(f"markers {START} / {END} not found in {ABLATION_FILE.name}")
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    return f"{before}{START}\n{block}\n{END}{after}"


def main() -> None:
    try:
        records = load_records(files_from_mlflow(GOLDEN_VERSION, SPLIT))
        source = "the MLflow runs tagged ablation=true"
    except Exception as error:  # noqa: BLE001 - any MLflow failure means: use the files
        print(f"warning: MLflow not readable ({error}); using all result files instead")
        records, source = all_records(), "all result files (MLflow unavailable)"
    rows = latest_per_config(records, GOLDEN_VERSION, SPLIT)
    if not rows:
        raise SystemExit(f"no ablation runs for golden {GOLDEN_VERSION}, {SPLIT}")
    text = ABLATION_FILE.read_text(encoding="utf-8")
    ABLATION_FILE.write_text(replace_block(text, render(rows, source)), encoding="utf-8")
    names = ", ".join(r["config_id"] for r in rows)
    print(f"{ABLATION_FILE.name}: {len(rows)} configs written ({names})")


if __name__ == "__main__":
    main()
