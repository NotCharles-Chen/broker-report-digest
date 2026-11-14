# CLAUDE.md — 外資報告重點摘要站

## 1. 專案目的

把英文外資券商報告整理成**可並排比較的中文重點頁**：一份報告 = 一個頁面，
每個數字都標出原文頁碼。網站是純靜態 HTML／CSS／JS，以 GitHub Pages 發布。

## 2. 指令

| 用途 | 指令（在 repo 根目錄執行） |
|---|---|
| 本機預覽 | `python3 -m http.server 8000`，開 <http://localhost:8000> |
| 自動檢查（**每次修改後必跑，必須 0 錯誤**） | `python3 scripts/check.py` |

不使用任何建置工具、框架或套件管理器；不新增 `package.json`、`node_modules`。

## 3. 資料夾結構

```
index.html               首頁：由 assets/app.js 讀 data/reports.json 產生報告卡片與比較表
reports/                 報告頁，一份報告一個檔：<id>.html
templates/report.html    報告頁唯一模板（只讀，新增頁面一律複製它）
data/reports.json        報告索引（首頁唯一資料來源）
data/brokers.json        券商代碼表（唯一合法的券商代碼來源）
data/reports.example.json  欄位填寫範例（虛構資料，只讀）
assets/style.css         全站唯一樣式表
assets/app.js            首頁渲染與比較表
scripts/check.py         自動檢查
CLAUDE.md log.md README.md .nojekyll .gitignore
```

- 不新增其他頂層資料夾；不為單一頁面另寫 CSS 檔或 `<style>` 區塊。
- 需要新樣式時，加到 `assets/style.css` 並沿用既有的 CSS 變數（`--c-*`、`--sp-*`）。

## 4. 命名規則

- 報告 id：`YYYYMMDD-<券商代碼>-<股票代號>`，例：`20261110-ms-2330`。
  - 日期 = 報告**發布日**（封面日期），不是你整理的日期。
  - 券商代碼必須存在於 `data/brokers.json`；沒有就先在該檔新增一筆，並記入 `log.md`。
  - 股票代號用交易所代號；英文字母一律小寫。
- 報告頁檔名 = `reports/<id>.html`；`data/reports.json` 的 `path` 欄位必須等於它。
- **所有會出現在網址的路徑一律英文小寫、數字、連字號**，不准出現中文、空白、大寫。
- 同一券商同一天同一檔股票有兩份報告時，id 後加 `-b`、`-c`。

## 5. 報告頁規格（`templates/report.html`）

每頁固定 6 個 `<section>`，**順序與 `data-section` 值不得更動、不得增刪**：

| # | data-section | 標題 | 內容要求 |
|---|---|---|---|
| 1 | `basic` | 基本資料 | 公司、代號、券商全名、報告日期、原文標題（只寫標題）、總頁數、一句話結論 |
| 2 | `rating` | 評等與目標價 | 評等（原文用詞）、前次評等、目標價、前次目標價、報告日股價、潛在漲幅 |
| 3 | `thesis` | 核心論點 | **剛好 3 點**，每點 ≤ 60 字，粗體小標＋一句說明 |
| 4 | `risks` | 主要風險 | 2～4 點，每點 ≤ 50 字 |
| 5 | `estimates` | EPS 預估 | 表格：欄 = 年度；列 = 本次預估、前次預估、調整幅度 |
| 6 | `sources` | 原文頁碼對照 | 表格：頁碼｜該頁內容｜本頁引用了哪些數字 |

### 5.1 數字標記（最重要的規則）

- 取自原文的數字一律寫成：
  `<data class="num" value="1800">1,800</data><cite class="pg">p.3</cite>`
  - `value` 放純數字（不含千分位、單位、%）；顯示文字可含千分位。
  - 緊接著一個 `<cite class="pg">p.頁碼</cite>`，中間不可有其他文字。
- **找不到頁碼的數字不准放上頁面。** 寧可留空寫「原文未提供」，不准推估或補數字。
- 自己計算出的數字（潛在漲幅、調整幅度）寫成
  `<data class="calc" value="24.1">+24.1%</data>`，不加頁碼。
- 計算公式固定：潛在漲幅 = (目標價 ÷ 報告日股價 − 1) × 100；
  調整幅度 = (本次 ÷ 前次 − 1) × 100；皆四捨五入到小數 1 位，正數加 `+`。
- 報告日股價以原文封面或首頁標示的股價為準，並附頁碼。

### 5.2 文字與格式

- 繁體中文，全形標點（，。、：；「」！？），中英文、數字之間加半形空格。
- 券商、評等、專有名詞保留英文原文，例：「Overweight（加碼）」。
- 金額寫幣別，例：「目標價 NT$1,800」。日期格式 `2026-11-10`。
- 用自己的話摘要，不寫「本報告認為」這類贅詞，直接寫結論。

