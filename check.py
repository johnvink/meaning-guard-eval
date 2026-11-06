#!/usr/bin/env python3
"""Reference checker for the meaning guard.

Usage: check.py cases.jsonl outputs.jsonl

outputs.jsonl has one {"raw": ..., "clean": ...} per line, in any order; cases are
matched on "raw". Each case is checked against its own must_keep / must_not_contain
and the generic rules in rules.md. Exit status is the number of failures that are
not marked "known" in the case.
"""
import json, re, sys
from difflib import SequenceMatcher

NEG = {"not", "never", "none", "nothing", "nobody", "neither", "nor", "without"}
UNITS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
LT_UNITS = ["nulis", "vienas", "du", "trys", "keturi", "penki", "šeši", "septyni", "aštuoni", "devyni", "dešimt", "vienuolika", "dvylika", "trylika", "keturiolika", "penkiolika", "šešiolika", "septyniolika", "aštuoniolika", "devyniolika"]
LT_FEM = {"viena": 1, "dvi": 2, "keturios": 4, "penkios": 5, "šešios": 6, "septynios": 7, "aštuonios": 8, "devynios": 9}
LT_TENS = {"dvidešimt": 20, "trisdešimt": 30, "keturiasdešimt": 40, "penkiasdešimt": 50, "šešiasdešimt": 60, "septyniasdešimt": 70, "aštuoniasdešimt": 80, "devyniasdešimt": 90}
WORDNUM = {w: i for i, w in enumerate(UNITS)} | {w: i for i, w in enumerate(LT_UNITS)} | LT_FEM
SCALE = {"hundred": 100, "thousand": 1000, "million": 1_000_000, "šimtas": 100, "šimtai": 100, "tūkstantis": 1000, "tūkstančiai": 1000}
MARKERS = ["no wait", "no,", "no ", "actually", "sorry", "i mean"]
MAX_CHANGE = 0.6


def words(text):
    out = []
    for w in re.sub(r"-", " ", text.lower()).split():
        w = w.strip(".,;:!?\"'()[]{}")
        w = re.sub(r"[^a-z0-9'ąčęėįšųūž]", "", w)
        if w:
            out.append(w)
    return out


def negations(text):
    n = 0
    for w in words(text):
        if w in NEG or w.endswith("n't") or w == "cannot":
            n += 1
    return n


def numbers(text):
    vals, cur, has = [], 0, False
    for w in words(text):
        if re.fullmatch(r"\d[\d,]*", w) or re.fullmatch(r"\d+[a-z]+", w):
            if has:
                vals.append(cur); cur, has = 0, False
            vals.append(int(re.sub(r"\D", "", w)))
        elif w in WORDNUM:
            if has and cur % 10 == 0 and cur % 100 < 100 and WORDNUM[w] < 10 and cur >= 20:
                cur += WORDNUM[w]
            elif has:
                vals.append(cur); cur = WORDNUM[w]
            else:
                cur, has = WORDNUM[w], True
        elif w in TENS or w in LT_TENS:
            t = TENS.get(w) or LT_TENS.get(w)
            if has and cur >= 100:
                cur += t
            elif has:
                vals.append(cur); cur = t
            else:
                cur, has = t, True
        elif w in SCALE and has:
            cur *= SCALE[w]
        elif w == "and" and has:
            continue
        else:
            if has:
                vals.append(cur); cur, has = 0, False
    if has:
        vals.append(cur)
    return vals


def code_tokens(text):
    toks = []
    for raw in text.split():
        t = raw.strip(".,;:!?\"'()[]{}")
        if not t or t[0].isdigit():
            continue
        if ("_" in t or "/" in t or re.search(r"[A-Za-z0-9][.\-][A-Za-z0-9]", t) or re.search(r"[a-z][A-Z]", t)
                or re.fullmatch(r"[A-Z]{2,}", t) or (re.search(r"[A-Za-z]", t) and re.search(r"\d", t))):
            toks.append(t)
    return toks


def exact(needle, hay):
    return re.search(r"(?<![A-Za-z0-9_])" + re.escape(needle) + r"(?![A-Za-z0-9_])", hay) is not None


def correction_word(raw):
    low = raw.lower()
    for m in MARKERS:
        i = low.find(" " + m)
        if i >= 0:
            rest = words(low[i + len(m) + 1:])
            rest = [w for w in rest if w not in ("wait", "no")]
            if rest:
                return rest[0]
    return None


def change_ratio(raw, clean):
    a, b = words(raw), words(clean)
    if not a:
        return 0.0
    same = sum(blk.size for blk in SequenceMatcher(None, a, b).get_matching_blocks())
    return 1 - same / len(a)


def check(case, clean, protected=()):
    raw = case["raw"]
    if re.match(r"\s*[\[{<`]", clean):
        return "markup instead of text"
    cw = correction_word(raw)
    if cw and cw not in words(clean):
        return f"dropped the correction '{cw}'"
    if negations(raw) != negations(clean):
        return "negation count changed"
    missing = [v for v in numbers(raw) if v not in numbers(clean)]
    if missing:
        return f"number {missing[0]} missing"
    for t in list(protected) + code_tokens(raw):
        if not exact(t, clean):
            return f"token '{t}' changed"
    if change_ratio(raw, clean) > MAX_CHANGE:
        return "rewrote most of the take"
    for k in case.get("must_keep", []):
        if k.lower() not in clean.lower():
            return f"must_keep '{k}' missing"
    for k in case.get("must_not_contain", []):
        if k.lower() in clean.lower():
            return f"must_not_contain '{k}' present"
    return None


def main():
    cases = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
    outs = {}
    for l in open(sys.argv[2], encoding="utf-8"):
        if l.strip():
            o = json.loads(l); outs[o["raw"]] = o["clean"]
    ok = fail = known = 0
    for c in cases:
        clean = outs.get(c["raw"])
        if clean is None:
            print(f"[missing] {c['raw']}"); fail += 1; continue
        why = check(c, clean, c.get("words", []))
        if why is None:
            ok += 1; print(f"[     ok] {c['raw']}  →  {clean}")
        elif c.get("known"):
            known += 1; print(f"[  known] {c['raw']}  →  {clean}   ({why})")
        else:
            fail += 1; print(f"[   FAIL] {c['raw']}  →  {clean}   ({why})")
    print(f"\n{ok} ok, {fail} failed, {known} known weaknesses of {len(cases)} cases")
    sys.exit(fail)


if __name__ == "__main__":
    main()
