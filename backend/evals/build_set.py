"""Turn a downloaded scam/ham dataset (e.g. the Telugu/English set from Hugging Face) into evals/hf.extra.csv.
usage: python evals/build_set.py path/to/file.csv --text-col text --label-col label --lang en --n 120
Label values containing 'spam' or 'scam' or '1' map to scam; everything else to ham."""
import argparse, csv, random
ap = argparse.ArgumentParser(); ap.add_argument("path"); ap.add_argument("--text-col", default="text")
ap.add_argument("--label-col", default="label"); ap.add_argument("--lang", default="en"); ap.add_argument("--n", type=int, default=120)
ap.add_argument("--out", default="evals/hf.extra.csv"); a = ap.parse_args()
rows = list(csv.DictReader(open(a.path, newline="", encoding="utf-8")))
random.seed(7); random.shuffle(rows)
out = [{"text": r[a.text_col].strip(), "label": "scam" if str(r[a.label_col]).lower() in ("spam", "scam", "1", "fraud") else "ham", "lang": a.lang}
       for r in rows if r.get(a.text_col)][: a.n]
with open(a.out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["text", "label", "lang"]); w.writeheader(); w.writerows(out)
print("wrote", len(out), "rows to", a.out)
