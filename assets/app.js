// 首頁：讀 data/reports.json 與 data/brokers.json，產生報告卡片與比較表。
(function () {
  "use strict";

  const VIEW_LABEL = { positive: "正向", neutral: "中立", negative: "負向" };
  const VIEW_ORDER = { positive: 0, neutral: 1, negative: 2 };
  const state = { reports: [], brokers: {}, company: "", broker: "", sortKey: "date", sortDir: -1 };

  const $ = (sel) => document.querySelector(sel);

  function esc(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function fmtNum(v) {
    if (v === null || v === undefined) return "—";
    const frac = Number.isInteger(v) ? 0 : 2;
    return v.toLocaleString("en-US", { minimumFractionDigits: frac, maximumFractionDigits: frac });
  }

  function fmtPct(v) {
    return (v > 0 ? "+" : "") + v.toFixed(1) + "%";
  }

  function brokerName(code) {
    return (state.brokers[code] && state.brokers[code].name) || code;
  }

  function filtered() {
    return state.reports.filter((r) =>
      (!state.company || r.ticker === state.company) && (!state.broker || r.broker === state.broker));
  }

  function badge(r) {
    return `<span class="badge ${esc(r.rating_view)}">${esc(r.rating)}・${VIEW_LABEL[r.rating_view] || ""}</span>`;
  }

  function renderCards(list) {
    const html = list.map((r) => `
      <a class="card" href="${esc(r.path)}">
        <div class="card-top">${badge(r)}${r.tags.map((t) => `<span class="tag">${esc(t)}</span>`).join("")}${r.demo ? '<span class="badge demo">示範</span>' : ""}</div>
        <h3>${esc(r.company)}<span class="ticker">${esc(r.ticker)}</span></h3>
        <p class="card-sub">${esc(brokerName(r.broker))}・${esc(r.date)}</p>
        <div class="card-nums">
          <div><span class="kpi-label">目標價（${esc(r.currency)}）</span><span class="card-big">${fmtNum(r.target_price)}</span>
            <span class="kpi-sub">前次：${r.target_prev === null ? "原文未提供" : fmtNum(r.target_prev)}</span></div>
          <div><span class="kpi-label">潛在漲幅</span><span class="card-big calc">${fmtPct(r.upside_pct)}</span>
            <span class="kpi-sub">報告日股價 ${fmtNum(r.price_at_report)}</span></div>
        </div>
        <p class="card-line">${esc(r.one_line)}</p>
      </a>`).join("");
    $("#cards").innerHTML = html || '<p class="empty">尚無報告。</p>';
  }

  function sortValue(r, key) {
    if (key === "broker") return brokerName(r.broker);
    if (key === "rating_view") return VIEW_ORDER[r.rating_view];
    const v = r[key];
    return v === null || v === undefined ? -Infinity : v;
  }

  function renderTable(list) {
    const { sortKey, sortDir } = state;
    const rows = list.slice().sort((a, b) => {
      const x = sortValue(a, sortKey), y = sortValue(b, sortKey);
      if (x < y) return -sortDir;
      if (x > y) return sortDir;
      return a.date < b.date ? 1 : -1;
    });
    $("#compare tbody").innerHTML = rows.map((r) => `
      <tr>
        <td class="nowrap">${esc(r.date)}</td>
        <td class="nowrap"><a href="${esc(r.path)}">${esc(r.company)}</a> <span class="muted">${esc(r.ticker)}</span></td>
        <td class="nowrap">${esc(brokerName(r.broker))}</td>
        <td class="nowrap">${badge(r)}</td>
        <td class="r num">${fmtNum(r.target_price)}</td>
        <td class="r num">${r.target_prev === null ? "—" : fmtNum(r.target_prev)}</td>
        <td class="r num">${fmtNum(r.price_at_report)}</td>
        <td class="r num calc">${fmtPct(r.upside_pct)}</td>
      </tr>`).join("") || '<tr><td colspan="8" class="empty">尚無報告。</td></tr>';
    document.querySelectorAll("#compare th button").forEach((b) => {
      const active = b.dataset.key === sortKey;
      b.closest("th").setAttribute("aria-sort", active ? (sortDir > 0 ? "ascending" : "descending") : "none");
      b.dataset.arrow = active ? (sortDir > 0 ? "▲" : "▼") : "";
    });
  }

  function render() {
    const list = filtered();
    renderCards(list);
    renderTable(list);
  }

  function fillSelect(sel, pairs) {
    sel.insertAdjacentHTML("beforeend", pairs.map(([v, label]) => `<option value="${esc(v)}">${esc(label)}</option>`).join(""));
  }

  function init(reports, updated) {
    state.reports = reports;
    $("#meta").textContent = `收錄 ${reports.length} 份報告・更新於 ${updated}`;
    const companies = new Map();
    reports.forEach((r) => companies.set(r.ticker, `${r.company} ${r.ticker}`));
    fillSelect($("#filter-company"), [...companies].sort((a, b) => a[0].localeCompare(b[0])));
    const brokers = [...new Set(reports.map((r) => r.broker))].map((c) => [c, brokerName(c)]).sort((a, b) => a[1].localeCompare(b[1]));
    fillSelect($("#filter-broker"), brokers);
    $("#filter-company").addEventListener("change", (e) => { state.company = e.target.value; render(); });
    $("#filter-broker").addEventListener("change", (e) => { state.broker = e.target.value; render(); });
    document.querySelectorAll("#compare th button").forEach((b) => b.addEventListener("click", () => {
      const key = b.dataset.key;
      state.sortDir = state.sortKey === key ? -state.sortDir : (key === "company" || key === "broker" || key === "rating_view" ? 1 : -1);
      state.sortKey = key;
      renderTable(filtered());
    }));
    render();
  }

  Promise.all([
    fetch("data/reports.json").then((r) => r.json()),
    fetch("data/brokers.json").then((r) => r.json()),
  ]).then(([data, brokers]) => {
    state.brokers = brokers.brokers || {};
    init(data.reports || [], data.updated || "");
  }).catch(() => {
    $("#meta").textContent = "資料讀取失敗。若是直接開啟檔案，請改用本機伺服器預覽（python3 -m http.server）。";
  });
})();
