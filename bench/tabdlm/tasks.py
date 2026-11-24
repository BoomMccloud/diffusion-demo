"""Prompts, parsing, deterministic checks, the Amazon judge prompt and the no-model floors.

Cells are (dataset, setting): `gen1` and `gen10` ask for 1 or 10 new records (Setting A), `extract`
asks for the structured fields of one held-out description (Setting B).

Parsing strips a code fence or text around the JSON and nothing else. `raw_json_ok` records whether
the output was bare JSON before that.
"""
import json, re

from . import data

DATASETS = ("amazon", "bio")
SETTINGS = ("gen1", "gen10", "extract")
N_RECORDS = {"gen1": 1, "gen10": 10, "extract": 1}

# ---------- schemas shown to the model

AMAZON_SCHEMA = """Fields:
- price: number, list price in USD, 0 to 1000
- review_time: integer, days since a fixed reference date, 0 to 3000
- rating: integer star rating, 1 to 5
- verified: boolean, whether the reviewer bought the book on Amazon
- category: string, the Amazon Books category path, "Top level > Subcategory"
- brand: string, the author or publisher as the store lists it
- title: string, the book title
- description: string, the store description
- review_text: string, the customer review
- summary: string, the review headline"""

BIO_SCHEMA = f"""Fields:
- age: integer, 21 to 70
- salary: integer, annual salary in thousands of USD (75 means $75,000)
- sex: "male" or "female"
- birth_state: lowercase US state
- college: lowercase college name
- degree: one of {", ".join(data.bio_values("degree"))}
- occupation: one of {", ".join(data.bio_values("occupation"))}
- biography: 3 to 6 sentences of natural prose about the person. It must state the exact age, the exact
  salary, the birth state, the college, the degree and the occupation, and refer to the person with
  pronouns that match the sex. Write each biography in your own words, not from a fixed template."""

# The TabDLM biographies are one fill-in template, so the generation examples carry these hand-written
# free-form biographies instead. Their attributes are the train rows picked in data.bio_fewshot().
BIO_FREEFORM = [
    "At 37, she has spent most of her working life making things people look at: she is a creative "
    "content professional who writes and edits campaigns for regional brands. She grew up in georgia "
    "and earned a bachelor degree at houston community college. Her work now pays $116,000 a year.",
    "He is a 28-year-old software developer who builds payment services for a mid-sized retailer. "
    "Born in california, he studied at arizona state university and finished a bachelor degree there. "
    "He earns $122,000 a year and still codes side projects on weekends.",
    "Originally from washington, he moved south for school and took a bachelor degree at houston "
    "community college. He is 31 now and works as a creative content professional, producing video for "
    "nonprofits. His salary is $125,000.",
]

# ---------- prompts

AMAZON_GEN = """You generate synthetic Amazon book review records for a dataset. Each record is one book listing with one customer review.

{schema}

Every field must agree with the others: the rating must fit the review's sentiment, the summary must fit the review, and the title, category, description and review must be about the same book. Make the records new and realistic. Do not copy the examples.

Examples:
{examples}

{ask}"""

BIO_GEN = """You generate synthetic person records for a dataset. Each record is a set of attributes and a biography that describes them.

{schema}

The biography must agree with every attribute. Make the records new and realistic. Do not copy the examples.

Examples:
{examples}

{ask}"""

ASK = {"gen1": "Generate 1 new record. Output only the JSON object, with no other text.",
       "gen10": "Generate 10 new records, all different from each other. Output only a JSON array of "
                "10 objects, with no other text."}

AMAZON_EXTRACT = """Read a book listing and its customer review, then give the review's star rating and the book's top-level Amazon category.

Output a JSON object with:
- rating: integer, 1 to 5
- category: one of {categories}

Examples:
{examples}

Listing and review:
{item}

Output only the JSON object, with no other text."""

BIO_EXTRACT = """Read a short biography and fill in the person's attributes.

Output a JSON object with:
- age: integer. The biography gives a career stage, not an exact age. The stages are early (21 to 30), career-building (31 to 40), established (41 to 50), advanced (51 to 60) and late (61 to 70). Give an age in the stated stage.
- salary: integer, annual salary in thousands of USD. The biography gives an income level: comfortable (up to 100), professional (101 to 150) or high-level (151 and up). Give a salary in the stated level.
- sex: "male" or "female"
- birth_state, college: lowercase, as written in the biography
- degree: one of {degrees}
- occupation: one of {occupations}

Examples:
{examples}

Biography:
{item}

Output only the JSON object, with no other text."""


