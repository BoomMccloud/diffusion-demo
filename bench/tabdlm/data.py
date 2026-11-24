"""TabDLM source data (MIT), pinned to one commit, plus the fixed few-shot and held-out picks.

Few-shot rows come from train.csv and held-out inputs from test.csv, so they never overlap. Every
pick uses a fixed random seed, so both models see the same rows.
"""
import csv, functools, hashlib, random, urllib.request
from pathlib import Path

COMMIT = "91560d4f9fdb1ad380f0ae003d0a8704c6bbe877"
URL = "https://raw.githubusercontent.com/ilikevegetable/TabDLM/{commit}/data/tabular/{name}/{split}.csv"
NAMES = {"bio": "biography", "amazon": "rel_amazon"}
CACHE = Path(__file__).resolve().parent / ".data"

STAR_WORDS = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five"}


def path(ds, split):
    p = CACHE / f"{NAMES[ds]}-{split}-{COMMIT[:7]}.csv"
    if not p.exists():
        CACHE.mkdir(exist_ok=True)
        urllib.request.urlretrieve(URL.format(commit=COMMIT, name=NAMES[ds], split=split), p)
    return p


@functools.cache
def _rows(ds, split):
    return tuple(csv.DictReader(open(path(ds, split), newline="")))


def sources():
    """Source URL and sha256 of every file used, for the manifest."""
    out = {}
    for ds in NAMES:
        for split in ("train", "test"):
            p = path(ds, split)
            out[f"{ds}/{split}"] = {"url": URL.format(commit=COMMIT, name=NAMES[ds], split=split),
                                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "license": "MIT"}
    return out


def rows(ds, split):
    return list(_rows(ds, split))


def typed_amazon(r):
    """A row as the JSON the model is asked to produce: numbers and booleans, not CSV strings."""
    return {"price": float(r["price"]), "review_time": int(float(r["review_time"])),
            "rating": int(float(r["rating"])), "verified": r["verified"] == "True",
            "category": r["category"], "brand": r["brand"], "title": r["title"],
            "description": r["description"], "review_text": r["review_text"], "summary": r["summary"]}


def typed_bio(r):
    return {"age": int(r["age"]), "salary": int(r["salary"]), "sex": r["sex"],
            "birth_state": r["birth_state"], "college": r["college"], "degree": r["degree"],
            "occupation": r["occupation"], "biography": r["biography"]}


def star_summary(s):
    """The rating a "Five Stars"-style summary states, or None."""
    for n, w in STAR_WORDS.items():
        if s.strip().lower() in (f"{w.lower()} stars", f"{w.lower()} star"):
            return n
    return None


def amazon_fewshot():
    """One 5-, 3- and 1-star row with a review of at least 25 words and a summary that isn't "N Stars"."""
    pool = [r for r in rows("amazon", "train")
            if len(r["review_text"].split()) >= 25 and star_summary(r["summary"]) is None]
    rng = random.Random(0)
    return [typed_amazon(rng.choice([r for r in pool if int(float(r["rating"])) == k])) for k in (5, 3, 1)]


def bio_fewshot():
    return [typed_bio(r) for r in random.Random(0).sample(rows("bio", "train"), 3)]


def amazon_heldout(n):
    """Held-out rows stratified by rating, about n / 5 per star, so a majority guess can't look good."""
    test = rows("amazon", "test")
    rng = random.Random(1)
    out = []
    for k in (1, 2, 3, 4, 5):
        out += rng.sample([r for r in test if int(float(r["rating"])) == k], -(-n // 5))
    rng.shuffle(out)
    return [typed_amazon(r) for r in out[:n]]


def bio_heldout(n):
    return [typed_bio(r) for r in random.Random(1).sample(rows("bio", "test"), n)]


def amazon_real(n):
    """Unstratified held-out rows, scored as real data to show where the judge puts real records."""
    return [typed_amazon(r) for r in random.Random(2).sample(rows("amazon", "test"), n)]


def amazon_categories():
    """Top-level categories in train, most common first."""
    from collections import Counter
    return [c for c, _ in Counter(r["category"].split(" > ")[0] for r in rows("amazon", "train")).most_common()]


@functools.cache
def bio_values(field):
    return sorted({r[field] for r in rows("bio", "train")})
