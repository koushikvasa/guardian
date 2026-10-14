"""Offline experiment for the Arize scoreboard: catch rate, false alarms, per language.

Text-only (no detonation, no calls) so it runs in seconds. A message counts as "flagged" when the
verdict is suspicious or scam. Writes data/scoreboard.json, which GET /scoreboard serves.
If ARIZE_SPACE_ID + ARIZE_API_KEY are set, also uploads the dataset and logs an Arize AX experiment
(fallback: a Phoenix experiment when PHOENIX_COLLECTOR_ENDPOINT is set).

usage: python evals/run_eval.py [csv ...]   (default: evals/seed_messages.csv + evals/*.extra.csv)
"""
import csv, glob, json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import config, rules
from app.signals import extract

ROOT = Path(__file__).resolve().parent.parent


def predict(text: str) -> dict:
    s = extract(text)
    v = rules.evaluate(s, {"saved": False, "trusted": False}, _url_hint(s), 0, s.get("language", "en"))
    return {"label": v.label, "score": v.score, "flagged": v.label != "safe", "rules": [f["rule"] for f in v.fired]}


def _url_hint(s):
    # Without detonation, treat a brand mentioned + a link on a non-official domain as a mismatch hint.
    if s.get("brand") and s.get("urls"):
        u = s["urls"][0].lower()
        dom = u.replace("https://", "").replace("http://", "").split("/")[0]
        return {"brands": [s["brand"]], "final_domain": dom, "official_domain": False,
                "redirects": [], "shortener": s.get("shortener")}
    return None


def main(paths):
    rows = []
    for p in paths:
        with open(p, newline="", encoding="utf-8") as f:
            rows += list(csv.DictReader(f))
    t0 = time.time()
    res = []
    for r in rows:
        pr = predict(r["text"])
        res.append({**r, "truth": r["label"], "pred": pr["label"], "score": pr["score"], "flagged": pr["flagged"], "rules": pr["rules"]})
    def stats(sub):
        scams = [x for x in sub if x["truth"] == "scam"]; hams = [x for x in sub if x["truth"] == "ham"]
        return {"n": len(sub),
                "catch_rate": round(sum(x["flagged"] for x in scams) / max(1, len(scams)), 3),
                "false_alarm_rate": round(sum(x["flagged"] for x in hams) / max(1, len(hams)), 3)}
    board = {"generated_at": time.strftime("%Y-%m-%d %H:%M"), "overall": stats(res),
             "by_lang": {l: stats([x for x in res if x.get("lang") == l]) for l in sorted({x.get("lang") for x in res})},
             "ms_per_message": round((time.time() - t0) * 1000 / max(1, len(res)), 1)}
    (ROOT / "data" / "scoreboard.json").write_text(json.dumps(board, indent=2), encoding="utf-8")
    (ROOT / "data" / "eval_results.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(board, indent=2))
    misses = [x for x in res if (x["truth"] == "scam") != x["flagged"]]
    for m in misses:
        print(f"  MISS [{m['truth']} -> {m['pred']} {m['score']}] {m['text'][:90]}")
    if config.live(config.ARIZE_SPACE_ID, config.ARIZE_API_KEY):
        _arize(rows)
    elif config.live(config.PHOENIX_COLLECTOR_ENDPOINT):
        _phoenix(rows)


def _arize(rows):
    """Dataset + experiment in Arize AX. Task = the deterministic rules; evaluator = caught the scam / no false alarm."""
    try:
        import pandas as pd
        from arize import ArizeClient
        from arize.experiments import EvaluationResult

        client = ArizeClient(api_key=config.ARIZE_API_KEY)
        df = pd.DataFrame({
            "attributes.input.value": [r["text"] for r in rows],
            "attributes.output.value": [r["label"] for r in rows],
            "attributes.metadata": [{"lang": r.get("lang", ""), "source": r.get("source", "")} for r in rows],
        })
        ds = client.datasets.create(space=config.ARIZE_SPACE_ID, name=f"guardian-msgs-{int(time.time())}", examples=df)

        def task(input):
            return json.dumps(predict(input), ensure_ascii=False)

        def caught(output, dataset_output):  # arg names are fixed by the SDK: output, dataset_output, input, dataset_row, metadata
            out = json.loads(output)
            ok = out["flagged"] == (dataset_output == "scam")
            return EvaluationResult(score=float(ok), label="correct" if ok else ("missed" if dataset_output == "scam" else "false_alarm"),
                                    explanation=f"rules fired: {', '.join(out['rules']) or 'none'}")

        exp, _ = client.experiments.run(name=f"rules-v1-{time.strftime('%m%d-%H%M')}", dataset=ds.id, space=config.ARIZE_SPACE_ID,
                                        task=task, evaluators=[caught], concurrency=4, exit_on_error=False)
        print("Arize AX experiment logged:", getattr(exp, "id", exp))
    except Exception as e:
        print("Arize AX experiment skipped:", e)


def _phoenix(rows):
    try:
        import pandas as pd
        import phoenix as px
        from phoenix.experiments import run_experiment
        client = px.Client(endpoint=config.PHOENIX_COLLECTOR_ENDPOINT)
        ds = client.upload_dataset(dataframe=pd.DataFrame(rows), dataset_name=f"guardian-msgs-{int(time.time())}",
                                   input_keys=["text", "lang"], output_keys=["label"])
        def task(input):
            return predict(input["text"])
        def caught(output, expected):
            return float(output["flagged"] == (expected["label"] == "scam"))
        run_experiment(ds, task, evaluators=[caught], experiment_name="rules-v1")
        print("Phoenix experiment logged")
    except Exception as e:
        print("Phoenix experiment skipped:", e)


if __name__ == "__main__":
    paths = sys.argv[1:] or [str(ROOT / "evals" / "seed_messages.csv")] + glob.glob(str(ROOT / "evals" / "*.extra.csv"))
    main(paths)
