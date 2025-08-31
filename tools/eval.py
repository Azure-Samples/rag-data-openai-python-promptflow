import os, csv, argparse, json, time

RAG_API_URL = os.getenv("RAG_API_URL", "http://localhost:8000/ask")

def _ask_via_rest(q: str) -> str:
    import requests
    r = requests.post(RAG_API_URL, json={"question": q}, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data.get("answer") or data.get("output_text") or json.dumps(data)

def normalize(s: str) -> str: return (s or "").strip().lower()
def exact_match(p: str, g: str) -> float: return 1.0 if normalize(p)==normalize(g) and g else 0.0

def token_f1(p: str, g: str) -> float:
    P, G = normalize(p).split(), normalize(g).split()
    if not P and not G: return 1.0
    if not P or not G:  return 0.0
    common = set(P)&set(G)
    if not common: return 0.0
    prec = sum(w in G for w in P)/len(P)
    rec  = sum(w in P for w in G)/len(G)
    return 0.0 if prec+rec==0 else 2*prec*rec/(prec+rec)

def run_eval(rows):
    out = []
    for q,g in rows:
        try: pred = _ask_via_rest(q)
        except Exception as e: pred = f"[ERROR] {e}"
        em = exact_match(pred,g) if g else ""
        f1 = token_f1(pred,g) if g else ""
        print(f"Q: {q}
A: {pred}
EM: {em}  F1: {f1}
---")
        out.append((q,pred,g,em,f1))
    with open("results.csv","w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["question","pred","gold","exact_match","f1"]); w.writerows(out)
    print(f"Saved results.csv (n={len(out)})")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--q", type=str)
    ap.add_argument("--file", type=str)
    a=ap.parse_args()
    if a.q: run_eval([(a.q,"")])
    elif a.file:
        with open(a.file,newline="",encoding="utf-8") as f:
            r=csv.DictReader(f)
            rows=[(d["question"], d.get("answer","")) for d in r]
        run_eval(rows)
    else: ap.error("Provide --q or --file")
if __name__=="__main__": main()