def _j(x):
    return json.dumps(x, ensure_ascii=False)


def amazon_item(r):
    return f"Title: {r['title']}\nDescription: {r['description']}\nReview: {r['review_text']}"


def amazon_label(r):
    return {"rating": r["rating"], "category": r["category"].split(" > ")[0]}


BIO_FIELDS = ("age", "salary", "sex", "birth_state", "college", "degree", "occupation")


def bio_label(r):
    return {k: r[k] for k in BIO_FIELDS}


def prompt(ds, setting, item=None):
    if ds == "amazon" and setting != "extract":
        ex = "\n".join(_j(r) for r in data.amazon_fewshot())
        return AMAZON_GEN.format(schema=AMAZON_SCHEMA, examples=ex, ask=ASK[setting])
    if ds == "bio" and setting != "extract":
        ex = "\n".join(_j({**r, "biography": b}) for r, b in zip(data.bio_fewshot(), BIO_FREEFORM))
        return BIO_GEN.format(schema=BIO_SCHEMA, examples=ex, ask=ASK[setting])
    if ds == "amazon":
        ex = "\n\n".join(f"Listing and review:\n{amazon_item(r)}\nOutput: {_j(amazon_label(r))}"
                         for r in data.amazon_fewshot())
        return AMAZON_EXTRACT.format(categories=", ".join(data.amazon_categories()), examples=ex,
                                     item=amazon_item(item))
    ex = "\n\n".join(f"Biography:\n{r['biography']}\nOutput: {_j(bio_label(r))}" for r in data.bio_fewshot())
    return BIO_EXTRACT.format(degrees=", ".join(data.bio_values("degree")),
                              occupations=", ".join(data.bio_values("occupation")), examples=ex, item=item["biography"])


# ---------- parsing

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def parse(setting, raw):
    """Returns (records or None, raw_json_ok, reason). gen10 must be an array, the others an object."""
    t = (raw or "").strip()
    try:
        obj, raw_ok = json.loads(t), True
    except json.JSONDecodeError:
        raw_ok = False
        m = _FENCE.search(t)
        body = m.group(1) if m else t
        start = min([i for i in (body.find("{"), body.find("[")) if i >= 0], default=-1)
        if start < 0:
            return None, False, "no json"
        try:
            obj, _ = json.JSONDecoder().raw_decode(body[start:])
        except json.JSONDecodeError:
            return None, False, "bad json"
    if setting == "gen10":
        if not isinstance(obj, list) or not all(isinstance(x, dict) for x in obj):
            return None, raw_ok, "not an array of objects"
        return obj, raw_ok, None
    if isinstance(obj, list) and len(obj) == 1 and isinstance(obj[0], dict):
        obj = obj[0]
    if not isinstance(obj, dict):
        return None, raw_ok, "not an object"
    return [obj], raw_ok, None


# ---------- shared text matching (ported from TabDLM eval/bio_match_score.py)

def _norm(s):
    return re.sub(r"\s+", " ", str(s).strip()).lower()


def _words(s):
    return re.findall(r"[a-z0-9]+", _norm(s))


def hit_field(text, value):
    """TabDLM's rule: a substring hit, or for multi-word values enough of the words."""
    if _norm(value) and _norm(value) in _norm(text):
        return True
    toks = _words(value)
    if len(toks) <= 1:
        return False
    have = set(_words(text))
    common = sum(t in have for t in toks)
    need = 1.0 if len(toks) == 2 else 0.6
    return common >= 2 and common / len(toks) >= need


def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool) or isinstance(x, float) and x.is_integer()


# ---------- ProfileBio Setting A: schema and free-form biography checks

BIO_CHECKS = ("age", "salary", "pronoun", "birth_state", "college", "degree", "occupation")
_AGE_MENTION = re.compile(r"\b(\d{1,3})(?:-| )years?(?:-| )old\b|\baged? (\d{1,3})\b|\bat (\d{1,3}),", re.I)
_MONEY = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(k|thousand)?\b|\b(\d+(?:\.\d+)?)\s*(k|thousand)\b", re.I)


