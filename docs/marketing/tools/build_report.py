"""Build the bilingual DiffuSpace launch strategy report as two static HTML pages.

Usage: python3 docs/marketing/tools/build_report.py
Writes docs/marketing/launch_strategy_report.en.html and .zh.html.
"""
import html
import json
import pathlib

OUT = pathlib.Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------- data
# All figures from competitor_launches.md, launch_playbooks.md,
# youtube_launch_study.md and community_mentions.md, checked 2026-10-12.

DIRECT = ["Qwen3.8-27B", "Gemma 4", "GLM-4.7-Flash", "Nemotron 3.5", "Edge0"]

DATA = {
    "xviews": [  # millions, launch post views
        ["Jev", 40.02, "ref"], ["GPT-6 Luna*", 10.15, "ref"], ["Claude Haiku 5.5", 6.43, "ref"],
        ["Qwen3.8-27B", 6.04, "direct"], ["Nemotron 3.5", 2.64, "direct"], ["GLM-4.7-Flash", 1.66, "direct"],
        ["Edge0", 0.73, "direct"], ["Gemma 4*", 0.63, "direct"], ["Ember-1", 0.161, "ref"],
    ],
    "reddit": [["Gemma 4", 354], ["Qwen3.8-27B", 274], ["GLM-4.7-Flash", 60], ["Nemotron 3.5", 7], ["Edge0", 0]],
    "youtube": [["Gemma 4", 7.4], ["Qwen3.8-27B", 4.9], ["Nemotron 3.5", 0.40], ["GLM-4.7-Flash", 0.17], ["Edge0", 0.04]],
    "hn": [["Gemma 4", 1812], ["Qwen3.8-27B", 381], ["GLM-4.7-Flash", 378], ["Nemotron 3.5", 262], ["Edge0", 2]],
    "trends_direct": {
        "Qwen3.8-27B": [67, 100, 81, 86, 90, 81, 60, 54, 43, 43, 46, 54, 66, 62, 52, 40, 38, 38, 36, 42, 36, 33, 30, 28, 31, 31, 30, 30, 29],
        "GLM-4.7-Flash": [26, 100, 63, 52, 36, 56, 49, 42, 42, 42, 39, 47, 27, 43, 39, 33, 24, 25, 31, 19, 20, 26, 22, 30, 22, 34, 25, 18, 18],
        "Gemma 4": [27, 100, 82, 60, 64, 48, 45, 48, 38, 37, 33, 33, 32, 26, 26, 31, 23, 20, 19, 19, 17, 16, 16, 14, 15, 13, 13, 11, 11],
        "Nemotron 3.5": [54, 100, 56, 31, 22, 23, 24, 23, 21, 11, 11, 10, 7, 8, 12, 14, 15, 13, 7, 8, 10, 11, 17, 11, 9, 8, 7, 11, 8],
    },
    "trends_ref": {
        "Jev": [2, 11, 24, 46, 69, 97, 100, 78, 57, 45, 33, 27, 24, 29, 27, 22, 18, 15, 12, 10, 14, 13, 13, 12, 11, 8, 6, 8],
        "GPT-6 Luna": [100, 81, 34, 24, 18, 17, 15, 14, 12, 7, 6, 5, 4, 6, 6, 7, 8, 5, 4, 3, 4],
    },
    "hf30": [["Gemma 4", 11.66], ["Qwen3.8-27B", 11.30], ["GLM-4.7-Flash", 1.44], ["Nemotron 3.5", 1.44], ["Edge0", 0.08]],
    "openrouter": [  # trillions of tokens, 30 days to Oct 11
        ["GPT-6 Luna", 16.1, "ref"], ["Jev", 9.5, "ref"], ["Nemotron 3.5", 2.82, "direct"],
        ["Qwen3.8-27B", 1.35, "direct"], ["Claude Haiku 5.5**", 1.06, "ref"], ["Gemma 4", 0.82, "direct"],
    ],
    "hflikes": [["Edge0", 43.4, "hi"], ["Qwen3.8-27B", 1.20, ""], ["Nemotron 3.5", 0.20, ""], ["GLM-4.7-Flash", 0.13, ""], ["Gemma 4", 0.02, ""]],
    "bookmarks": [  # bookmarks per 1,000 views on X launch posts
        ["Edge0", 12.5, "hi"], ["Edge0 apps", 9.5, "hi"], ["Gemma 4", 2.27, ""], ["Ember-1", 1.68, ""],
        ["Jev", 1.46, ""], ["GLM-4.7-Flash", 1.38, ""], ["Qwen3.8-27B", 0.80, ""], ["Claude Haiku 5.5", 0.79, ""],
        ["GPT-6 Sol/Luna", 0.63, ""], ["Nemotron 3.5", 0.58, ""],
    ],
}

# Day-0 readiness: hours relative to the official announcement.
# bucket: pre, h1 (within 1h), h6, h24, late, none, unk
READY_COLS = ["Unsloth", "llama.cpp GGUF", "LM Studio", "MLX", "Ollama", "OpenRouter"]
READY = [
    ["Qwen3.8-27B", [("pre", "−31h"), ("h1", "+16m"), ("h1", "0h"), ("pre", "arch"), ("unk", "?"), ("h1", "+1h")]],
    ["Gemma 4", [("pre", "−50h"), ("pre", "−30h"), ("pre", "−3h"), ("h6", "+1h"), ("h1", "0h"), ("h24", "+23h")]],
    ["Nemotron 3.5", [("none", "—"), ("h1", "+26m"), ("pre", "−13h"), ("h6", "+3h"), ("h1", "+18m"), ("pre", "−8m")]],
    ["GLM-4.7-Flash", [("h24", "+9h"), ("h24", "+18h"), ("h6", "+2h"), ("h6", "+1h"), ("h6", "+6h"), ("h1", "0h")]],
    ["Edge0", [("none", "—")] * 6],
]


# ---------------------------------------------------------------- text helpers
def esc(s):
    return html.escape(s, quote=False)


class Page:
    def __init__(self, lang):
        self.lang = lang

    def t(self, en, zh):
        return en if self.lang == "en" else zh


