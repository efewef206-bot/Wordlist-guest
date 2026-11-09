#!/usr/bin/env python3
"""
pwprofiler.py — targeted wordlist generator (CUPP-style).
Use ONLY on accounts you own or are authorized to test.
No network calls. Stdlib only. Python 3.8+.
"""
import argparse, hashlib, itertools, re, sys, datetime

LEET = {"a":["a","@","4"],"b":["b","8"],"e":["e","3"],"g":["g","9"],
        "i":["i","1","!"],"l":["l","1"],"o":["o","0"],"s":["s","5","$"],
        "t":["t","7"]}
SUFFIX = ["123","1234","12345","123456","1","12","!","!!","@","1!",
          "123!","2025","2024","2023"]
PREFIX = ["1","123","the","my","!"]

def leet_variants(w, cap=16):
    opts = [LEET.get(c,[c]) for c in w.lower()]
    out, n = set(), 0
    for combo in itertools.product(*opts):
        out.add("".join(combo)); n += 1
        if n >= cap: break
    return out

def case_variants(w):
    v = {w.lower(), w.upper(), w.capitalize()}
    if len(w) > 1: v.add(w.title())
    return v

def dob_variants(s):
    out = set()
    for fmt in ("%Y-%m-%d","%d/%m/%Y","%m/%d/%Y","%Y%m%d","%d%m%Y","%m%d%Y"):
        try: dt = datetime.datetime.strptime(s, fmt)
        except ValueError: continue
        out |= {dt.strftime("%d%m%Y"), dt.strftime("%Y%m%d"), dt.strftime("%m%d%Y"),
                dt.strftime("%d%m%y"), dt.strftime("%y%m%d"), dt.strftime("%d%m"),
                dt.strftime("%m%d"), str(dt.year), str(dt.year)[2:]}
        break
    if not out: out.add(re.sub(r"\D","",s))
    return {x for x in out if x}

def build_tokens(a):
    t = set()
    for v in (a.first,a.last,a.middle,a.nick,a.partner,a.pet,
              a.company,a.city,a.hobby,a.extra):
        if v:
            for p in re.split(r"[\s,\-_]+", v):
                if p: t.add(p)
    if a.name:
        parts = [p for p in re.split(r"\s+", a.name.strip()) if p]
        t |= set(parts) | {"".join(parts), "".join(parts)[::-1]}
    if a.dob: t |= dob_variants(a.dob)
    return t

def make_seeds(tokens):
    seeds = set()
    for t in tokens:
        if t.isdigit(): seeds.add(t)
        else:
            for c in case_variants(t):
                seeds.add(c); seeds |= leet_variants(c, 8)
    return seeds

def rank(pw):
    pool = 0
    if re.search(r"[a-z]", pw): pool += 26
    if re.search(r"[A-Z]", pw): pool += 26
    if re.search(r"\d",    pw): pool += 10
    if re.search(r"[^\w]", pw): pool += 32
    return pool ** min(len(pw), 12)

def generate(a):
    seeds = make_seeds(build_tokens(a))
    if not seeds: sys.exit("No details supplied. Use --name / --nick / --dob ...")

    years   = [str(y) for y in range(a.year_end, a.year_start-1, -1)]
    digits  = [str(i) for i in range(100)]
    if a.extended: digits += [f"{i:03d}" for i in range(100,1000,10)]
    symbols = list("!@#$%&*?._-")
    suffixes = SUFFIX + years + digits + symbols
    if a.extended:
        suffixes += [d+s for d in digits[:100] for s in "!@#$"]

    out = set()
    def add(x):
        if a.min_len <= len(x) <= a.max_len: out.add(x)

    for s in seeds: add(s)
    for s in seeds:
        for suf in suffixes:
            add(s+suf)
            if len(out) >= a.limit: return sorted(out, key=rank)
    for s in seeds:
        for pre in PREFIX: add(pre+s)
    s_l = sorted(seeds)
    for i,x in enumerate(s_l):
        for y in s_l[:i]+s_l[i+1:]:
            for sep in ("","_",".","-"):
                add(x+sep+y)
                if len(out) >= a.limit: return sorted(out, key=rank)
    return sorted(out, key=rank)

def check_hash(cands, target, algo="md5"):
    h = getattr(hashlib, algo); t = target.lower().strip()
    for pw in cands:
        if h(pw.encode()).hexdigest() == t: return pw
    return None

def interactive():
    def ask(l): return input(f"{l:>12}: ").strip() or None
    return argparse.Namespace(
        name=ask("full name"), first=ask("first name"), last=ask("last name"),
        middle=ask("middle"), nick=ask("nickname"), partner=ask("partner"),
        pet=ask("pet"), company=ask("company"), city=ask("city"),
        hobby=ask("hobby"), extra=ask("other words"),
        dob=ask("DOB (YYYY-MM-DD)"),
        year_start=1970, year_end=2030, min_len=6, max_len=32,
        limit=500_000, extended=False, out="wordlist.txt",
        check_hash=None, hash_algo="md5")

def main():
    p = argparse.ArgumentParser(description="Targeted wordlist generator (authorized use only).")
    for flag in ("name","first","last","middle","nick","partner","pet",
                 "company","city","hobby","extra","dob"):
        p.add_argument(f"--{flag}")
    p.add_argument("--year-start", type=int, default=1970)
    p.add_argument("--year-end",   type=int, default=2030)
    p.add_argument("--min-len",    type=int, default=6)
    p.add_argument("--max-len",    type=int, default=32)
    p.add_argument("--limit",      type=int, default=500_000)
    p.add_argument("--extended",   action="store_true")
    p.add_argument("--out",        default="wordlist.txt")
    p.add_argument("--check-hash")
    p.add_argument("--hash-algo", default="md5", choices=["md5","sha1","sha256"])
    a = p.parse_args()

    if not any([a.name,a.first,a.last,a.nick,a.partner,a.pet,
                a.company,a.city,a.hobby,a.extra,a.dob]):
        a = interactive()

    pws = generate(a)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write("\n".join(pws))
    print(f"[+] {len(pws):,} candidates -> {a.out}")
    print("[i] weakest first:", pws[:5])

    if a.check_hash:
        hit = check_hash(pws, a.check_hash, a.hash_algo)
        print(f"[!!] FOUND: {hit!r}" if hit else "[ok] not in list")

if __name__ == "__main__":
    main()