def bio_schema(r):
    if not _is_int(r.get("age")) or not 18 <= r["age"] <= 100:
        return "age"
    if not _is_int(r.get("salary")) or not 1 <= r["salary"] <= 1000:
        return "salary"
    if r.get("sex") not in ("male", "female"):
        return "sex"
    if r.get("degree") not in data.bio_values("degree"):
        return "degree"
    if r.get("occupation") not in data.bio_values("occupation"):
        return "occupation"
    for k in ("birth_state", "college", "biography"):
        if not isinstance(r.get(k), str) or not r[k].strip():
            return k
    return None


def salaries_in(text):
    """Dollar amounts in the text, in thousands."""
    out = []
    for m in _MONEY.finditer(text):
        num, unit = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        v = float(num.replace(",", ""))
        out.append(v if unit else v / 1000 if v >= 1000 else v)
    return out


def bio_checks(r):
    """Pass or fail per check. Age and salary must be stated exactly, with no conflicting value."""
    bio = r["biography"]
    ages = [int(next(g for g in m.groups() if g)) for m in _AGE_MENTION.finditer(bio)]
    age_ok = (set(ages) == {r["age"]}) if ages else bool(re.search(rf"\b{r['age']}\b", bio))
    sal = salaries_in(bio)
    b = _norm(bio)
    he = bool(re.search(r"\b(he|him|his)\b", b))
    she = bool(re.search(r"\b(she|her|hers)\b", b))
    pron = (he and not she) if r["sex"] == "male" else (she and not he)
    return {"age": age_ok, "salary": bool(sal) and all(abs(v - r["salary"]) < 0.5 for v in sal),
            "pronoun": pron, **{k: hit_field(bio, r[k]) for k in ("birth_state", "college", "degree", "occupation")}}


def bio_key(r):
    return tuple(str(r.get(k)).lower() for k in BIO_FIELDS)


def bio_opening(r):
    return " ".join(_words(r["biography"])[:5])


# ---------- Amazon Setting A: schema and deterministic checks (the judge does the rest)

def amazon_schema(r):
    if not isinstance(r.get("price"), (int, float)) or isinstance(r["price"], bool) or not 0 <= r["price"] <= 1000:
        return "price"
    if not _is_int(r.get("review_time")) or not 0 <= r["review_time"] <= 3000:
        return "review_time"
    if not _is_int(r.get("rating")) or not 1 <= r["rating"] <= 5:
        return "rating"
    if not isinstance(r.get("verified"), bool):
        return "verified"
    for k in ("category", "brand", "title", "review_text", "summary"):
        if not isinstance(r.get(k), str) or not r[k].strip():
            return k
    if not isinstance(r.get("description"), str):
        return "description"
    return None


def amazon_checks(r):
    stars = data.star_summary(r["summary"])
    return {"star_summary": stars is None or stars == int(r["rating"])}


def amazon_key(r):
    return _norm(r["title"])


def copied(ds, r):
    """Same title (Amazon) or the same attributes or biography (ProfileBio) as a few-shot example."""
    if ds == "amazon":
        return any(amazon_key(r) == amazon_key(f) or _norm(r["review_text"]) == _norm(f["review_text"])
                   for f in data.amazon_fewshot())
    return any(bio_key(r) == bio_key(f) or _norm(r["biography"]) == _norm(b)
               for f, b in zip(data.bio_fewshot(), BIO_FREEFORM))


JUDGE_AMAZON = """You check one synthetic Amazon book review record for internal consistency. Judge only whether the fields agree with each other, not whether the book exists.

Record:
{record}

Answer with a JSON object:
- rating_fits_review: true if the star rating fits the review's sentiment (1 to 2 negative, 3 mixed, 4 to 5 positive)
- summary_fits_review: true if the summary agrees with the review and the rating
- same_book: true if the title, category, description and review are about the same book, or the same kind of book
- no_contradiction: true if no field contradicts another, such as a review that names a different title or author, or a price or verified status the review disputes
- specific_claims: integer count of concrete statements in review_text about this book (plot, characters, content, condition), not counting generic praise or complaints
- reason: one sentence naming any problem"""