## 6. 資料格式（`data/reports.json`）

```json
{ "schema_version": 1, "updated": "YYYY-MM-DD", "reports": [ { 一筆報告 } ] }
```

| 欄位 | 型別 | 說明 |
|---|---|---|
| `id` | string | 見第 4 節 |
| `date` | string | `YYYY-MM-DD`，必須與 id 日期一致 |
| `broker` | string | `data/brokers.json` 的代碼 |
| `ticker` / `company` | string | 股票代號／中文公司名 |
| `title_original` | string | 原文報告標題 |
| `rating` / `rating_prev` | string / null | 原文評等用詞；無前次填 `null` |
| `rating_view` | string | `positive`／`neutral`／`negative`（對照第 6.1 節） |
| `target_price` / `target_prev` | number / null | 目標價；無前次填 `null` |
| `currency` | string | `TWD`、`USD` 等 ISO 代碼 |
| `price_at_report` | number | 報告日股價 |
| `upside_pct` | number | 依第 5.1 節公式計算 |
| `one_line` | string | 一句話結論，≤ 40 字，與報告頁第 1 區塊一致 |
| `tags` | string[] | 1～3 個主題標籤，優先沿用既有標籤 |
| `pages` | number | 原文總頁數 |
| `path` | string | `reports/<id>.html` |
| `demo` | boolean | 虛構示範資料填 `true`，真實報告填 `false` |

- `reports` 依 `date` **新到舊**排序；新增後同步更新 `updated`。
- 報告頁與 `reports.json` 的同一數字必須一致；改一邊就要改另一邊。

### 6.1 評等對照

| rating_view | 原文用詞 |
|---|---|
| `positive` | Buy、Overweight、Outperform、Add、Accumulate |
| `neutral` | Hold、Neutral、Equal-weight、Market Perform、In-Line |
| `negative` | Sell、Underweight、Underperform、Reduce |

不在表中的用詞，先問使用者，確認後補進本表。

## 7. 標準流程：新增一份報告

1. 確認報告的券商代碼、發布日、股票代號，組出 id。
2. `cp templates/report.html reports/<id>.html`。
3. 依第 5 節填完 6 個區塊，替換所有 `{{佔位符}}`，刪掉模板內的 HTML 註解說明。
4. 在 `data/reports.json` 新增一筆（依日期排序位置插入），更新 `updated`。
5. 執行 `python3 scripts/check.py`，修到 0 錯誤。
6. 本機預覽：首頁出現新卡片、比較表多一列、報告頁手機寬度（375px）排版正常。
7. 若有改規則，在 `log.md` 記一筆。
8. commit 訊息格式：`新增報告：<券商代碼> <股票代號> <YYYY-MM-DD>`。

修改既有報告：只改內容，不改 id 與檔名；改完同樣執行第 5～7 步，
commit 訊息格式：`修正報告：<id>：<改了什麼>`。

## 8. 禁止事項

- 不准編造、推估或「四捨五入成好看」的數字；不准放沒有頁碼的原文數字。
- 不准刪除或改名既有報告頁（網址一旦公開就不能失效）。
- 不准修改 `templates/report.html` 的區塊結構；要改結構先改本檔第 5 節。
- 不准引入外部 JS 框架、CDN 腳本或追蹤碼；字型只可用 Google Fonts。

## 9. 完成前檢查清單

- [ ] `python3 scripts/check.py` 0 錯誤
- [ ] 沒有殘留 `{{` 佔位符、模板註解
- [ ] 首頁卡片、比較表、報告頁三處數字一致
- [ ] 375px 寬度下沒有水平捲動
- [ ] 規則有變動時 `log.md` 已記錄

## 10. 工作方式

### 10.1 開工與收工

- 開工：讀完本檔與 `log.md` 最近 5 筆，再動手。
- 收工：回報改了哪些檔案，並貼出 `python3 scripts/check.py` 結果的最後一行。

### 10.2 處理報告 PDF

- 逐頁讀取並記下每個數字的頁碼，再填頁面；不要憑摘要記憶填數字。
- 同一個數字在報告中出現多次且數值不同時（如封面 vs 內文），兩者都列給使用者，由使用者決定，不要自行挑選。
- 評等用詞不在第 6.1 節對照表內時，停下來問使用者。

### 10.3 何時要先問使用者

- 要修改本檔、`templates/report.html`、`assets/style.css` 的既有規則或結構時。
- 要刪除任何檔案時。
- 報告日期、券商或股票代號無法從原文確定時。

### 10.4 回覆方式

- 繁體中文，先講結論，再列出改動的檔案路徑。