# ---------------------------------------------------------------- content
def build(lang):
    p = Page(lang)
    t = p.t
    parts = []
    add = parts.append

    def chart(cid, title, sub, note=""):
        n = f'<p class="note">{note}</p>' if note else ""
        return (f'<figure class="card chart"><figcaption><h4>{title}</h4><p class="sub">{sub}</p></figcaption>'
                f'<div class="plot" id="{cid}"></div>{n}<details class="dt"><summary>{t("Show data table", "显示数据表")}</summary>'
                f'<div class="dtwrap" data-for="{cid}"></div></details></figure>')

    def ul(items):
        return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"

    def concl(en, zh, cls=""):
        return f'<p class="concl {cls}">{t(en, zh)}</p>'

    def comp(name, maker, verdict, vclass, stats, did, result, why):
        tiers_ = ["t1", "t1", "t2", "t3"]
        st = "".join(f'<div class="mini {tiers_[i]}"><span class="mv">{v}</span><span class="ml">{l}</span></div>' for i, (v, l) in enumerate(stats))
        return (f'<article class="card comp"><header><div><h3>{name}</h3><p class="maker">{maker}</p></div>'
                f'<span class="chip {vclass}">{verdict}</span></header><p class="concl sm">{why}</p><div class="minis">{st}</div>'
                f'<div class="cols"><div><h5>{t("What they did", "做了什么")}</h5>{ul(did)}</div>'
                f'<div><h5>{t("What happened", "结果")}</h5>{ul(result)}</div></div></article>')

    # ---------------- header
    add(f'''<header class="top"><div class="bar"><span class="mono">{t("DiffuSpace · Launch review · Draft, 2026-10-12", "DiffuSpace · 发布评审 · 草稿，2026-10-12")}</span>
<a href="{t("launch_strategy_report.zh.html", "launch_strategy_report.en.html")}">{t("中文版", "English")}</a></div>
<h1>{t("Competitive launch review: implications for DiffuSpace", "竞品发布复盘：对 DiffuSpace 的启示")}</h1>
<p class="lede">{t("Nine model launches from January to October 2026: five open-weight direct competitors and four references. Ranked by sustained use, with recommendations for the DiffuSpace launch.",
"2026 年 1 月至 10 月的九次模型发布：五个开源权重直接竞品和四个参照。按持续使用排序，并给出 DiffuSpace 发布建议。")}</p>
<nav class="toc"><a href="#summary">{t("Summary", "摘要")}</a><a href="#path">{t("Suggested path", "建议路径")}</a><a href="#low">{t("Low leverage", "低杠杆事项")}</a><a href="#metrics">{t("How we judge a launch", "评判标准")}</a><a href="#compare">{t("1 · Compare", "1 · 对比")}</a><a href="#deep">{t("2 · Competitors", "2 · 竞品")}</a><a href="#learn">{t("3 · Learnings", "3 · 启示")}</a></nav></header>''')

    # ---------------- summary
    def sbox(cls, tag, subject, metric, mlabel, body, why):
        return (f'<article class="sbox {cls}"><div class="shead"><span class="kw">{tag}</span><b>{subject}</b></div>'
                f'<div class="smetric"><span class="sv">{metric}</span><span class="sl">{mlabel}</span></div>'
                f'<p>{body}</p></article>')
    add(f'<section id="summary"><h2>{t("Summary", "摘要")}</h2>')
    add(concl("Every launch with strong sustained use ran in the major local runtimes on day 0. None of them supports diffusion decoding today.",
              "所有持续使用强劲的发布，首日都能在主流本地运行时中运行。这些运行时目前都不支持扩散解码。", "lg"))
    add('<div class="srow r3">' +
        sbox("copy", t("Copy", "模仿"), "Qwen3.8-27B", "52%", t("of peak search interest still there on day 14", "第 14 天仍保持的峰值搜索热度"),
             t("Highest sustained use among the open models. All major runtimes supported it on day 0. Headline claim: frontier-level coding on a consumer GPU.",
               "开源模型中持续使用最高。首日所有主流运行时均支持。核心卖点：消费级 GPU 上的前沿级编程能力。"),
             t("Day-14 search retention is the primary metric. Qwen's was the highest of the open models.",
               "第 14 天搜索保持度是首要指标。Qwen 在开源模型中最高。")) +
        sbox("learn", t("Learn", "学习"), "Jev", "40M", t("views from a founder account with about 1,500 followers", "浏览量，来自约 1,500 粉丝的创始人账号"),
             t("Led with the outcome (structured decisions, about 100x faster and cheaper), not the architecture. Jev is also a parallel, non-autoregressive model.",
               "以结果为主打（结构化决策，约快 100 倍、便宜 100 倍），而非架构。Jev 同样是并行、非自回归模型。"),
             t("Reach is the weakest predictor of use. This result is included because it shows a small account can reach a wide audience with a new, simply stated idea.",
               "覆盖面对使用的预测力最弱。列入此项是因为它表明，小账号凭借新颖、易表述的想法也能触达大量受众。")) +
        sbox("avoid", t("Avoid", "避免"), "Edge0-35B-A3B", "82k", t("downloads, against 4.5k GitHub stars", "下载量，对比 4.5k GitHub star"),
             t("Same size class as DiffuSpace. Not supported in any standard runtime at launch. Hands-on reviews were negative within four days.",
               "与 DiffuSpace 同体量。发布时不被任何标准运行时支持。四天内上手评测即转为负面。"),
             t("Stars and bookmarks measure interest; downloads measure use. Edge0 scored high on the first and low on the second.",
               "star 和收藏衡量兴趣，下载衡量使用。Edge0 前者高、后者低。")) + '</div>')
    add('<div class="srow r2">' +
        sbox("risk", t("Risk", "风险"), t("Runtime support", "运行时支持"), t("0 of 4", "0 / 4"), t("major local runtimes run diffusion decoding today: llama.cpp, Ollama, LM Studio, MLX", "主流本地运行时目前支持扩散解码：llama.cpp、Ollama、LM Studio、MLX"),
             t("Without upstream support merged before launch, we repeat Edge0.", "发布前没有合入上游支持，就会重蹈 Edge0 覆辙。"),
             t("Every successful open launch in the set ran in these tools on day 0.", "样本中所有成功的开源发布，首日都能在这些工具里运行。")) +
        sbox("path", t("Path", "路径"), t("For a small team", "小团队路径"), t("Day 0", "首日"), t("runnable everywhere, before the first post goes out", "处处可跑，先于第一条帖子"),
             t("Then one visual outcome claim, 8 to 12 creators with early access, and a founder post plus demo on X, Hacker News and r/LocalLLaMA at once.",
               "然后一个可视化的结果型卖点，给 8 到 12 位创作者提前体验，创始人文章加演示同时发 X、Hacker News 和 r/LocalLLaMA。"),
             t("Day-0 runtime support was common to every launch with strong sustained use, and does not depend on audience size.",
               "首日运行时支持是所有持续使用强劲的发布的共同点，且不依赖粉丝规模。")) + '</div></section>')

    summary_end = len(parts)

    # ---------------- metric priority
    add(f'<section id="metrics"><h2>{t("How we judge a launch", "我们如何评判一次发布")}</h2>')
    add(concl("Ranked by sustained use, Qwen and Gemma lead the direct competitors and Edge0 is last.",
              "按持续使用排名，Qwen 和 Gemma 在直接竞品中领先，Edge0 排最后。"))
    mstart = len(parts)
    add(f'<h3>{t("How the tiers are defined", "分层定义")}</h3>')
    add(f'<p class="lead2">{t("For an open-weight model, success is lasting use. So the metrics are ranked by how well they predicted it across these nine launches, not by how big the numbers are.", "对开源权重模型来说，成功就是持续被使用。所以这些指标按它们在九次发布中对持续使用的预测力排序，而不是按数字大小。")}</p>')
    tiers = [
        ("t1", t("Tier 1", "第一层"), t("Sustained use", "持续使用"), 3,
         t("Hugging Face downloads (last 30 days) · OpenRouter tokens (last 30 days) · search interest on day 14", "Hugging Face 近 30 天下载 · OpenRouter 近 30 天 token · 第 14 天搜索热度"),
         t("The outcome a launch is meant to produce.", "发布要达成的结果本身。")),
        ("t2", t("Tier 2", "第二层"), t("Community depth", "社区深度"), 2,
         t("r/LocalLLaMA posts in week 1 · YouTube views", "首周 r/LocalLLaMA 帖子 · YouTube 播放"),
         t("Leading indicator. Qwen, Gemma and GLM led here and retained use; Nemotron and Edge0 did not.", "领先指标。Qwen、Gemma 和 GLM 在此领先并保持了使用；Nemotron 和 Edge0 没有。")),
        ("t3", t("Tier 3", "第三层"), t("Reach", "覆盖面"), 1,
         t("X launch post views · top Hacker News story", "X 发布帖浏览 · Hacker News 最高帖"),
         t("Awareness, and the weakest predictor. Nemotron's 2.64M X views produced 7 Reddit posts. Edge0's 725k produced 82k downloads. The exception is a genuinely new idea (Jev).", "知名度，也是最弱的预测指标。Nemotron 264 万 X 浏览只带来 7 个 Reddit 帖；Edge0 72.5 万浏览只带来 8.2 万下载。例外是真正的新想法（Jev）。")),
    ]
    add('<div class="tiers">' + "".join(
        f'<div class="tier {c}"><div class="tw1"><span class="eyebrow">{n}</span><b>{name}</b><span class="weight" aria-label="weight {w}">' +
        "".join(f'<i class="{"on" if j < w else ""}"></i>' for j in range(3)) +
        f'</span></div><p class="tm mono">{m}</p><p>{why}</p></div>' for c, n, name, w, m, why in tiers) + '</div>')
    ranks = [  # direct competitors, rank per tier
        ("Qwen3.8-27B", 1, 2, 1, "good", t("1st", "第 1")), ("Gemma 4", 2, 1, 2, "good", t("2nd", "第 2")),
        ("GLM-4.7-Flash", 3, 3, 4, "mid", t("3rd", "第 3")), ("Nemotron 3.5", 4, 4, 3, "warn", t("4th", "第 4")),
        ("Edge0", 5, 5, 5, "bad", t("5th", "第 5")),
    ]
    add(f'<figure class="card score"><figcaption><h4>{t("Direct competitors, ranked by tier", "直接竞品：分层排名")}</h4><p class="sub">{t("1 is best. Overall weights the tiers 3 : 2 : 1.", "1 为最佳。总排名按 3 : 2 : 1 加权。")}</p></figcaption>'
        f'<div class="stw"><table class="scoret"><thead><tr><th></th><th>{t("Sustained use", "持续使用")}</th><th>{t("Community", "社区深度")}</th><th>{t("Reach", "覆盖面")}</th><th>{t("Overall", "总排名")}</th></tr></thead><tbody>' +
        "".join(f'<tr><td>{n}</td>' + "".join(f'<td><span class="rk r{r}">{r}</span></td>' for r in (a, b, c)) +
                f'<td><span class="chip {cls}">{o}</span></td></tr>' for n, a, b, c, cls, o in ranks) +
        f'</tbody></table></div><p class="note">{t("Qwen ranks first on sustained use despite slightly fewer official downloads than Gemma: double the day-14 retention (52% vs 26%), more OpenRouter tokens (1.35T vs 0.82T), and 6.49M more downloads through Unsloth. Reach puts Nemotron above GLM, but GLM wins where it counts, which is the case for ranking metrics this way.", "Qwen 官方下载略少于 Gemma，但持续使用排第一：第 14 天保持度是 Gemma 的两倍（52% 对 26%），OpenRouter token 更多（1.35 万亿 对 0.82 万亿），另有 649 万 Unsloth 下载。按覆盖面 Nemotron 高于 GLM，但在关键指标上 GLM 胜出，这正是按此方式排序指标的理由。")}</p></figure></section>')
    score_html = parts.pop()[:-len("</section>")]
    parts.insert(mstart, score_html)
    add("</section>")

    # ---------------- 1. compare
    add(f'<section id="compare"><h2>{t("1 · How the launches compare", "1 · 各次发布对比")}</h2>')
    add(concl("Reach did not predict sustained use. Nemotron had 2.64M X views and 7 r/LocalLLaMA posts in week 1.",
              "覆盖面不能预测持续使用。Nemotron 有 264 万 X 浏览，首周 r/LocalLLaMA 只有 7 帖。"))
    add(f'<div class="sets"><div class="set"><span class="dot d1"></span><div><b>{t("Direct competitors", "直接竞品")}</b><p>{t("Open weights, about 25B to 35B, local and agent use", "开源权重，约 25B 到 35B，面向本地和智能体")}</p><p class="names">Qwen3.8-27B · Gemma 4 26B-A4B · GLM-4.7-Flash · Nemotron 3.5 Lightning · Edge0-35B-A3B</p></div></div>'
        f'<div class="set"><span class="dot d2"></span><div><b>{t("References", "参照组")}</b><p>{t("Different category or much larger closed models, for scale", "不同品类或体量大得多的闭源模型，用于对比量级")}</p><p class="names">Jev · GPT-6 Luna · Claude Haiku 5.5 · Ember-1</p></div></div></div>')

    def tierhead(c, n, name, sub):
        return f'<div class="th3 {c}"><span class="eyebrow">{n}</span><h3>{name}</h3><p>{sub}</p></div>'

    add(tierhead("t1", t("Tier 1", "第一层"), t("Sustained use", "持续使用"),
                 t("Current 30-day numbers, so older launches don't win on age alone. Gemma and GLM launched 6 and 9 months ago.", "使用近 30 天数据，避免老发布只因时间长而占优。Gemma 和 GLM 分别发布于 6 个月和 9 个月前。")))
    add(concl("Gemma and Qwen lead Hugging Face downloads. Nemotron leads the direct set on OpenRouter, almost entirely on its free endpoint.",
              "Gemma 和 Qwen 的 Hugging Face 下载领先。Nemotron 在直接竞品中 OpenRouter 用量最高，几乎全部来自免费端点。"))
    add(f'<h3 class="cu">{t("Current usage", "当前使用情况")}</h3><p class="lead2">{t("Usage over the 30 days to October 11, 2026: Hugging Face downloads for open weights, tokens processed through OpenRouter for API use, and tokens and users in the OpenCode coding agent.", "截至 2026 年 10 月 11 日的 30 天使用量：开源权重的 Hugging Face 下载量、通过 OpenRouter 处理的 API token 量，以及 OpenCode 编程智能体中的 token 和用户数。")}</p>')
    add('<div class="grid2">' +
        chart("c_hf", t("Hugging Face downloads, last 30 days", "Hugging Face 近 30 天下载"), t("Millions, official repos only", "单位：百万，仅官方仓库"),
              t("Qwen adds 6.49M more through Unsloth's community GGUF.", "Qwen 另有 649 万来自 Unsloth 的社区 GGUF。")) +
        chart("c_or", t("OpenRouter tokens, last 30 days", "OpenRouter 近 30 天 token"), t("Trillions of tokens", "单位：万亿"),
              t("** Haiku 5.5 is 4 days of data. GLM-4.7-Flash and Ember-1 never made OpenRouter's daily top 50. Edge0 is not listed.",
                "** Haiku 5.5 只有 4 天数据。GLM-4.7-Flash 和 Ember-1 从未进入 OpenRouter 每日前 50。Edge0 未上架。")) + "</div>")
    or_rows = [('GPT-6 Luna', 'ref', '16.1', '7.08', '20', '5'), ('Jev', 'ref', '9.50', '3.36', '24', '9'), ('Nemotron 3.5 (free tier)', 'direct', '2.82', '0.91', '30', '22'), ('Qwen3.8-27B', 'direct', '1.35', '0.34', '20', '28'), ('Claude Haiku 5.5 (from Oct 8)', 'ref', '1.06', '1.06', '4', '15'), ('Gemma 4 26B', 'direct', '0.82', '0.32', '17', '46'), ('GLM-4.7-Flash', 'direct', '—', '—', '0', '—'), ('Ember-1', 'ref', '—', '—', '0', '—'), ('Edge0', 'direct', 'n/a', 'n/a', 'n/a', 'n/a')]
    add(f'<figure class="card score orstats"><figcaption><h4>{t("OpenRouter usage statistics", "OpenRouter 使用统计")}</h4><p class="sub">{t("Daily rankings export, Sep 12 to Oct 11, 2026. Tokens in trillions.", "每日排名导出数据，2026 年 9 月 12 日至 10 月 11 日。单位：万亿 token。")}</p></figcaption>'
        f'<div class="stw"><table class="ort"><thead><tr><th>{t("Model", "模型")}</th><th>{t("30-day tokens", "30 天 token")}</th><th>{t("Oct 5–11 tokens", "10 月 5–11 日 token")}</th><th>{t("Days in daily top 50", "进入每日前 50 的天数")}</th><th>{t("Best daily rank", "最佳单日排名")}</th></tr></thead><tbody>' +
        "".join(f'<tr><td><span class="dot {"d2" if g == "ref" else "d1"}"></span>{n}</td><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td></tr>' for n, g, a, b, c, d in or_rows) +
        f'</tbody></table></div><p class="note">{t("Only the top 50 models are published each day, so totals are minimums. GLM-4.7-Flash and Ember-1 never made the top 50 in this window. Edge0 is not on OpenRouter. Data before Sep 12 is not in the public export, so launch weeks for Qwen, Nemotron, Gemma and GLM are not covered.", "每天只公布前 50 名模型，因此总量为下限。GLM-4.7-Flash 和 Ember-1 在此期间从未进入前 50。Edge0 未在 OpenRouter 上架。公开导出不含 9 月 12 日之前的数据，因此 Qwen、Nemotron、Gemma 和 GLM 的发布周未覆盖。")} {t("Source: OpenRouter, CC BY 4.0.", "来源：OpenRouter，CC BY 4.0。")}</p></figure>')
    oc_rows = [('GPT-6 Luna', 'ref', '1,719', '758', '16.9K', '65.2%'), ('Nemotron 3.5', 'direct', '1,805', '638', '3.7K', '—'), ('Claude Haiku 5.5 (from Oct 7)', 'ref', '151', '151', '2.7K', '—'), ('Qwen3.8-27B', 'direct', '~0*', '0', '~0', '—'), ('GLM-4.7-Flash', 'direct', '0', '0', '0', '—'), ('Gemma 4 26B', 'direct', 'not offered', '—', '—', '—')]
    add(f'<figure class="card score orstats"><figcaption><h4>{t("OpenCode usage statistics (agentic coding)", "OpenCode 使用统计（智能体编程）")}</h4><p class="sub">{t("OpenCode Data, updated 2026-10-12 05:01 UTC. Tokens in billions.", "OpenCode Data，更新于 2026-10-12 05:01 UTC。单位：十亿 token。")}</p></figcaption>'
        f'<div class="stw"><table class="ort"><thead><tr><th>{t("Model", "模型")}</th><th>{t("Tokens, Sep 12–Oct 11", "9 月 12 日–10 月 11 日 token")}</th><th>{t("Tokens, Oct 5–11", "10 月 5–11 日 token")}</th><th>{t("Avg daily users, Oct 5–11", "10 月 5–11 日日均用户")}</th><th>{t("Weekly retention", "周留存")}</th></tr></thead><tbody>' +
        "".join(f'<tr><td><span class="dot {"d2" if g == "ref" else "d1"}"></span>{n}</td><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td></tr>' for n, g, a, b, c, d in oc_rows) +
        f'</tbody></table></div><p class="note">{t("* 0.19B tokens in total since Aug 18, from 52 users and 318 sessions. Nemotron 3.5 is free to use inside OpenCode (total spend $0) and logged 6.6M sessions from 278K users since launch. Edge0, Jev and Ember-1 are not listed.", "* 8 月 18 日以来合计 1.9 亿 token，来自 52 名用户、318 次会话。Nemotron 3.5 在 OpenCode 内免费使用（总花费 0 美元），发布以来来自 27.8 万用户的会话达 660 万次。Edge0、Jev 和 Ember-1 未列出。")} {t("Source: OpenCode Data (opencode.ai/data).", "来源：OpenCode Data（opencode.ai/data）。")}</p></figure>')
    add(f'<div class="callout wide"><b>{t("Hosted agent usage is a distribution channel of its own.", "托管智能体的使用本身就是一条分发渠道。")}</b> {t("Nemotron 3.5 has thin community activity but is the 12th most-used model in OpenCode, almost entirely as a free default. Qwen3.8-27B and GLM-4.7-Flash, which lead on downloads and community, are almost unused there. Local downloads and hosted agent usage measure different audiences.", "Nemotron 3.5 社区热度低，却是 OpenCode 使用量第 12 的模型，几乎全靠免费默认选项。在下载和社区上领先的 Qwen3.8-27B 和 GLM-4.7-Flash 在那里几乎无人使用。本地下载和托管智能体使用衡量的是不同的用户群。")}</div>')

    add(concl("On day 14, Qwen kept 52% of peak search interest and GLM 39%. Luna and Haiku fell below half on day 2.",
              "第 14 天，Qwen 保持峰值搜索热度的 52%，GLM 为 39%。Luna 和 Haiku 第 2 天就跌破一半。"))
    add('<div class="grid2w">' +
        chart("c_tr",t("Search interest after launch, days 0 to 28", "发布后的搜索热度，第 0 到 28 天"),
              t("Google Trends, each line scaled to its own peak = 100. Compares shape, not size.", "Google Trends，每条线以自身峰值 = 100 缩放。比较形状，不比较量级。")) +
        chart("c_tr2", t("References: Jev and GPT-6 Luna", "参照组：Jev 与 GPT-6 Luna"),
              t("Jev built for six days. Luna peaked on day 0.", "Jev 连续攀升六天，Luna 在第 0 天就见顶。")) + "</div>")
    add('<div class="callouts">' + "".join(f'<div class="callout"><b>{h}</b> {b}</div>' for h, b in [
        (t("Local models held longest.", "本地模型保持最久。"), t("Qwen was still at 52% of its peak on day 14, and GLM at 39%. Creator hardware guides fed a second wave.", "Qwen 第 14 天仍有峰值的 52%，GLM 为 39%。创作者的硬件指南带来了第二波。")),
        (t("API launches dropped fastest.", "API 发布衰减最快。"), t("Luna and Haiku fell below half on day 2. Nemotron had open weights but was at 23% by day 7.", "Luna 和 Haiku 第 2 天就跌破一半。Nemotron 虽开源，第 7 天也只剩 23%。")),
        (t("Usage and buzz separate for incumbents.", "巨头的使用量与声量是分离的。"), t("Luna has the most OpenRouter usage in the set, 16.1T tokens, with almost no lasting search interest.", "Luna 的 OpenRouter 使用量全场最大（16.1 万亿 token），搜索热度却几乎没有保持。")),
    ]) + '</div>')

    add(tierhead("t2", t("Tier 2", "第二层"), t("Community depth", "社区深度"),
                 t("Leading indicator of sustained use.", "持续使用的领先指标。")))
    add(concl("Gemma had 354 r/LocalLLaMA posts in week 1 and Qwen 274. Nemotron had 7 and Edge0 had 0.",
              "首周 r/LocalLLaMA 帖子：Gemma 354，Qwen 274，Nemotron 7，Edge0 0。"))
    add('<div class="grid2">' +
        chart("c_rd", t("r/LocalLLaMA posts, week 1", "r/LocalLLaMA 首周帖子数"), t("Posts naming the model, days 0 to 6", "标题提到该模型的帖子，第 0 到 6 天")) +
        chart("c_yt", t("YouTube views found", "YouTube 已发现播放量"), t("Millions, videos naming the model", "单位：百万，标题提到该模型的视频")) + "</div>")

    add(tierhead("t3", t("Tier 3", "第三层"), t("Reach", "覆盖面"),
                 t("Weakest predictor of sustained use.", "对持续使用预测力最弱。")))
    add(concl("X views tracked account size. Jev, a new model category, had 180 Hacker News stories; the open models had 4 to 36.",
              "X 浏览量反映账号体量。新品类 Jev 有 180 个 Hacker News 帖，开源模型为 4 到 36 个。"))
    add('<div class="grid2w">' +
        chart("c_x", t("X launch post views", "X 发布帖浏览量"), t("Millions of views", "单位：百万次"),
              t("* GPT-6 Luna's post was shared with GPT-6 Sol. Gemma 4 counts only the @googlegemma post; the @GoogleDeepMind thread was not checked.",
                "* GPT-6 Luna 的帖子与 GPT-6 Sol 共用。Gemma 4 只统计了 @googlegemma 的帖子，@GoogleDeepMind 的发布帖未统计。")) +
        chart("c_hn", t("Top Hacker News story", "Hacker News 最高帖"), t("Points, direct competitors", "得分，直接竞品")) + "</div>")

    add("</section>")

    # ---------------- 2. deep dive
    add(f'<section id="deep"><h2>{t("2 · Direct competitors: what they did, what happened", "2 · 直接竞品：做了什么，结果如何")}</h2>')
    add(concl("Qwen, Gemma and GLM ran in the major runtimes on day 0. Edge0 ran in none, and Nemotron launched alongside a separate router.",
              "Qwen、Gemma 和 GLM 首日即可在主流运行时中运行。Edge0 一个都不支持，Nemotron 则与一个独立路由库一同发布。"))
    add(comp("Qwen3.8-27B", t("Alibaba · launched Aug 14, 2026", "阿里 · 2026 年 8 月 14 日发布"), t("Strong", "强"), "good",
             [("52%", t("search at day 14", "第 14 天搜索")), ("18.0M", t("Unsloth GGUF downloads", "Unsloth GGUF 下载")), ("274", t("Reddit posts, wk 1", "首周 Reddit 帖")), ("6.04M", t("X views", "X 浏览"))],
             [t("Promised the 27B with the family launch on Aug 3, then shipped ten days late. The wait built search demand.", "8 月 3 日随家族发布预告 27B，推迟十天才发布。等待期间积累了搜索需求。"),
              t("Reused the Qwen3.5 architecture, so every runtime worked with no new code.", "沿用 Qwen3.5 架构，所有运行时无需新代码。"),
              t("Unsloth had early access (31 hours). LM Studio and llama.cpp GGUFs within 20 minutes; OpenRouter within the hour.", "Unsloth 提前 31 小时拿到权重。LM Studio 和 llama.cpp GGUF 20 分钟内上线，OpenRouter 一小时内上线。"),
              t("Put Claude Opus 4.6 Max in its own benchmark table.", "在官方基准表里放入 Claude Opus 4.6 Max。"),
              t("No official video. One X post, one model card.", "没有官方视频，只有一条 X 帖和一份模型卡。")],
             [t("Creators turned the table into two headlines: “runs on an 8GB card” (592k views) and “as good as Opus” (247k).", "创作者把表格变成两个标题：“8GB 显卡能跑”（59.2 万播放）和“和 Opus 一样好”（24.7 万）。"),
              t("Hardware guides drove a second wave on days 10 to 13, visible in search.", "硬件指南在第 10 到 13 天带来第二波，搜索曲线清晰可见。"),
              t("Unsloth's GGUF out-downloaded the official repo, 18.0M vs 14.6M all-time.", "Unsloth 的 GGUF 下载超过官方仓库，累计 1,800 万 对 1,460 万。")],
             t("Zero friction to run, plus a claim that pits a free local model against a paid frontier subscription.", "零门槛运行，加上把免费本地模型和付费前沿订阅正面对比的卖点。")))
    add(comp("Gemma 4", t("Google DeepMind · launched Apr 2, 2026", "Google DeepMind · 2026 年 4 月 2 日发布"), t("Strong", "强"), "good",
             [("11.7M", t("HF downloads / month, 6 mo in", "半年后 HF 月下载")), ("354", t("Reddit posts, wk 1", "首周 Reddit 帖")), ("4×", t("Qwen's search peak", "Qwen 搜索峰值")), ("1,812", t("HN points", "HN 得分"))],
             [t("Teasers on X from Demis Hassabis and Logan Kilpatrick.", "Demis Hassabis 和 Logan Kilpatrick 在 X 预热。"),
              t("Unsloth and ggml-org 1 to 2 days early; LM Studio 3 hours early; mlx-lm support at launch.", "Unsloth 和 ggml-org 提前 1 到 2 天，LM Studio 提前 3 小时，mlx-lm 发布时合入。"),
              t("Blog named about 30 launch partners. Headline: “Byte for byte, the most capable open models.”", "博客列出约 30 家首发伙伴。标题：“按参数量计算，最强的开源模型”。"),
              t("Official launch video (419k), six months of follow-ups, a Kaggle challenge, a 12B in June.", "官方发布视频（41.9 万），半年持续后续视频、Kaggle 挑战赛、6 月发布 12B。")],
             [t("Biggest community week of the direct set.", "直接竞品中首周社区反响最大。"),
              t("Creators framed it as strategy (“Why Google gave away Gemma 4”, 719k) and as free, private, offline AI.", "创作者包装成战略故事（“为什么谷歌免费送出 Gemma 4”，71.9 万）和免费、隐私、离线 AI。"),
              t("Below half of peak search by day 5, faster than Qwen, but follow-up launches brought it back.", "第 5 天跌破峰值一半，比 Qwen 快，但后续发布又拉了回来。")],
             t("The whole ecosystem was ready at once and Google's channels carried it. Not replicable for us, but the pre-staging is.", "整个生态同时就绪，谷歌渠道全力推送。我们无法复制，但提前准备生态可以。")))
    add(comp("GLM-4.7-Flash", t("Z.ai · launched Jan 19, 2026", "智谱 Z.ai · 2026 年 1 月 19 日发布"), t("Moderate", "中"), "mid",
             [("39%", t("search at day 14", "第 14 天搜索")), ("1.4M", t("HF downloads / month, 9 mo in", "9 个月后 HF 月下载")), ("60", t("Reddit posts, wk 1", "首周 Reddit 帖")), ("1.66M", t("X views", "X 浏览"))],
             [t("Model card and X post the same day: “the strongest model in the 30B class”, SWE-bench Verified 59.2.", "同一天发布模型卡和 X 帖：“30B 级别最强”，SWE-bench Verified 59.2。"),
              t("No visible early access. The community did the rest: MLX and LM Studio in hours, Ollama in 6, Unsloth in 9.", "看不到提前访问，社区完成其余：MLX 和 LM Studio 几小时内，Ollama 6 小时，Unsloth 9 小时。"),
              t("OpenRouter live the same minute as the X post.", "OpenRouter 与 X 帖同一分钟上线。")],
             [t("Day-0 videos framed as “Claude Code at home” and “42x cheaper than Claude”.", "首日视频标题是“家里的 Claude Code”和“比 Claude 便宜 42 倍”。"),
              t("Second-best retention after Qwen, still 1.4M downloads a month nine months later.", "保持度仅次于 Qwen，九个月后月下载仍有 140 万。")],
             t("A specific, credible benchmark in a size people can run, and a community that reliably converts new models.", "在大家跑得动的体量上给出具体可信的基准，加上稳定转化新模型的社区。")))
    add(comp("Nemotron 3.5 Lightning", t("NVIDIA · launched Aug 11, 2026", "英伟达 · 2026 年 8 月 11 日发布"), t("Weak", "弱"), "warn",
             [("23%", t("search at day 7", "第 7 天搜索")), ("2.8T", t("OpenRouter tokens / mo, free tier", "OpenRouter 月 token，免费档")), ("7", t("Reddit posts, wk 1", "首周 Reddit 帖")), ("2.64M", t("X views", "X 浏览"))],
             [t("Best-coordinated runtimes: llama.cpp and Ollama merged within 18 minutes, LM Studio staged 13 hours early.", "运行时协同最好：llama.cpp 和 Ollama 18 分钟内合入，LM Studio 提前 13 小时。"),
              t("Launched with a separate routing library; most blog numbers were customer routing savings.", "与路由库一同发布，博客数字多为客户路由节省。"),
              t("Same week as three other model launches.", "与另外三个模型同周发布。")],
             [t("Creators bundled it: “four new models in just 3 days”.", "创作者打包报道：“3 天 4 个新模型”。"),
              t("Real API usage, almost all on the free endpoint, but no community.", "有真实 API 使用，几乎都在免费端点，但没有社区。")],
             t("Two products split the message, the numbers weren't about the model, and the week was crowded.", "两个产品分散了信息，数字讲的不是模型本身，且撞上拥挤的一周。")))
    add(comp("Edge0-35B-A3B", t("Edge0 · launched Sep 8 to 10, 2026", "Edge0 · 2026 年 9 月 8 至 10 日发布"), t("Weak", "弱"), "bad",
             [("82k", t("downloads, all-time", "累计下载")), ("0", t("Reddit posts, wk 1", "首周 Reddit 帖")), ("12.5", t("bookmarks per 1k views", "每千次浏览收藏")), ("725k", t("X views", "X 浏览"))],
             [t("Model plus a custom streaming runtime on GitHub and Hugging Face; founder X post two days later.", "在 GitHub 和 HF 发布模型和自研流式运行时，两天后创始人发帖。"),
              t("One claim: a 35B MoE in 3 GB of active memory, on a phone.", "只有一个卖点：35B MoE 只占 3 GB 活跃内存，能在手机上跑。"),
              t("No quality benchmarks. No GGUF, Ollama, LM Studio or OpenRouter.", "没有质量基准，没有 GGUF、Ollama、LM Studio 或 OpenRouter。")],
             [t("People saved it to try later, at five times anyone else's bookmark rate.", "大家收藏留着以后试，收藏率是其他人的五倍以上。"),
              t("Reviews turned negative: an install that died on the first command; “the release and the iPhone footage are not yet the same thing”.", "评测转负面：安装后第一条命令就挂；“开源版本和 iPhone 演示还不是一回事”。")],
             t("The claim spread, but people could not verify it in tools they already use. Interest became bookmarks instead of usage.", "卖点传开了，但大家无法在已有工具里验证。兴趣变成了收藏，而不是使用。")))
    add("</section>")

    # ---------------- 3. learnings
    add(f'<section id="learn"><h2>{t("3 · Learnings for DiffuSpace", "3 · 对 DiffuSpace 的启示")}</h2>')
    add(f'<h3>{t("Channels, by leverage for an open-weight launch", "渠道：按开源权重发布的杠杆排序")}</h3>')
    add(concl("Unsloth's Qwen GGUF out-downloaded the official repo, 18.0M to 14.6M all-time.",
              "Unsloth 的 Qwen GGUF 累计下载超过官方仓库，1,800 万 对 1,460 万。", "sm"))
    ch = [
        (t("Runtimes and quantizers", "运行时与量化者"), t("Unsloth, LM Studio, ggml-org, Ollama, mlx-community are distribution. Unsloth's Qwen build beat the official repo.", "Unsloth、LM Studio、ggml-org、Ollama、mlx-community 本身就是分发。Unsloth 的 Qwen 版本下载超过官方。"), 5),
        ("r/LocalLLaMA", t("Where local models live or die: Gemma 354 posts, Qwen 274, Edge0 0. A plain Hugging Face link post works.", "本地模型的生死场：Gemma 354 帖，Qwen 274，Edge0 0。简单的 HF 链接帖就有效。"), 5),
        (t("YouTube local testers", "YouTube 本地测评者"), t("They make the long tail. Qwen's biggest videos came on days 10 to 13.", "他们制造长尾。Qwen 播放最高的视频出现在第 10 到 13 天。"), 4),
        ("Hacker News", t("Rewards new ideas, not checkpoints. Jev got 180 stories; open models got 4 to 36. Diffusion decoding is HN material.", "奖励新想法，不奖励新权重。Jev 有 180 帖，开源模型 4 到 36。扩散解码是 HN 好素材。"), 3),
        ("X", t("Mostly reflects account size, unless the idea is new and visual (Jev). Founder posts beat corporate ones.", "基本反映账号体量，除非想法新且可视化（Jev）。创始人帖胜过官方号。"), 3),
        ("OpenRouter", t("Where API users try models. Free tiers drive volume, not community.", "API 用户试用模型的地方。免费档带来量，带不来社区。"), 2),
    ]
    add('<div class="channels">' + "".join(
        f'<div class="chan"><span class="rank">{i + 1}</span><div class="cb"><b>{n}</b><p>{d}</p></div><span class="lev" aria-label="{lv}/5">' +
        "".join(f'<i class="{"on" if j < lv else ""}"></i>' for j in range(5)) + "</span></div>"
        for i, (n, d, lv) in enumerate(ch)) + "</div>")

    add(f'<h3>{t("KOL shortlist", "KOL 名单")}</h3>')
    add(concl("Qwen's most-viewed videos were hardware guides posted on days 10 to 13.",
              "Qwen 播放最高的视频是第 10 到 13 天发布的硬件指南。", "sm"))
    kol = [
        (t("Day-0 local testers", "首日本地测评"), [("Bijan Bowen", t("6 launches, same day, fixed test suite", "6 次发布，当天出片，固定测试")), ("Fahd Mirza", t("6 launches, install guide in 24h; covered Edge0", "6 次发布，24 小时出教程，报道过 Edge0")), ("Luke's Dev Lab", t("16GB local test series", "16GB 本地测试系列")), ("Sam Witteveen", t("Technical; repeats vendor framing accurately", "偏技术，准确转述厂商定位"))]),
        (t("Long-tail hardware", "长尾硬件"), [("RepoChad", t("VRAM guides; 406k on Qwen from 11K subs", "显存指南，1.1 万订阅拿到 40.6 万")), ("Red Stapler", t("Budget-GPU stunts; 592k", "低预算显卡挑战，59.2 万")), ("Digital Spaceport", t("Local inference hardware", "本地推理硬件")), ("Zero to MVP", t("Same app, two models", "同一应用对比两个模型"))]),
        (t("Mechanism explainers", "机制讲解"), [("Caleb Writes Code", t("“Explained in 7 min”; 1.27M across 4 launches", "“7 分钟讲清楚”，四次发布共 127 万")), ("IBM Technology", t("1.13M on Jev", "Jev 一期 113 万")), ("Theo · Greg Isenberg", t("Developer and startup angles", "开发者与创业视角")), ("Matthew Berman", t("Launch-day livestreams", "发布日直播"))]),
        (t("Skeptics to prepare for", "需提前应对的质疑者"), [("Prompt Engineer 48", t("Tested Edge0's install; it failed", "实测 Edge0 安装失败")), ("TechWealth Hub", t("Demo vs. release gap", "演示与发布版本的差距"))]),
    ]
    add('<div class="kols">' + "".join(
        f'<div class="card kol"><h5>{g}</h5><ul>' + "".join(f"<li><b>{n}</b><span>{d}</span></li>" for n, d in people) + "</ul></div>"
        for g, people in kol) + "</div>")

    add(f'<h3>{t("What was ready on day 0", "首日就绪情况")}</h3>')
    add(concl("Every launch with strong sustained use ran on day 0. Edge0 did not.",
              "所有持续使用强劲的发布首日都能运行。Edge0 不能。", "sm"))
    add(f'<p class="lead2">{t("Hours from the official announcement until each tool could run the model.", "从官方发布到各工具能运行该模型的小时数。")}</p>')
    add(f'<figure class="card chart"><figcaption><h4>{t("Day-0 readiness by runtime", "各运行时首日就绪情况")}</h4><p class="sub">{t("Negative = before the announcement (partner had early access). “arch” = existing architecture, no work needed.", "负数 = 早于官方发布（合作方提前拿到）。“arch” = 沿用已有架构，无需适配。")}</p></figcaption><div class="plot" id="c_ready"></div></figure>')

    add(f'<h3>{t("What needs to happen before launch", "发布前需要完成什么")}</h3>')
    add(concl("Upstream runtime support needs the most lead time, 8 weeks or more.",
              "上游运行时支持所需准备时间最长，8 周以上。", "sm"))
    tl = [
        (t("8+ weeks", "8 周以上"), t("Upstream diffusion decoding into llama.cpp, then Ollama, LM Studio, MLX; check vLLM and SGLang", "把扩散解码合入 llama.cpp 上游，再到 Ollama、LM Studio、MLX；确认 vLLM 和 SGLang"), t("The long pole. Our own harness needs a patched llama-diffusion-cli.", "最长的一环。我们自己的框架需要打补丁的 llama-diffusion-cli。"), "crit"),
        (t("6 weeks", "6 周"), t("Founder talk or technical post: why diffusion decoding, with our honest benchmark findings", "创始人演讲或技术文章：为什么做扩散解码，附真实基准结论"), t("Jev's talk six weeks out seeded the story.", "Jev 提前六周的演讲埋下了叙事。"), ""),
        (t("4 weeks", "4 周"), t("Freeze one claim our data backs. Publish the benchmark harness.", "锁定一个有数据支撑的卖点，公开基准测试框架"), t("Our HackMD draft says 700 vs 140 tok/s; our MiniWoB++ data shows 207 vs 99. Fix first.", "HackMD 草稿写 700 对 140 tok/s，MiniWoB++ 数据是 207 对 99。先解决。"), "crit"),
        (t("2 weeks", "2 周"), t("Check the release calendar; avoid weeks with major model drops", "查发布日历，避开大模型扎堆的周"), t("Luna and Nemotron were bundled into roundups.", "Luna 和 Nemotron 被打包进合集报道。"), ""),
        (t("3–5 days", "3–5 天"), t("Weights to Unsloth, bartowski, LM Studio, mlx-community. Hosted endpoint on OpenRouter. Embargoed access for 8 to 12 creators.", "权重给 Unsloth、bartowski、LM Studio、mlx-community；OpenRouter 托管端点；给 8 到 12 位创作者保密期提前体验"), t("Gemma partners were up 1 to 2 days early, Nemotron's 13 hours early; day-0 videos need early access.", "Gemma 合作方提前 1 到 2 天就绪，Nemotron 合作方提前 13 小时；首日视频需要提前体验。"), ""),
        (t("Launch minute", "发布那一分钟"), t("X, blog, HF card, Hacker News, r/LocalLLaMA, all at once", "X、博客、HF 模型卡、Hacker News、r/LocalLLaMA 同时发"), t("Haiku, Gemma and Nemotron hit every channel in the same minute.", "Haiku、Gemma 和 Nemotron 都是同一分钟全渠道发布。"), "go"),
        (t("Days 7–14", "第 7–14 天"), t("Second wave: hardware guide, head-to-head vs Qwen3.8-27B, agent-harness setup", "第二波：硬件指南、对比 Qwen3.8-27B、智能体工具链配置"), t("Qwen's long tail came from exactly these.", "Qwen 的长尾正是来自这些。"), ""),
    ]
    add('<ol class="timeline">' + "".join(
        f'<li class="{c}"><span class="when">{w}</span><div><b>{what}</b><p>{why}</p></div></li>' for w, what, why, c in tl) + "</ol>")

    add(f'<h3>{t("Messaging: one headline, supported in layers", "信息策略：一个核心标题，分层支撑")}</h3>')
    add(concl("Jev, Qwen and Haiku each led with one outcome, and creators repeated it almost word for word.",
              "Jev、Qwen 和 Haiku 各自只主打一个结果，创作者几乎逐字复述。", "sm"))
    add('<div class="evidence">' + "".join(
        f'<div class="ev {c}"><span class="tag">{h}</span><p>{b}</p></div>' for c, h, b in [
            ("good", t("One outcome won", "单一结果型标题胜出"), t("Jev: decisions, not text, 100x faster. Qwen: flagship quality on your GPU. Haiku: cheapest, fastest small model. Creators repeated these almost word for word.", "Jev：要决策不要文本，快 100 倍。Qwen：你的 GPU 上跑出旗舰质量。Haiku：最便宜最快的小模型。创作者几乎逐字复述。")),
            ("warn", t("Splitting lost", "信息分散的输了"), t("Nemotron shipped a model and a router together, and its numbers described the router's customers.", "Nemotron 同时发布模型和路由器，数字讲的是路由器客户。")),
            ("bad", t("Unproven lost", "无法证明的也输了"), t("Edge0 had one clear claim but nothing to verify it. Ember-1 had one claim but nothing to watch.", "Edge0 卖点清楚但无从验证。Ember-1 卖点单一但没东西可看。")),
        ]) + "</div>")
    ladder = [
        (t("Headline", "标题"), t("One sentence about speed people can see, tied to a model they know. Lead with the outcome, not “diffusion”.", "一句话讲看得见的速度，绑定大家熟悉的模型。用结果开头，不用“扩散”。")),
        (t("Proof", "证明"), t("A benchmark table that names Qwen3.8-27B, with quality and speed together.", "基准表点名 Qwen3.8-27B，质量和速度一起给。")),
        (t("Demo", "演示"), t("Side-by-side: the same prompt completing in parallel vs. token by token. Reproducible.", "并排视频：同一提示词，并行生成 对 逐 token 生成。必须可复现。")),
        (t("Mechanism", "机制"), t("How diffusion decoding works, with honest limits. The explainer's second act and the HN hook.", "扩散解码如何工作，以及诚实的局限。讲解视频的第二幕，也是 HN 的钩子。")),
        (t("Audiences", "受众"), t("Local runners: tok/s on a named GPU. Agent builders: latency per step. Researchers: architecture.", "本地用户：具体 GPU 上的 tok/s；智能体开发者：每步延迟；研究者：架构。")),
    ]
    add('<div class="ladder">' + "".join(
        f'<div class="rung" style="--i:{i}"><span class="step">{i + 1}</span><b>{n}</b><p>{d}</p></div>' for i, (n, d) in enumerate(ladder)) + "</div>")
    add(f'<div class="callout wide"><b>{t("Claim selection.", "卖点选择。")}</b> {t("On our benchmarks, plain diffusion was 2x to 3x faster than AR but never more accurate. Diffusion-draft plus AR-verify kept AR's exact output at 2.3x to 3.6x lower latency.", "在我们的基准中，纯扩散比自回归快 2 到 3 倍，但准确率从未更高；“扩散起草 + 自回归验证”在输出完全一致的前提下延迟降低 2.3 到 3.6 倍。")}</div>')
    add("</section>")

    # ---------------- path (rendered right after the summary)
    pstart = len(parts)
    add(f'<section id="path"><h2>{t("Suggested path for a small team", "小团队的建议路径")}</h2>')
    add(concl("Step 1 is day-0 runtime support, the one factor common to every launch with strong sustained use.",
              "第一步是首日运行时支持，这是所有持续使用强劲的发布唯一的共同点。"))
    add(f'<p class="lead2">{t("Ranked by leverage when you don't have an audience.", "在没有粉丝基础时，按杠杆从高到低排序。")}</p>')
    steps = [
        (t("Make it run everywhere on day 0", "首日处处可跑"), t("Upstream runtime support plus pre-staged GGUF and MLX quants. Needs no audience, and it turns everyone else's attention into videos, posts and downloads. Without it, nothing below converts.", "上游运行时支持，加上提前准备的 GGUF 和 MLX 量化版。不需要粉丝，却能把别人的关注转化为视频、帖子和下载。没有这一步，下面都转化不了。")),
        (t("One founder post plus a demo video", "一篇创始人文章加演示视频"), t("Post on X from the founder account, as a Show HN, and as an r/LocalLLaMA link, all at once. Jev's 40M views came from a 1,500-follower account.", "同时从创始人账号发 X、发 Show HN、发 r/LocalLLaMA 链接帖。Jev 的 4,000 万浏览来自 1,500 粉丝的账号。")),
        (t("Seed 8 to 12 creators", "提前给 8 到 12 位创作者"), t("Day 0: Bijan Bowen, Fahd Mirza, Sam Witteveen, Caleb Writes Code, Luke's Dev Lab. Follow-ups: RepoChad, Red Stapler. Pitch IBM Technology on a diffusion explainer.", "首日：Bijan Bowen、Fahd Mirza、Sam Witteveen、Caleb Writes Code、Luke's Dev Lab。后续：RepoChad、Red Stapler。向 IBM Technology 提议做扩散讲解。")),
        (t("Ride partner channels", "借力合作方渠道"), t("Ask Unsloth, LM Studio, Ollama and the OpenRouter host to post on launch day.", "请 Unsloth、LM Studio、Ollama 和 OpenRouter 托管方在发布当天发帖。")),
        (t("Get listed as a free model in coding agents", "成为编程智能体中的免费模型"), t("Nemotron 3.5 has thin community activity but is the 12th most-used model in OpenCode: 6.6M sessions from 278K users, almost all as a free option. Approach OpenCode and similar agents for a free launch slot.", "Nemotron 3.5 社区热度低，却是 OpenCode 使用量第 12 的模型：来自 27.8 万用户的 660 万次会话，几乎全部是免费选项。与 OpenCode 等智能体洽谈首发免费名额。")),
        (t("Publish the harness and honest results", "公开框架和真实结果"), t("Pre-empts the skeptics and gives Hacker News something to argue about.", "提前回应质疑者，也给 Hacker News 讨论素材。")),
        (t("Plan the second wave", "规划第二波"), t("Hardware guide, head-to-head vs Qwen3.8-27B, and agent-harness setup in weeks 2 and 3.", "第 2、3 周发布硬件指南、对比 Qwen3.8-27B、智能体工具链配置。")),
    ]
    add('<div class="steps">' + "".join(
        f'<div class="stepc"><span class="sn">{i + 1}</span><div><b>{n}</b><p>{d}</p></div></div>' for i, (n, d) in enumerate(steps)) + "</div>")
    add(f'<div class="callout wide"><b>{t("Measure from day 0.", "从发布当天开始记录。")}</b> {t("Most sources only show current totals. Snapshot daily: HF downloads, Ollama pulls, OpenRouter tokens, GitHub stars, r/LocalLLaMA posts, search interest against Qwen 3.8.", "大多数数据源只显示当前总量。每天快照：HF 下载、Ollama 拉取、OpenRouter token、GitHub star、r/LocalLLaMA 帖子数、相对 Qwen 3.8 的搜索热度。")}</div>')
    add(f'<h3>{t("Open questions for the team", "待团队决定的问题")}</h3>')
    add('<div class="questions">' + "".join(f'<div class="q"><span>?</span><p>{q}</p></div>' for q in [
        t("Which claim do we lead with, and does it survive independent reproduction? Resolve 700 vs 207 tok/s first.", "用哪个卖点打头？能否经得起独立复现？先解决 700 对 207 tok/s 的出入。"),
        t("Can diffusion decoding land in llama.cpp and Ollama in time, or do we ship a diffusion-draft, AR-verify mode that existing speculative paths can run?", "能否及时把扩散解码合入 llama.cpp 和 Ollama？否则是否发布现有投机解码路径能运行的“扩散起草、自回归验证”模式？"),
        t("Who hosts our OpenRouter endpoint?", "OpenRouter 上谁来托管我们的端点？"),
        t("Which week? Check against expected Qwen, Gemma and DeepSeek drops.", "选哪一周？对照 Qwen、Gemma 和 DeepSeek 的预期发布时间。"),
    ]) + "</div>")
    add("</section>")
    add(f'<section id="low"><h2>{t("Low leverage for us", "对我们杠杆较低的事项")}</h2>')
    add(concl("Official videos, press releases, free API tiers and engagement counts did not predict sustained use in this set.",
              "在这组样本中，官方视频、新闻稿、免费 API 档和互动数字都不能预测持续使用。"))
    lows = [
        (t("Official YouTube launch video", "官方 YouTube 发布视频"), t("Only Google's worked (419k views), on a 2.68M-subscriber channel. NVIDIA's got 10k and 15k. Creator videos did the work for Qwen, which posted none.", "只有谷歌的有效（41.9 万播放），依托 268 万订阅的频道。英伟达的只有 1 万和 1.5 万。Qwen 没发官方视频，靠的是创作者。")),
        (t("Press releases and paid promotion", "新闻稿和付费推广"), t("None of the launches that sustained use relied on them.", "持续使用强劲的发布都没有依赖它们。")),
        (t("A free API tier on its own", "单靠免费 API 档"), t("Nemotron's free OpenRouter endpoint produced 2.8T tokens a month but almost no community (7 Reddit posts in week 1).", "Nemotron 的免费 OpenRouter 端点每月 2.8 万亿 token，但几乎没有社区（首周 7 个 Reddit 帖）。")),
        (t("Optimizing for engagement counts", "追求互动数字"), t("Stars, likes and bookmarks did not predict use. Edge0 led on all three relative to its size and has 82k downloads.", "star、点赞和收藏不能预测使用。Edge0 按体量计在三项上都领先，下载却只有 8.2 万。")),
    ]
    add('<div class="lowlist">' + "".join(f'<div class="lowc"><b>{n}</b><p>{d}</p></div>' for n, d in lows) + '</div>')
    add(f'<h3>{t("Example: Edge0's engagement did not match its usage", "案例：Edge0 的互动与使用不匹配")}</h3>')
    add('<div class="grid2">' +
        chart("c_bm", t("Bookmarks per 1,000 views on X launch posts", "X 发布帖每千次浏览的收藏数"),
              t("Edge0's two posts are 4x to 22x every other launch.", "Edge0 两条帖子是其他发布的 4 到 22 倍。")) +
        chart("c_lk", t("Hugging Face likes per 1,000 downloads", "Hugging Face 每千次下载的点赞数"),
              t("Official repos, all-time. Edge0 is 36x Qwen.", "官方仓库，累计。Edge0 是 Qwen 的 36 倍。")) + '</div>')
    add(f'<div class="callout wide"><b>{t("Possibly inorganic, not verified.", "可能非自然，未经核实。")}</b> {t("Edge0 bookmarks ran at 12.5 per 1,000 views against 0.6 to 2.3 for every other launch, and its Hugging Face likes ran at 43 per 1,000 downloads against 0.02 to 1.2. It also had 4.5k GitHub stars but zero r/LocalLLaMA posts and a 2-point Hacker News story. That pattern fits inorganic engagement, or heavy save-for-later behavior. We have no direct evidence either way. The lesson holds regardless: engagement counts are cheap to inflate and did not predict use.", "Edge0 的收藏率为每千次浏览 12.5 次，其他发布为 0.6 到 2.3；其 Hugging Face 点赞为每千次下载 43 个，其他为 0.02 到 1.2。它还有 4.5k GitHub star，但 r/LocalLLaMA 零帖、Hacker News 仅 2 分。这种模式符合非自然互动，也可能是大量“先收藏再说”的行为。两种情况都没有直接证据。无论如何结论不变：互动数字容易被抬高，且不能预测使用。")}</div>')
    path_parts = parts[pstart:] + ["</section>"]
    del parts[pstart:]
    parts[summary_end:summary_end] = path_parts
    add(f'<p class="foot">{t("Sources: competitor_launches.md, launch_playbooks.md, youtube_launch_study.md, community_mentions.md. Data checked 2026-10-12.", "来源：competitor_launches.md、launch_playbooks.md、youtube_launch_study.md、community_mentions.md。数据核对于 2026-10-12。")}</p>')

    labels = {
        "direct": t("Direct competitor", "直接竞品"), "ref": t("Reference", "参照组"),
        "day": t("Day", "第"), "dayAfter": t("", " 天"), "peak": t("% of peak", "% 峰值"),
        "M": t("M", " 百万"), "T": t("T", " 万亿"), "posts": t("posts", " 帖"), "pts": t("pts", " 分"),
        "model": t("Model", "模型"), "value": t("Value", "数值"),
        "buckets": {"pre": t("Before launch", "发布前"), "h1": t("Within 1 hour", "1 小时内"), "h6": t("1 to 6 hours", "1–6 小时"),
                    "h24": t("6 to 24 hours", "6–24 小时"), "late": t("Over a day", "超过 1 天"), "none": t("Not available", "不可用"), "unk": t("Not recorded", "未记录")},
        "edge": t("Edge0 posts", "Edge0 帖子"), "other": t("Other launch posts", "其他发布帖"),
    }
    return "\n".join(parts), labels


# ---------------------------------------------------------------- page shell
CSS = r"""
:root{--bg:#eef1f5;--surface:#ffffff;--card:#ffffff;--ink:#131820;--ink2:#4a5463;--muted:#7c8594;--grid:#dde2e9;--axis:#c3cad4;--ring:rgba(19,24,32,.09);
--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--neutral:#b9c0ca;
--r250:#86b6ef;--r350:#5598e7;--r450:#2a78d6;--r550:#1c5cab;--none:#e6e9ee;
--good:#0ca30c;--warn:#fab219;--serious:#ec835a;--crit:#d03b3b;--goodink:#006300;--tint:#f3f5f8;--mask:#c9d0da;
--fd:"IBM Plex Sans Condensed","IBM Plex Sans","PingFang SC","Noto Sans SC",system-ui,sans-serif;
--fb:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI","PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--fm:"IBM Plex Mono",ui-monospace,"SF Mono",Menlo,monospace}
@media (prefers-color-scheme: dark){:root:where(:not([data-theme="light"])){--bg:#0e1116;--surface:#161b22;--card:#161b22;--ink:#f2f4f7;--ink2:#b7c0cc;--muted:#7f8896;--grid:#262d37;--axis:#3a4250;--ring:rgba(255,255,255,.09);
--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--neutral:#4b5361;--none:#202630;--goodink:#0ca30c;--tint:#1c222b;--mask:#2c3440}}
:root[data-theme="dark"]{--bg:#0e1116;--surface:#161b22;--card:#161b22;--ink:#f2f4f7;--ink2:#b7c0cc;--muted:#7f8896;--grid:#262d37;--axis:#3a4250;--ring:rgba(255,255,255,.09);
--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--neutral:#4b5361;--none:#202630;--goodink:#0ca30c;--tint:#1c222b;--mask:#2c3440}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 var(--fb)}
main{max-width:1120px;margin:0 auto;padding:24px 16px 96px}
a{color:var(--s1)}
.top .bar{display:flex;justify-content:space-between;gap:12px;font-size:13px;color:var(--muted);padding-bottom:12px;border-bottom:1px solid var(--grid)}
.top .bar a{font-weight:600;text-decoration:none}
h1{font-family:var(--fd);font-weight:700;font-size:clamp(34px,5.2vw,58px);line-height:1.04;margin:36px 0 16px;letter-spacing:-.015em;max-width:20ch}
.lede{font-size:18px;color:var(--ink2);max-width:62ch;margin:0 0 20px}
.toc{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 8px}
.toc a{font-size:14px;padding:6px 12px;border-radius:999px;background:var(--card);box-shadow:0 0 0 1px var(--ring);color:var(--ink2);text-decoration:none}
.toc a:hover{color:var(--ink)}
section{margin-top:56px}
h2{font-family:var(--fd);font-weight:700;font-size:30px;line-height:1.15;margin:0 0 20px;padding-top:18px;border-top:2px solid var(--ink)}
h3{font-size:19px;margin:40px 0 14px}
h4{font-size:15px;margin:0}
h5{font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin:0 0 8px}
p{margin:0 0 10px}
.lead2{color:var(--ink2);max-width:72ch}
.card{background:var(--card);border-radius:12px;box-shadow:0 0 0 1px var(--ring);padding:18px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-bottom:16px}
.tile{background:var(--card);border-radius:12px;box-shadow:0 0 0 1px var(--ring);padding:18px}
.tv{display:block;font-size:44px;font-weight:650;line-height:1.05;letter-spacing:-.02em}
.tl{display:block;font-size:14px;color:var(--ink2);margin-top:8px}
.takeaways{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
.take{background:var(--card);border-radius:12px;box-shadow:0 0 0 1px var(--ring);padding:16px;border-top:4px solid var(--neutral)}
.take p{font-size:14.5px;color:var(--ink2);margin:8px 0 0}
.take b{color:var(--ink)}
.take.copy{border-top-color:var(--good)}.take.learn{border-top-color:var(--s1)}.take.avoid{border-top-color:var(--crit)}.take.risk{border-top-color:var(--warn)}.take.path{border-top-color:var(--ink)}
.tag{display:inline-block;font-size:12px;font-weight:650;text-transform:uppercase;letter-spacing:.05em;color:var(--ink2)}
.sets{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}
.set{display:flex;gap:12px;background:var(--card);border-radius:12px;box-shadow:0 0 0 1px var(--ring);padding:16px}
.set p{font-size:14px;color:var(--ink2);margin:2px 0 0}.set .names{color:var(--ink);margin-top:6px}
.dot{flex:none;width:12px;height:12px;border-radius:50%;margin-top:6px}.d1{background:var(--s1)}.d2{background:var(--s2)}
.chart{margin:16px 0;padding:18px 18px 12px}
.sub{font-size:13.5px;color:var(--muted);margin:2px 0 8px}
.plot{position:relative;width:100%}
.plot svg{display:block;width:100%;height:auto;overflow:visible}
.note{font-size:12.5px;color:var(--muted);margin:8px 0 0}
.dt summary{font-size:12.5px;color:var(--muted);cursor:pointer;margin-top:8px}
.dt table{border-collapse:collapse;font-size:13px;margin-top:6px;font-variant-numeric:tabular-nums}
.dt td,.dt th{padding:3px 12px 3px 0;text-align:left;border-bottom:1px solid var(--grid)}
.grid3{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:12px}
.grid3 .chart,.grid2 .chart,.grid2w .chart{margin:0}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:12px}
.grid2w{display:grid;grid-template-columns:minmax(0,3fr) minmax(0,2fr);gap:12px}
@media (max-width:820px){.grid2w{grid-template-columns:1fr}}
.callouts{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;margin-top:12px}
.callout{background:var(--tint);border-radius:10px;padding:14px 16px;font-size:14.5px;color:var(--ink2)}
.callout b{color:var(--ink)}
.callout.wide{margin-top:16px;border-left:4px solid var(--s1)}
.pattern{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin-bottom:14px}
.pcard{background:var(--card);border-radius:10px;box-shadow:0 0 0 1px var(--ring);padding:12px 14px;border-left:4px solid var(--s1)}
.pcard.ref{border-left-color:var(--s2)}
.pn{font-weight:650;margin-bottom:6px}
.pk{font-size:13px;color:var(--ink);display:flex;gap:8px}.pk span{color:var(--muted);min-width:44px}
.pcard p{font-size:13px;color:var(--ink2);margin:6px 0 0}
.comp{margin:14px 0}
.comp header{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap}
.comp h3{margin:0;font-size:20px}
.maker{font-size:14px;color:var(--muted);margin:2px 0 0}
.chip{font-size:12.5px;font-weight:650;padding:4px 10px;border-radius:999px;background:var(--tint);color:var(--ink);display:inline-flex;align-items:center;gap:6px}
.chip::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--neutral)}
.chip.good::before{background:var(--good)}.chip.mid::before{background:var(--s1)}.chip.warn::before{background:var(--warn)}.chip.bad::before{background:var(--crit)}
.minis{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin:14px 0}
.mini{background:var(--tint);border-radius:8px;padding:10px 12px}
.mv{display:block;font-size:22px;font-weight:650;line-height:1.1}
.ml{display:block;font-size:12.5px;color:var(--ink2);margin-top:2px}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px}
.cols ul{margin:0;padding-left:18px;font-size:14.5px;color:var(--ink2)}
.cols li{margin:0 0 6px}
.why{margin:12px 0 0;padding-top:12px;border-top:1px solid var(--grid);font-size:14.5px}
.why b{display:inline-block;font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);margin-right:10px}
.channels{display:grid;gap:8px}
.chan{display:flex;gap:14px;align-items:center;background:var(--card);border-radius:10px;box-shadow:0 0 0 1px var(--ring);padding:12px 14px}
.rank{flex:none;width:30px;height:30px;border-radius:50%;background:var(--ink);color:var(--bg);display:grid;place-items:center;font-weight:650;font-size:14px}
.cb{flex:1;min-width:0}.cb p{font-size:14px;color:var(--ink2);margin:2px 0 0}
.lev{flex:none;display:flex;gap:3px}.lev i{width:10px;height:18px;border-radius:2px;background:var(--grid)}.lev i.on{background:var(--s1)}
.kols{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}
.kol ul{list-style:none;margin:0;padding:0}
.kol li{padding:7px 0;border-bottom:1px solid var(--grid);font-size:14px}
.kol li:last-child{border-bottom:0}
.kol li span{display:block;color:var(--ink2);font-size:13px}
.ready{width:100%;border-collapse:separate;border-spacing:3px;font-size:13.5px;font-variant-numeric:tabular-nums}
.ready th{font-weight:600;color:var(--ink2);text-align:center;padding:4px;font-size:12.5px}
.ready th:first-child{text-align:left}
.ready td{text-align:center;padding:10px 4px;border-radius:6px;font-weight:600}
.ready td:first-child{text-align:left;background:none;font-weight:650;padding-left:0;white-space:nowrap}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:12.5px;color:var(--ink2);margin:10px 0 0}
.legend span{display:inline-flex;align-items:center;gap:6px}
.legend i{width:12px;height:12px;border-radius:3px;display:inline-block}
.legend i.line{height:2px;border-radius:1px;width:16px}
.timeline{list-style:none;margin:0;padding:0;position:relative}
.timeline::before{content:"";position:absolute;left:110px;top:6px;bottom:6px;width:2px;background:var(--grid)}
.timeline li{display:grid;grid-template-columns:96px 1fr;gap:28px;padding:10px 0;position:relative}
.timeline li::before{content:"";position:absolute;left:105px;top:16px;width:12px;height:12px;border-radius:50%;background:var(--card);box-shadow:0 0 0 2px var(--s1)}
.timeline li.crit::before{box-shadow:0 0 0 2px var(--crit);background:var(--crit)}
.timeline li.go::before{background:var(--s1)}
.when{font-weight:650;text-align:right;font-size:14px;padding-top:2px}
.timeline p{font-size:14px;color:var(--ink2);margin:2px 0 0}
@media (max-width:600px){.timeline::before{left:6px}.timeline li{grid-template-columns:1fr;gap:2px;padding-left:24px}.timeline li::before{left:1px}.when{text-align:left}}
.evidence{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin-bottom:16px}
.ev{background:var(--card);border-radius:10px;box-shadow:0 0 0 1px var(--ring);padding:14px 16px;border-top:4px solid var(--good)}
.ev.warn{border-top-color:var(--warn)}.ev.bad{border-top-color:var(--crit)}
.ev p{font-size:14px;color:var(--ink2);margin:6px 0 0}
.ladder{display:grid;gap:6px}
.rung{display:grid;grid-template-columns:34px 130px 1fr;align-items:center;gap:12px;background:var(--card);box-shadow:0 0 0 1px var(--ring);border-radius:10px;padding:12px 14px;margin-left:calc(var(--i) * 22px)}
.rung p{margin:0;font-size:14px;color:var(--ink2)}
.step{width:28px;height:28px;border-radius:50%;background:var(--s1);color:#fff;display:grid;place-items:center;font-weight:650;font-size:13px}
@media (max-width:700px){.rung{grid-template-columns:34px 1fr;margin-left:0}.rung p{grid-column:2}}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}
.stepc{display:flex;gap:14px;background:var(--card);border-radius:12px;box-shadow:0 0 0 1px var(--ring);padding:16px}
.stepc p{font-size:14px;color:var(--ink2);margin:4px 0 0}
.sn{flex:none;width:36px;height:36px;border-radius:10px;background:var(--ink);color:var(--bg);display:grid;place-items:center;font-weight:700;font-size:16px}
.stepc:first-child{grid-column:1/-1;box-shadow:0 0 0 2px var(--s1)}
.stepc:first-child .sn{background:var(--s1);color:#fff}
.stepc.low{opacity:.75}.stepc.low .sn{background:var(--grid);color:var(--ink2)}
.questions{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}
.q{display:flex;gap:12px;background:var(--tint);border-radius:10px;padding:14px}
.q span{flex:none;width:26px;height:26px;border-radius:50%;background:var(--warn);color:#0b0b0b;display:grid;place-items:center;font-weight:700}
.q p{margin:0;font-size:14px}
.foot{font-size:12.5px;color:var(--muted);margin-top:32px}

.mono{font-family:var(--fm);letter-spacing:.02em}
.eyebrow{font-family:var(--fm);font-size:11.5px;font-weight:500;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
h1 .tk{transition:color .25s ease,background-color .25s ease;border-radius:4px}
h1 .tk.m{color:transparent;background:var(--mask)}
@media (prefers-reduced-motion: reduce){h1 .tk{transition:none}}
.srow{display:grid;gap:12px;margin-bottom:12px}
.srow.r3{grid-template-columns:repeat(3,minmax(0,1fr))}
.srow.r2{grid-template-columns:repeat(2,minmax(0,1fr))}
@media (max-width:860px){.srow.r3,.srow.r2{grid-template-columns:1fr}}
.sbox{background:var(--card);border-radius:14px;box-shadow:0 0 0 1px var(--ring);padding:18px 20px;display:flex;flex-direction:column;border-top:5px solid var(--neutral)}
.sbox.copy{border-top-color:var(--good)}.sbox.learn{border-top-color:var(--s1)}.sbox.avoid{border-top-color:var(--crit)}.sbox.risk{border-top-color:var(--warn)}.sbox.path{border-top-color:var(--ink)}
.shead{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.shead b{font-family:var(--fd);font-size:21px;font-weight:700}
.smetric{display:flex;align-items:baseline;gap:10px;margin:12px 0 10px;flex-wrap:wrap}
.sv{font-family:var(--fd);font-size:46px;font-weight:700;line-height:1;letter-spacing:-.02em}
.sl{font-size:14px;color:var(--ink2);flex:1;min-width:140px}
.sbox>p{font-size:14.5px;color:var(--ink2);margin:0 0 10px}
.swhy{margin-top:auto !important;padding-top:10px;border-top:1px dashed var(--grid);font-size:13.5px !important}
.swhy .mono{display:block;font-size:10.5px;color:var(--muted);margin-bottom:3px}
.tiers{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:8px 0 16px}
@media (max-width:860px){.tiers{grid-template-columns:1fr}}
.tier{background:var(--card);border-radius:12px;box-shadow:0 0 0 1px var(--ring);padding:16px 18px;border-left:5px solid var(--neutral)}
.tier.t1{border-left-color:var(--r550)}.tier.t2{border-left-color:var(--r350)}.tier.t3{border-left-color:var(--neutral)}
.tw1{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.tw1 b{font-family:var(--fd);font-size:20px}
.weight{margin-left:auto;display:flex;gap:3px}.weight i{width:16px;height:6px;border-radius:2px;background:var(--grid)}.weight i.on{background:var(--s1)}
.tm{font-size:12px;color:var(--ink2);margin:10px 0 8px;line-height:1.5}
.tier p:last-child{font-size:14px;color:var(--ink2);margin:0}
.score{padding:18px}
.stw{overflow-x:auto}
.scoret{border-collapse:collapse;width:100%;font-size:14px;min-width:480px}
.scoret th{font-family:var(--fm);font-size:11px;font-weight:500;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);text-align:center;padding:6px}
.scoret th:first-child{text-align:left}
.scoret td{padding:8px 6px;border-top:1px solid var(--grid);text-align:center}
.scoret td:first-child{text-align:left;font-weight:600}
.rk{display:inline-grid;place-items:center;width:28px;height:28px;border-radius:50%;font-family:var(--fm);font-weight:500;font-size:13px}
.rk.r1{background:var(--r550);color:#fff}.rk.r2{background:var(--r450);color:#fff}.rk.r3{background:var(--r350);color:#0b0b0b}.rk.r4{background:var(--r250);color:#0b0b0b}.rk.r5{background:var(--none);color:var(--muted)}
.th3{margin:44px 0 14px;padding-left:14px;border-left:5px solid var(--neutral)}
.th3.t1{border-left-color:var(--r550)}.th3.t2{border-left-color:var(--r350)}
.th3 h3{margin:2px 0 4px;font-family:var(--fd);font-size:22px}
.th3 p{color:var(--ink2);margin:0;max-width:72ch;font-size:15px}
.mini.t1{box-shadow:inset 3px 0 0 var(--r550)}.mini.t2{box-shadow:inset 3px 0 0 var(--r350)}.mini.t3{box-shadow:inset 3px 0 0 var(--neutral)}
.comp h3{font-family:var(--fd)}
.top .bar .mono{font-size:11.5px}

/* professional overrides */
:root{--fd:-apple-system,BlinkMacSystemFont,"Segoe UI","Helvetica Neue",Arial,"PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;--fb:var(--fd);--fm:var(--fd);--bg:#f5f6f8}
@media (prefers-color-scheme: dark){:root:where(:not([data-theme="light"])){--bg:#0f1217}}
:root[data-theme="dark"]{--bg:#0f1217}
body{font-size:15px;line-height:1.55}
main{max-width:1080px}
h1{font-family:var(--fd);font-size:28px;font-weight:600;letter-spacing:0;line-height:1.25;margin:24px 0 8px;max-width:none}
.lede{font-size:15.5px;max-width:80ch}
h2{font-family:var(--fd);font-size:20px;font-weight:600;border-top:1px solid var(--axis);padding-top:14px;margin-bottom:14px}
h3,.th3 h3,.comp h3,.shead b,.tw1 b{font-family:var(--fd);font-weight:600}
h3{font-size:16px;margin:28px 0 10px}
section{margin-top:40px}
.toc a{border-radius:4px;box-shadow:0 0 0 1px var(--grid);font-size:13px;padding:4px 10px}
.mono,.eyebrow{font-family:var(--fd);letter-spacing:0}
.eyebrow{font-size:11px;font-weight:600;letter-spacing:.04em}
.card,.sbox,.tier,.set,.pcard,.chan,.stepc,.ev,.rung,.kol,.comp{border-radius:6px;box-shadow:0 0 0 1px var(--grid)}
.sbox{border-top:none;border-left:3px solid var(--neutral);padding:14px 16px}
.sbox.copy{border-left-color:var(--good)}.sbox.learn{border-left-color:var(--s1)}.sbox.avoid{border-left-color:var(--crit)}.sbox.risk{border-left-color:var(--warn)}.sbox.path{border-left-color:var(--ink2)}
.shead b{font-size:16px}
.sv{font-family:var(--fd);font-size:30px;font-weight:600;letter-spacing:0}
.smetric{margin:8px 0}
.sl{font-size:13px}
.sbox>p{font-size:14px}
.swhy{border-top:1px solid var(--grid)}
.swhy .mono{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.04em}
.tier{border-left-width:3px}
.tw1 b{font-size:16px}
.tm{font-size:12.5px}
.th3{margin:32px 0 10px;border-left-width:3px;padding-left:12px}
.th3 h3{font-size:16px}
.th3 p{font-size:14px}
.comp h3{font-size:17px}
.mv{font-size:20px;font-weight:600}
.mini{border-radius:4px}
.chip{border-radius:4px;font-size:12px;font-weight:600}
.callout{border-radius:4px;font-size:14px}
.callout.wide{border-left-width:3px}
.take,.ev{border-top-width:3px}
.rank,.sn,.step{border-radius:4px}
.rung{margin-left:0}
.stepc:first-child{box-shadow:0 0 0 1px var(--s1)}
.pcard{border-left-width:3px}
.tv{font-size:32px}
.rk{border-radius:4px;font-family:var(--fd);font-weight:600}
.scoret th{font-family:var(--fd);letter-spacing:.03em}
.timeline li::before{border-radius:2px}

/* summary keywords */
:root{--kw-copy:#006300;--kw-learn:#1c5cab;--kw-avoid:#b42d2d;--kw-risk:#8a5a00;--kw-path:var(--ink)}
@media (prefers-color-scheme: dark){:root:where(:not([data-theme="light"])){--kw-copy:#3fbf3f;--kw-learn:#6da7ec;--kw-avoid:#ef7070;--kw-risk:#fab219}}
:root[data-theme="dark"]{--kw-copy:#3fbf3f;--kw-learn:#6da7ec;--kw-avoid:#ef7070;--kw-risk:#fab219}
.sbox .shead{display:block;margin-bottom:4px}
.sbox .kw{display:block;font-size:30px;font-weight:700;line-height:1.1;letter-spacing:-.01em;color:var(--kw-path)}
.sbox.copy .kw{color:var(--kw-copy)}.sbox.learn .kw{color:var(--kw-learn)}.sbox.avoid .kw{color:var(--kw-avoid)}.sbox.risk .kw{color:var(--kw-risk)}
.sbox .shead b{display:block;font-size:16px;font-weight:600;color:var(--ink);margin-top:2px}
.sbox .smetric{margin:10px 0 8px;padding:8px 10px;background:var(--tint);border-radius:4px}
.sbox .sv{font-size:22px}
.sbox{border-left-width:4px}
figure.score{margin:0 0 8px}
.orstats{margin:12px 0 0}
.ort{border-collapse:collapse;width:100%;font-size:14px;min-width:560px;font-variant-numeric:tabular-nums}
.ort th{font-size:11px;font-weight:600;letter-spacing:.03em;text-transform:uppercase;color:var(--muted);text-align:right;padding:6px 8px}
.ort th:first-child,.ort td:first-child{text-align:left}
.ort td{padding:7px 8px;border-top:1px solid var(--grid);text-align:right}
.ort td:first-child{font-weight:600;display:flex;align-items:center;gap:8px}
.ort .dot{width:9px;height:9px;margin:0}
h3.cu{margin-top:8px}
.lowlist{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:10px;margin-bottom:8px}
.lowc{background:var(--card);border-radius:6px;box-shadow:0 0 0 1px var(--grid);border-left:3px solid var(--neutral);padding:12px 14px}
.lowc p{font-size:13.5px;color:var(--ink2);margin:4px 0 0}
#tip{position:fixed;pointer-events:none;background:var(--card);color:var(--ink);box-shadow:0 0 0 1px var(--ring),0 6px 20px rgba(0,0,0,.15);border-radius:8px;padding:8px 10px;font-size:13px;opacity:0;transition:opacity .08s;z-index:10;min-width:120px}
#tip .tv2{font-weight:650;font-size:15px}
#tip .row{display:flex;align-items:center;gap:8px;justify-content:space-between}
#tip .row i{display:inline-block;width:12px;height:2px;border-radius:1px;margin-right:6px}
#tip .tl2{color:var(--ink2)}
.hit:hover + .bar,.hit:focus + .bar{filter:brightness(1.12)}
.concl{font-size:24px;font-weight:600;line-height:1.3;color:var(--ink);max-width:46ch;margin:4px 0 18px;letter-spacing:-.005em}
.concl.lg{font-size:30px;line-height:1.22;max-width:40ch;margin:4px 0 22px}
.concl.sm{font-size:19px;line-height:1.35;max-width:60ch;margin:0 0 14px}
.comp .concl.sm{margin:12px 0 0}
.concl{text-wrap:pretty}
:lang(zh) .concl,:lang(zh) .concl.lg,:lang(zh) .concl.sm{max-width:none}
@media (max-width:600px){.concl{font-size:20px}.concl.lg{font-size:24px}.concl.sm{font-size:17px}}
"""

JS = r"""
const D=window.DATA,L=window.LBL,NS='http://www.w3.org/2000/svg';
const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const tip=document.getElementById('tip');
function el(n,a={},p){const e=document.createElementNS(NS,n);for(const k in a)e.setAttribute(k,a[k]);if(p)p.appendChild(e);return e}
function txt(n,a,s,p){const e=el(n,a,p);e.textContent=s;return e}
function showTip(ev,rows){tip.replaceChildren();for(const r of rows){const d=document.createElement('div');d.className='row';
 const l=document.createElement('span');l.className='tl2';if(r.c){const i=document.createElement('i');i.style.background=r.c;l.appendChild(i)}l.appendChild(document.createTextNode(r.k));
 const v=document.createElement('span');v.className='tv2';v.textContent=r.v;d.append(v,l);tip.appendChild(d)}
 tip.style.opacity=1;moveTip(ev)}
function moveTip(ev){const x=Math.min(ev.clientX+14,innerWidth-tip.offsetWidth-8);tip.style.left=x+'px';tip.style.top=(ev.clientY+14)+'px'}
function hideTip(){tip.style.opacity=0}
function table(id,head,rows){const w=document.querySelector(`.dtwrap[data-for="${id}"]`);if(!w)return;const t=document.createElement('table');
 const h=t.insertRow();for(const c of head){const th=document.createElement('th');th.textContent=c;h.appendChild(th)}
 for(const r of rows){const tr=t.insertRow();for(const c of r){tr.insertCell().textContent=c}}w.replaceChildren(t)}
function fmt(v,u){if(Number.isInteger(v))return v.toLocaleString('en-US')+u;const d=v>=10?1:v>=0.1?2:3;return parseFloat(v.toFixed(d)).toString()+u}

// Horizontal bar chart. items: [label, value, group]; colorFn(group) -> css var
function bars(id,items,unit,colorFn,legend){
 const host=document.getElementById(id);if(!host)return;const W=host.clientWidth||600,rowH=30,pad={l:Math.min(150,W*0.36),r:64,t:4,b:4};
 const H=pad.t+pad.b+items.length*rowH;const svg=el('svg',{viewBox:`0 0 ${W} ${H}`,role:'img'},host);
 const max=Math.max(...items.map(d=>d[1]));const sx=v=>(W-pad.l-pad.r)*v/max;
 el('line',{x1:pad.l,x2:pad.l,y1:pad.t,y2:H-pad.b,stroke:css('--axis'),'stroke-width':1},svg);
 items.forEach((d,i)=>{const y=pad.t+i*rowH,bh=Math.min(18,rowH-10),by=y+(rowH-bh)/2,w=Math.max(sx(d[1]),d[1]>0?3:0);
  txt('text',{x:pad.l-8,y:y+rowH/2+4,'text-anchor':'end','font-size':12.5,fill:css('--ink2')},d[0],svg);
  const g=el('g',{tabindex:0},svg);
  el('rect',{class:'hit',x:pad.l,y:y,width:W-pad.l,height:rowH,fill:'transparent'},g);
  if(w>0){const r=Math.min(4,w/2);el('path',{class:'bar',fill:css(colorFn(d[2])),d:`M${pad.l},${by}h${w-r}a${r},${r} 0 0 1 ${r},${r}v${bh-2*r}a${r},${r} 0 0 1 -${r},${r}h-${w-r}z`},g)}
  txt('text',{x:pad.l+w+6,y:y+rowH/2+4,'font-size':12.5,fill:css('--ink'),'font-weight':600},fmt(d[1],unit),svg);
  const rows=[{k:d[0],v:fmt(d[1],unit)}];if(legend&&d[2]&&legend[d[2]])rows.push({k:legend[d[2]],v:''});
  g.addEventListener('pointermove',e=>showTip(e,rows));g.addEventListener('pointerleave',hideTip);
  g.addEventListener('focus',()=>{const b=g.getBoundingClientRect();showTip({clientX:b.left+pad.l+w,clientY:b.top},rows)});g.addEventListener('blur',hideTip)});
 if(legend){const lg=document.createElement('div');lg.className='legend';for(const k in legend){const s=document.createElement('span');const i=document.createElement('i');i.style.background=css(colorFn(k));s.append(i,document.createTextNode(legend[k]));lg.appendChild(s)}host.appendChild(lg)}
 table(id,[L.model,L.value],items.map(d=>[d[0],fmt(d[1],unit)]))}

// Line chart with crosshair; series: {name:[...]}, colors in order
function lines(id,series,colors){
 const host=document.getElementById(id);if(!host)return;const W=host.clientWidth||600,H=Math.max(220,Math.min(300,W*0.5)),pad={l:34,r:118,t:10,b:28};
 const names=Object.keys(series),n=Math.max(...names.map(k=>series[k].length));const svg=el('svg',{viewBox:`0 0 ${W} ${H}`,role:'img'},host);
 const sx=i=>pad.l+(W-pad.l-pad.r)*i/(n-1),sy=v=>pad.t+(H-pad.t-pad.b)*(1-v/100);
 for(const v of [0,25,50,75,100]){el('line',{x1:pad.l,x2:W-pad.r,y1:sy(v),y2:sy(v),stroke:css(v?'--grid':'--axis'),'stroke-width':1},svg);
  txt('text',{x:pad.l-6,y:sy(v)+4,'text-anchor':'end','font-size':11,fill:css('--muted')},v,svg)}
 for(let i=0;i<n;i+=7)txt('text',{x:sx(i),y:H-8,'text-anchor':'middle','font-size':11,fill:css('--muted')},(L.day+' '+i+L.dayAfter).trim(),svg);
 const ends=[];
 names.forEach((k,j)=>{const a=series[k],c=css(colors[j]);el('path',{d:a.map((v,i)=>(i?'L':'M')+sx(i)+','+sy(v)).join(''),fill:'none',stroke:c,'stroke-width':2,'stroke-linejoin':'round','stroke-linecap':'round'},svg);
  const li=a.length-1;el('circle',{cx:sx(li),cy:sy(a[li]),r:4,fill:c,stroke:css('--card'),'stroke-width':2},svg);ends.push({k,y:sy(a[li]),x:sx(li),c,v:a[li]})});
 ends.sort((a,b)=>a.y-b.y);for(let i=1;i<ends.length;i++)ends[i].ly=Math.max(ends[i].y,(ends[i-1].ly??ends[i-1].y)+15);ends[0].ly=ends[0].y;
 const lx=W-pad.r+14;for(const e of ends){if(Math.abs(e.ly-e.y)>1)el('path',{d:`M${e.x+6},${e.y}L${lx-4},${e.ly}`,stroke:css('--axis'),fill:'none'},svg);
  el('line',{x1:lx,x2:lx+10,y1:e.ly,y2:e.ly,stroke:e.c,'stroke-width':2},svg);txt('text',{x:lx+14,y:e.ly+4,'font-size':12,fill:css('--ink2')},e.k,svg)}
 const cross=el('line',{y1:pad.t,y2:H-pad.b,stroke:css('--axis'),'stroke-width':1,opacity:0},svg);
 const hit=el('rect',{x:pad.l,y:pad.t,width:W-pad.l-pad.r,height:H-pad.t-pad.b,fill:'transparent',tabindex:0},svg);
 const at=i=>{cross.setAttribute('x1',sx(i));cross.setAttribute('x2',sx(i));cross.setAttribute('opacity',1);
  return [{k:(L.day+' '+i+L.dayAfter).trim(),v:''}].concat(names.map((k,j)=>({k,v:series[k][i]!=null?series[k][i]+L.peak:'–',c:css(colors[j])})))};
 hit.addEventListener('pointermove',e=>{const r=svg.getBoundingClientRect(),x=(e.clientX-r.left)*W/r.width;const i=Math.max(0,Math.min(n-1,Math.round((x-pad.l)/(W-pad.l-pad.r)*(n-1))));showTip(e,at(i))});
 hit.addEventListener('pointerleave',()=>{hideTip();cross.setAttribute('opacity',0)});
 const lg=document.createElement('div');lg.className='legend';names.forEach((k,j)=>{const s=document.createElement('span');const i=document.createElement('i');i.className='line';i.style.background=css(colors[j]);s.append(i,document.createTextNode(k));lg.appendChild(s)});host.appendChild(lg);
 table(id,[L.day.trim()||'Day'].concat(names),Array.from({length:n},(_,i)=>[i].concat(names.map(k=>series[k][i]??''))))}

function ready(){const host=document.getElementById('c_ready');if(!host)return;const t=document.createElement('table');t.className='ready';
 const fill={pre:'--r550',h1:'--r450',h6:'--r350',h24:'--r250',late:'--r250',none:'--none',unk:'--none'};const dark={pre:1,h1:1};
 const h=t.insertRow();const th0=document.createElement('th');h.appendChild(th0);for(const c of window.RCOLS){const th=document.createElement('th');th.textContent=c;h.appendChild(th)}
 for(const [m,cells] of window.READY){const tr=t.insertRow();tr.insertCell().textContent=m;cells.forEach(([b,lab],j)=>{const td=tr.insertCell();td.textContent=lab;td.style.background=css(fill[b]);td.style.color=dark[b]?'#fff':css(b==='none'||b==='unk'?'--muted':'--ink');
  if(b==='h24'||b==='h6')td.style.color='#0b0b0b';td.title=m+' · '+window.RCOLS[j]+': '+L.buckets[b];
  td.addEventListener('pointermove',e=>showTip(e,[{k:m+' · '+window.RCOLS[j],v:lab},{k:L.buckets[b],v:''}]));td.addEventListener('pointerleave',hideTip)})}
 host.appendChild(t);const lg=document.createElement('div');lg.className='legend';for(const b of ['pre','h1','h6','h24','none']){const s=document.createElement('span');const i=document.createElement('i');i.style.background=css(fill[b]);if(b==='none')i.style.boxShadow='inset 0 0 0 1px '+css('--axis');s.append(i,document.createTextNode(L.buckets[b]));lg.appendChild(s)}host.appendChild(lg)}

function render(){for(const id of ['c_x','c_rd','c_yt','c_hn','c_tr','c_tr2','c_hf','c_or','c_bm','c_lk','c_ready']){const h=document.getElementById(id);if(h)h.replaceChildren()}
 const grp=g=>g==='ref'?'--s2':'--s1';const LG={direct:L.direct,ref:L.ref};
 bars('c_x',D.xviews,L.M,grp,LG);
 bars('c_rd',D.reddit,'',()=>'--s1');bars('c_yt',D.youtube,L.M,()=>'--s1');bars('c_hn',D.hn,'',()=>'--s1');
 lines('c_tr',D.trends_direct,['--s1','--s2','--s3','--s4']);lines('c_tr2',D.trends_ref,['--s1','--s2']);
 bars('c_hf',D.hf30,L.M,()=>'--s1');bars('c_or',D.openrouter,L.T,grp,LG);
 bars('c_bm',D.bookmarks,'',g=>g==='hi'?'--s2':'--neutral',{hi:L.edge,'':L.other});
 bars('c_lk',D.hflikes,'',g=>g==='hi'?'--s2':'--neutral');
 ready()}

render();let rt;addEventListener('resize',()=>{clearTimeout(rt);rt=setTimeout(render,150)});
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',render);
"""


def page(lang):
    body, labels = build(lang)
    title = "DiffuSpace Launch Strategy" if lang == "en" else "DiffuSpace 发布策略"
    data = json.dumps(DATA, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="{'en' if lang == 'en' else 'zh-CN'}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><style>{CSS}</style></head>
<body><main>
{body}
</main><div id="tip" role="tooltip"></div>
<script>window.DATA={data};window.LBL={json.dumps(labels, ensure_ascii=False)};window.READY={json.dumps(READY, ensure_ascii=False)};window.RCOLS={json.dumps(READY_COLS)};</script>
<script>{JS}</script>
</body></html>"""


if __name__ == "__main__":
    for lang in ("en", "zh"):
        (OUT / f"launch_strategy_report.{lang}.html").write_text(page(lang), encoding="utf-8")
        print("wrote", OUT / f"launch_strategy_report.{lang}.html")