JUDGE_KEYS = ("rating_fits_review", "summary_fits_review", "same_book", "no_contradiction")


def judge_prompt(record):
    return JUDGE_AMAZON.format(record=_j(record))


def judge_ok(v):
    return bool(v) and "error" not in v and all(v.get(k) is True for k in JUDGE_KEYS)


# ---------- Setting B scoring

# TabDLM Bio-MR bins (tolerance 0). Ages in the data run 21 to 70.
AGE_BINS = [(21, 30), (31, 40), (41, 50), (51, 60), (61, 200)]
SALARY_BINS = [(0, 100), (101, 150), (151, 10_000)]


def _bin(v, bins):
    return next((i for i, (lo, hi) in enumerate(bins) if lo <= v <= hi), None)


def score_extract(ds, pred, gold):
    """Per-field correctness. A missing or malformed field is wrong."""
    p = pred or {}
    if ds == "amazon":
        rating = p.get("rating")
        ok_r = _is_int(rating)
        return {"rating": ok_r and int(rating) == gold["rating"],
                "rating_within_1": ok_r and abs(int(rating) - gold["rating"]) <= 1,
                "category": isinstance(p.get("category"), str)
                            and _norm(p["category"]) == _norm(gold["category"].split(" > ")[0])}
    out = {}
    for k, bins in (("age", AGE_BINS), ("salary", SALARY_BINS)):
        out[k] = _is_int(p.get(k)) and _bin(int(p[k]), bins) == _bin(gold[k], bins)
    for k in ("sex", "birth_state", "college", "degree", "occupation"):
        out[k] = isinstance(p.get(k), str) and _norm(p[k]) == _norm(gold[k])
    return out


# ---------- floors that use no model

_STAGE_AGE = {"early": 25, "career-building": 35, "established": 45, "advanced": 55, "late": 65}
_TEMPLATE = re.compile(
    r"This (?P<sex>male|female) individual is (?:in|at) the (?P<stage>[\w-]+)(?: career)? stage\. \w+ earns (?P<inc>.*?) income\. "
    r"\w+ was born in (?P<state>.*?) and completed higher education at (?P<college>.*?), earning an? "
    r"(?P<degree>\w+) degree\. \w+ works as an? (?P<occ>.*?)\.$")


def bio_regex_extract(bio):
    """Reads the template slots back out. ProfileBio Setting B is this easy for code."""
    m = _TEMPLATE.match(bio.strip())
    if not m:
        return {}
    inc = m["inc"].lower()
    salary = 175 if "high" in inc else 125 if "professional" in inc else 85
    return {"age": _STAGE_AGE.get(m["stage"], 0), "salary": salary, "sex": m["sex"], "birth_state": m["state"],
            "college": m["college"], "degree": m["degree"], "occupation": m["occ"]}


def bio_code_record(r):
    """A one-line f-string biography. It passes every Setting A check without a model."""
    p = "He" if r["sex"] == "male" else "She"
    bio = (f"{p} is {r['age']} years old, earns ${r['salary']},000 a year, was born in {r['birth_state']}, "
           f"holds a {r['degree']} degree from {r['college']} and works as a {r['occupation']}.")
    return {**bio_label(r), "biography": bio}


BLAND_AMAZON = [
    {"price": 9.99, "review_time": 2400, "rating": 5, "verified": True, "category": "Literature & Fiction > Genre Fiction",
     "brand": "Visit Amazon's Jane Smith Page", "title": "The Long Road", "description": "A novel.",
     "review_text": "Great read, loved it!", "summary": "Five Stars"},
    {"price": 12.5, "review_time": 2500, "rating": 5, "verified": True, "category": "Romance > Contemporary",
     "brand": "Visit Amazon's Mary Jones Page", "title": "Summer Hearts", "description": "A love story.",
     "review_text": "Really enjoyed this book. Highly recommend.", "summary": "Great book"},
    {"price": 7.99, "review_time": 2300, "rating": 4, "verified": True, "category": "Mystery, Thriller & Suspense > Mystery",
     "brand": "Visit Amazon's Tom Brown Page", "title": "Dark Waters", "description": "A mystery.",
     "review_text": "Good story. Kept my interest.", "summary": "Four Stars"},
]
