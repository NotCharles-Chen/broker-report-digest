#!/usr/bin/env python3
"""外資報告重點摘要站：自動檢查（只用標準函式庫）。

用法：在 repo 根目錄執行 `python3 scripts/check.py`
規則來源：CLAUDE.md 第 4～8 節。任何錯誤 → 結束碼 1。
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTIONS = ["basic", "rating", "thesis", "risks", "estimates", "sources"]
REQUIRED = {
    "id": str, "date": str, "broker": str, "ticker": str, "company": str,
    "title_original": str, "rating": str, "rating_view": str,
    "target_price": (int, float), "currency": str, "price_at_report": (int, float),
    "upside_pct": (int, float), "one_line": str, "tags": list, "pages": int,
    "path": str, "demo": bool,
}
NULLABLE = {"rating_prev": str, "target_prev": (int, float)}
URL_SAFE = re.compile(r"^[a-z0-9._/-]+$")
ID_RE = re.compile(r"^(\d{8})-([a-z]+)-([0-9a-z]+)(-[b-z])?$")

errors: list[str] = []
warnings: list[str] = []


def err(where: str, msg: str) -> None:
    errors.append(f"[錯誤] {where}：{msg}")


def warn(where: str, msg: str) -> None:
    warnings.append(f"[提醒] {where}：{msg}")


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        err(rel(p), "檔案不存在")
    except json.JSONDecodeError as e:
        err(rel(p), f"JSON 格式錯誤（第 {e.lineno} 行）：{e.msg}")
    return None


def rating_map() -> dict[str, str]:
    """從 CLAUDE.md 第 6.1 節的表格讀出「原文評等 → rating_view」，規則只寫一處。"""
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    m = {}
    for view, words in re.findall(r"^\|\s*`(positive|neutral|negative)`\s*\|\s*(.+?)\s*\|\s*$", text, re.M):
        for w in re.split(r"[、,]", words):
            if w.strip():
                m[w.strip().lower()] = view
    return m


def pct(a: float, b: float) -> float:
    return round((a / b - 1) * 100, 1)


# ---------- HTML 解析 ----------
class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sections: list[str] = []
        self.cur_section: str | None = None
        self.meta_id: str | None = None
        self.links: list[str] = []
        self.lede = ""
        self._in_lede = False
        self.li_count = {"thesis": 0, "risks": 0}
        self.cited_pages: set[str] = set()
        self.source_text = ""
        self.calc_values: list[str] = []
        self.num_values: list[str] = []
        # 檢查 data.num 後面緊接 cite.pg
        self.tokens: list[str] = []
        self._cite = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if tag == "section" and a.get("data-section"):
            self.cur_section = a["data-section"]
            self.sections.append(self.cur_section)
        if tag == "meta" and a.get("name") == "report-id":
            self.meta_id = a.get("content")
        for attr in ("href", "src"):
            if a.get(attr):
                self.links.append(a[attr])
        if tag == "p" and "lede" in cls:
            self._in_lede = True
        if tag in ("td", "th") and self.cur_section == "sources":
            self.source_text += " | "  # 儲存格分隔，避免「p.2」與下一格文字黏在一起
        if tag == "li" and self.cur_section in self.li_count:
            self.li_count[self.cur_section] += 1
        if tag == "data" and "num" in cls:
            self.num_values.append(a.get("value", ""))
            self.tokens.append("NUM")
        elif tag == "data" and "calc" in cls:
            self.calc_values.append(a.get("value", ""))
            self.tokens.append("CALC")
        elif tag == "cite" and "pg" in cls:
            self._cite = True
            self.tokens.append("PG")

    def handle_endtag(self, tag):
        if tag == "section":
            self.cur_section = None
        if tag == "p":
            self._in_lede = False
        if tag == "cite":
            self._cite = False
        if tag == "data":
            self.tokens.append("/DATA")

    def handle_data(self, data):
        if self._in_lede:
            self.lede += data
        if self._cite:
            self.cited_pages.add(data.strip())
        if self.cur_section == "sources":
            self.source_text += data
        if self.tokens and self.tokens[-1] == "/DATA" and data.strip():
            self.tokens.append("TEXT")


def check_links(page: Path, links: list[str]) -> None:
    for link in links:
        if re.match(r"^(https?:|mailto:|#|data:)", link):
            continue
        target = (page.parent / link.split("#")[0].split("?")[0]).resolve()
        if not target.exists():
            err(rel(page), f"連結指向不存在的檔案：{link}")


def check_report_page(p: Path, rec: dict | None) -> None:
    where = rel(p)
    html = p.read_text(encoding="utf-8")
    if "{{" in html or "}}" in html:
        err(where, "殘留 {{佔位符}}")
    if "TEMPLATE" in html:
        err(where, "殘留模板註解（TEMPLATE）")
    pp = PageParser()
    pp.feed(html)

    if pp.sections != SECTIONS:
        err(where, f"區塊順序應為 {SECTIONS}，實際為 {pp.sections}")
    if pp.meta_id != p.stem:
        err(where, f'<meta name="report-id"> 應為 {p.stem}，實際為 {pp.meta_id}')
    if pp.li_count["thesis"] != 3:
        err(where, f"核心論點應剛好 3 點，實際 {pp.li_count['thesis']} 點")
    if not 2 <= pp.li_count["risks"] <= 4:
        err(where, f"主要風險應 2～4 點，實際 {pp.li_count['risks']} 點")

    # data.num 後必須緊接 cite.pg
    t = pp.tokens
    for i, tok in enumerate(t):
        if tok == "NUM" and not (i + 2 < len(t) and t[i + 1] == "/DATA" and t[i + 2] == "PG"):
            err(where, "有 <data class=\"num\"> 後面沒有緊接 <cite class=\"pg\">（第 %d 個數字）" % (t[:i + 1].count("NUM")))
    for v in pp.num_values + pp.calc_values:
        try:
            float(v)
        except ValueError:
            err(where, f"<data> 的 value 不是純數字：{v!r}")
    for pg in sorted(pp.cited_pages):
        if not re.fullmatch(r"p\.\d+", pg):
            err(where, f"頁碼格式應為 p.數字：{pg!r}")
        elif not re.search(rf"{re.escape(pg)}(?!\d)", pp.source_text):
            err(where, f"{pg} 被引用，但未出現在「原文頁碼對照」表")

    check_links(p, pp.links)

    if rec:
        if pp.lede.strip() != rec.get("one_line", "").strip():
            err(where, "一句話結論與 reports.json 的 one_line 不一致")
        up = rec.get("upside_pct")
        if up is not None and pp.calc_values and abs(float(pp.calc_values[0]) - up) > 1e-9:
            err(where, f"頁面潛在漲幅 {pp.calc_values[0]} 與 reports.json 的 {up} 不一致")
        nums = []
        for v in pp.num_values:
            try:
                nums.append(float(v))
            except ValueError:
                pass
        for key, label in (("target_price", "目標價"), ("price_at_report", "報告日股價")):
            if isinstance(rec.get(key), (int, float)) and float(rec[key]) not in nums:
                err(where, f"頁面找不到 reports.json 的{label} {rec[key]}")


def check_reports_json() -> dict[str, dict]:
    data = load_json(ROOT / "data/reports.json")
    brokers = (load_json(ROOT / "data/brokers.json") or {}).get("brokers", {})
    rmap = rating_map()
    where = "data/reports.json"
    if not isinstance(data, dict):
        return {}
    if data.get("schema_version") != 1:
        err(where, "schema_version 應為 1")
    reports = data.get("reports", [])
    by_id: dict[str, dict] = {}
    dates = []
    for n, r in enumerate(reports, 1):
        w = f"{where} 第 {n} 筆（{r.get('id', '?')}）"
        for k, typ in REQUIRED.items():
            if k not in r:
                err(w, f"缺少欄位 {k}")
            elif not isinstance(r[k], typ) or (typ is not bool and isinstance(r[k], bool)):
                err(w, f"欄位 {k} 型別錯誤")
        for k, typ in NULLABLE.items():
            if k not in r:
                err(w, f"缺少欄位 {k}（沒有資料請填 null）")
            elif r[k] is not None and not isinstance(r[k], typ):
                err(w, f"欄位 {k} 型別錯誤")
        rid = r.get("id", "")
        m = ID_RE.match(rid)
        if not m:
            err(w, "id 格式應為 YYYYMMDD-券商代碼-股票代號")
        else:
            if r.get("date", "").replace("-", "") != m.group(1):
                err(w, "id 日期與 date 欄位不一致")
            if r.get("broker") != m.group(2):
                err(w, "id 券商代碼與 broker 欄位不一致")
            if str(r.get("ticker", "")).lower() != m.group(3):
                err(w, "id 股票代號與 ticker 欄位不一致")
        if rid in by_id:
            err(w, "id 重複")
        by_id[rid] = r
        try:
            dates.append(date.fromisoformat(r.get("date", "")))
        except ValueError:
            err(w, "date 格式應為 YYYY-MM-DD")
        if r.get("broker") not in brokers:
            err(w, f"券商代碼 {r.get('broker')!r} 不在 data/brokers.json")
        view = rmap.get(str(r.get("rating", "")).lower())
        if view is None:
            err(w, f"評等 {r.get('rating')!r} 不在 CLAUDE.md 第 6.1 節對照表")
        elif view != r.get("rating_view"):
            err(w, f"rating_view 應為 {view}")
        if isinstance(r.get("target_price"), (int, float)) and isinstance(r.get("price_at_report"), (int, float)):
            exp = pct(r["target_price"], r["price_at_report"])
            if r.get("upside_pct") != exp:
                err(w, f"upside_pct 應為 {exp}")
        if len(r.get("one_line", "")) > 40:
            err(w, "one_line 超過 40 字")
        if not 1 <= len(r.get("tags", [])) <= 3:
            err(w, "tags 應為 1～3 個")
        if r.get("path") != f"reports/{rid}.html":
            err(w, f"path 應為 reports/{rid}.html")
        elif not (ROOT / r["path"]).exists():
            err(w, f"找不到報告頁 {r['path']}")
    if dates != sorted(dates, reverse=True):
        err(where, "reports 應依 date 新到舊排序")
    return by_id


def check_paths() -> None:
    for p in ROOT.rglob("*"):
        if any(part.startswith(".") for part in p.relative_to(ROOT).parts) or "__pycache__" in p.parts:
            continue
        r = rel(p)
        if p.parent == ROOT and p.suffix == ".md":
            continue  # 根目錄的 CLAUDE.md 等說明檔不會出現在網址
        if not URL_SAFE.match(r):
            err(r, "路徑只能用英文小寫、數字、連字號（不得有中文、空白、大寫）")


def main() -> int:
    if not (ROOT / ".nojekyll").exists():
        err(".nojekyll", "檔案不存在（GitHub Pages 純靜態站必備）")
    check_paths()
    by_id = check_reports_json()
    pages = sorted((ROOT / "reports").glob("*.html")) if (ROOT / "reports").exists() else []
    for p in pages:
        if p.stem not in by_id:
            err(rel(p), "報告頁沒有登記在 data/reports.json")
        check_report_page(p, by_id.get(p.stem))
    index = ROOT / "index.html"
    if index.exists():
        ip = PageParser()
        ip.feed(index.read_text(encoding="utf-8"))
        check_links(index, ip.links)
    else:
        warn("index.html", "首頁尚未建立")

    for line in warnings + errors:
        print(line)
    status = "通過" if not errors else "未通過"
    print(f"\n檢查{status}：{len(by_id)} 份報告、{len(pages)} 個報告頁，錯誤 {len(errors)} 項、提醒 {len(warnings)} 項")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
