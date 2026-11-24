"""Smoke test: synthetic test data (a customer plus orders) validated by code, not by an LLM.

Each request asks for one fictional customer with 1 to 3 orders as JSON, seeded with a province
and customer type in shuffled order. A record is valid only if every check passes:
  - JSON shape and types
  - 18-digit ID number: GB 11643 check digit, province code, birth date and sex agree with the fields
  - phone number format, city inside the province, age inside the customer type's range
  - dates: signup <= order <= ship <= delivery <= today, and status agrees with which dates exist
  - money: line_total = unit_price x quantity, subtotal = sum, total = subtotal - discount + shipping
  - the record loads into SQLite with CHECK, UNIQUE and FOREIGN KEY constraints
Distinct (smoke only): character 3-gram Jaccard below 0.6 against every valid record kept so far.

Run from the repo root:
    PYTHONPATH=. python experiments/testdata/smoke.py --n 20
"""
import argparse, asyncio, datetime as dt, json, random, re, sqlite3, time
from pathlib import Path

from bench.synthdata import arms

TODAY = dt.date(2026, 10, 20)
PROVINCES = {  # province: (ID code prefix, major cities)
    "北京": ("11", ["北京"]), "上海": ("31", ["上海"]),
    "广东": ("44", ["广州", "深圳", "佛山", "东莞", "珠海", "汕头", "惠州", "中山"]),
    "浙江": ("33", ["杭州", "宁波", "温州", "嘉兴", "绍兴", "金华", "台州", "湖州"]),
    "江苏": ("32", ["南京", "苏州", "无锡", "常州", "南通", "扬州", "徐州", "镇江"]),
    "四川": ("51", ["成都", "绵阳", "德阳", "宜宾", "南充", "乐山", "泸州"]),
    "湖北": ("42", ["武汉", "宜昌", "襄阳", "荆州", "黄石", "十堰"]),
    "山东": ("37", ["济南", "青岛", "烟台", "潍坊", "临沂", "淄博", "威海"]),
    "河南": ("41", ["郑州", "洛阳", "开封", "新乡", "南阳", "许昌"]),
    "福建": ("35", ["福州", "厦门", "泉州", "漳州", "莆田"]),
}
SEGMENTS = {"大学生": (18, 25), "年轻白领": (22, 35), "小微企业主": (25, 60), "自由职业者": (22, 50),
            "全职父母": (25, 45), "退休人员": (55, 85)}
STATUSES = {"pending", "shipped", "delivered", "cancelled"}

PROMPT = """请生成一条用于软件测试的虚构客户数据及其订单，内容要真实多样。今天是 2026-10-20。
客户所在省份：{province}；客户类型：{segment}。

只输出一个 JSON 对象，不要解释：
{{"customer": {{"name": 姓名, "sex": "男"或"女", "birth_date": "YYYY-MM-DD", "id_number": 18位身份证号（校验位正确，出生日期和性别与上面一致）,
  "phone": 11位手机号, "province": "{province}", "city": 该省的城市, "segment": "{segment}", "signup_date": "YYYY-MM-DD"}},
 "orders": [1到3个订单，每个为 {{"order_id": 唯一字符串, "order_date": "YYYY-MM-DD", "ship_date": 日期或null, "delivery_date": 日期或null,
   "status": "pending"/"shipped"/"delivered"/"cancelled",
   "items": [{{"sku": 字符串, "name": 商品名, "category": 品类, "unit_price": 单价, "quantity": 正整数, "line_total": 单价乘数量}}],
   "subtotal": 各行合计, "discount": 折扣金额, "shipping_fee": 运费, "total": subtotal - discount + shipping_fee}}]}}
日期需满足 注册日期 ≤ 下单日期 ≤ 发货日期 ≤ 送达日期 ≤ 今天。金额保留两位小数。"""


def check_digit(first17):
    w = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    return "10X98765432"[sum(int(c) * k for c, k in zip(first17, w)) % 11]


def date(s, field):
    if s is None:
        return None
    if not isinstance(s, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        raise ValueError(f"{field} format")
    return dt.date.fromisoformat(s)


def money_eq(a, b):
    return abs(float(a) - float(b)) <= 0.011


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE customer (id INTEGER PRIMARY KEY, id_number TEXT UNIQUE NOT NULL CHECK (length(id_number) = 18),
  phone TEXT NOT NULL CHECK (length(phone) = 11), sex TEXT CHECK (sex IN ('男','女')),
  birth_date TEXT NOT NULL, signup_date TEXT NOT NULL CHECK (signup_date >= birth_date));
CREATE TABLE orders (order_id TEXT PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customer(id),
  order_date TEXT NOT NULL, ship_date TEXT CHECK (ship_date IS NULL OR ship_date >= order_date),
  delivery_date TEXT CHECK (delivery_date IS NULL OR delivery_date >= ship_date),
  status TEXT CHECK (status IN ('pending','shipped','delivered','cancelled')),
  subtotal REAL CHECK (subtotal >= 0), discount REAL CHECK (discount >= 0 AND discount <= subtotal),
  shipping_fee REAL CHECK (shipping_fee >= 0), total REAL CHECK (total >= 0));
CREATE TABLE item (order_id TEXT NOT NULL REFERENCES orders(order_id), sku TEXT NOT NULL,
  unit_price REAL CHECK (unit_price > 0), quantity INTEGER CHECK (quantity > 0), line_total REAL,
  PRIMARY KEY (order_id, sku));
"""


def validate(record, seed):
    """Returns None if every check passes, else the first failure as a short reason."""
    try:
        c, orders = record["customer"], record["orders"]
        if c.get("province") != seed["province"] or c.get("segment") != seed["segment"]:
            return "off seed"
        if c.get("sex") not in ("男", "女"):
            return "sex"
        birth, signup = date(c.get("birth_date"), "birth_date"), date(c.get("signup_date"), "signup_date")
        idn = str(c.get("id_number", ""))
        if not re.fullmatch(r"\d{17}[\dX]", idn):
            return "id format"
        if check_digit(idn[:17]) != idn[17]:
            return "id check digit"
        if idn[:2] != PROVINCES[seed["province"]][0]:
            return "id province code"
        if idn[6:14] != birth.strftime("%Y%m%d"):
            return "id birth date"
        if (int(idn[16]) % 2 == 1) != (c["sex"] == "男"):
            return "id sex digit"
        if not re.fullmatch(r"1[3-9]\d{9}", str(c.get("phone", ""))):
            return "phone"
        if str(c.get("city", "")).removesuffix("市") not in PROVINCES[seed["province"]][1]:
            return "city not in province"
        age = TODAY.year - birth.year - ((TODAY.month, TODAY.day) < (birth.month, birth.day))
        lo, hi = SEGMENTS[seed["segment"]]
        if not lo <= age <= hi:
            return "age vs segment"
        if not (birth < signup <= TODAY):
            return "signup date"
        if not isinstance(orders, list) or not 1 <= len(orders) <= 3:
            return "order count"
        for o in orders:
            od, sd, dd = date(o.get("order_date"), "order_date"), date(o.get("ship_date"), "ship_date"), \
                date(o.get("delivery_date"), "delivery_date")
            st = o.get("status")
            if st not in STATUSES:
                return "status value"
            if not signup <= od <= TODAY:
                return "order date"
            if sd and not od <= sd <= TODAY or dd and not (sd and sd <= dd <= TODAY):
                return "date order"
            if {"pending": (sd, dd) == (None, None), "cancelled": dd is None,
                    "shipped": sd is not None and dd is None, "delivered": sd is not None and dd is not None}[st] is False:
                return "status vs dates"
            items = o["items"]
            if not items:
                return "no items"
            for it in items:
                if not isinstance(it["quantity"], int) or it["quantity"] < 1 or float(it["unit_price"]) <= 0:
                    return "item values"
                if not money_eq(float(it["unit_price"]) * it["quantity"], it["line_total"]):
                    return "line total"
            if not money_eq(sum(float(it["line_total"]) for it in items), o["subtotal"]):
                return "subtotal"
            if not money_eq(float(o["subtotal"]) - float(o["discount"]) + float(o["shipping_fee"]), o["total"]):
                return "total"
        db = sqlite3.connect(":memory:")
        db.executescript(SCHEMA)
        db.execute("INSERT INTO customer VALUES (1,?,?,?,?,?)",
                   (idn, str(c["phone"]), c["sex"], c["birth_date"], c["signup_date"]))
        for o in orders:
            db.execute("INSERT INTO orders VALUES (?,1,?,?,?,?,?,?,?,?)",
                       (str(o["order_id"]), o["order_date"], o["ship_date"], o["delivery_date"], o["status"],
                        float(o["subtotal"]), float(o["discount"]), float(o["shipping_fee"]), float(o["total"])))
            for it in o["items"]:
                db.execute("INSERT INTO item VALUES (?,?,?,?,?)", (str(o["order_id"]), str(it["sku"]),
                           float(it["unit_price"]), it["quantity"], float(it["line_total"])))
        db.commit()
    except sqlite3.IntegrityError as e:
        return f"database: {str(e)[:40]}"
    except (KeyError, TypeError, ValueError, AttributeError) as e:
        return f"shape: {type(e).__name__} {str(e)[:30]}"
    return None


def parse(text):
    t = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text.strip()).strip()
    m = re.search(r"\{.*\}", t, re.S)
    return json.loads(m.group(0) if m else t)


def grams(text):
    return {text[i:i + 3] for i in range(len(text) - 2)}


def content_text(r):
    """What makes two test records different: who the customer is and what they bought."""
    c = r["customer"]
    items = "；".join(f"{it['name']}/{it['category']}" for o in r["orders"] for it in o["items"])
    return f"{c['name']} {c['sex']} {c['birth_date'][:4]} {c['city']} {c['segment']} | {items}"


async def run(a):
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    seeds = [{"province": p, "segment": s} for p in PROVINCES for s in SEGMENTS]
    rng.shuffle(seeds)
    seeds = (seeds * (a.n // len(seeds) + 1))[:a.n]
    cells = [tuple(c.split(":")) for c in a.cells]

    async def cell(arm, temp):
        client = arms.client(arm)
        sem = asyncio.Semaphore(a.concurrency)
        t0 = time.time()

        async def one(i, seed):
            async with sem:
                ts = time.time()
                try:
                    r = await client.chat.completions.create(
                        model=arms.ARMS[arm]["model"], temperature=float(temp), max_tokens=1500, seed=5000 + i,
                        extra_body=arms.ARMS[arm]["extra"],
                        messages=[{"role": "user", "content": PROMPT.format(**seed)}])
                    raw, toks = r.choices[0].message.content or "", r.usage.completion_tokens
                except Exception as e:
                    raw, toks = "", None
                    err = repr(e)[:200]
            row = {"arm": arm, "temp": float(temp), "i": i, "seed": seed, "raw": raw, "completion_tokens": toks,
                   "latency_s": round(time.time() - ts, 2), "t_done": round(time.time() - t0, 2)}
            if not raw:
                row.update(valid=False, reason="error " + (err if toks is None else "empty"))
            else:
                try:
                    rec = parse(raw)
                    why = validate(rec, seed)
                except Exception as e:
                    rec, why = None, f"json: {type(e).__name__}"
                row.update(record=rec, valid=why is None, reason=why or "ok")
            with out.open("a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        await asyncio.gather(*(one(i, s) for i, s in enumerate(seeds)))
        print(arm, temp, "done in", round(time.time() - t0, 1), "s", flush=True)

    by_arm = {}
    for arm, temp in cells:
        by_arm.setdefault(arm, []).append(temp)

    async def arm_run(arm):
        for t in by_arm[arm]:
            await cell(arm, t)

    await asyncio.gather(*map(arm_run, by_arm))


def report(path):
    rows = [json.loads(l) for l in open(path)]
    import collections
    print("cell        | valid | distinct | wall s | median latency | top failures")
    for c in sorted({(r["arm"], r["temp"]) for r in rows}):
        rs = sorted((r for r in rows if (r["arm"], r["temp"]) == c), key=lambda r: r["t_done"])
        valid = [r for r in rs if r["valid"]]
        kept = []
        for r in valid:
            g = grams(content_text(r["record"]))
            if all(len(g & k) / len(g | k) < 0.6 for k in kept):
                kept.append(g)
        lat = sorted(r["latency_s"] for r in rs)
        fails = collections.Counter(r["reason"] for r in rs if not r["valid"]).most_common(4)
        print(f"{c[0]} {c[1]:<4} | {len(valid):2d}/{len(rs)} | {len(kept):2d} | {max(r['t_done'] for r in rs):5.1f} | "
              f"{lat[len(lat) // 2]:5.1f} | {fails}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--cells", nargs="+", default=["dllm:0.6", "dllm:0.8", "qwen:0.8", "qwen:1.0", "qwen:1.2"])
    p.add_argument("--n", type=int, default=20)
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", default="experiments/testdata/results/smoke.jsonl")
    p.add_argument("--report", action="store_true", help="only print the summary of --out")
    a = p.parse_args()
    if not a.report:
        asyncio.run(run(a))
    report(a.out)
