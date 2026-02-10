const markets = [
  ["XAUUSD", "2328.45", "+0.44%", "High", "Bullish"],
  ["EURUSD", "1.0821", "+0.11%", "Medium", "Neutral"],
  ["GBPUSD", "1.2685", "-0.08%", "Medium", "Bearish"],
  ["USDJPY", "151.64", "+0.26%", "High", "Bullish"],
  ["USDINR", "83.09", "-0.04%", "Low", "Neutral"],
  ["XAGUSD", "29.14", "+0.64%", "High", "Bullish"],
];

const correlations = [
  ["XAU vs DXY", "-0.82"],
  ["EURUSD vs DXY", "-0.91"],
  ["GBPUSD vs GILT10Y", "-0.54"],
  ["USDJPY vs US10Y", "+0.78"],
  ["XAU vs US10Y", "-0.66"],
  ["USDINR vs DXY", "+0.44"],
  ["XAG vs XAU", "+0.92"],
  ["EURUSD vs XAU", "+0.63"],
];

const signals = [
  "XAUUSD H1: Ascending triangle near breakout point (confidence 71%).",
  "EURUSD M15: Mean reversion sell setup invalidated by CPI surprise.",
  "GBPUSD H4: Bear channel continuation with London momentum.",
  "USDJPY M30: Bull flag in progress; watch US yields at NY open.",
];

const analysisCards = [
  {
    title: "Gold Desk – Intraday Bias",
    text: "Bias remains long above 2318. Invalidation under 2309. Targets: 2334 / 2341.",
  },
  {
    title: "Euro Volatility Regime",
    text: "Low dispersion pre-ECB. Optionality favored over directional leverage.",
  },
  {
    title: "Rupee Crossboard",
    text: "USDINR options wall near 83.20 dampens breakout probability this session.",
  },
];

const calendar = [
  ["14:00 IST", "US", "Core CPI m/m", "High", "0.3% / 0.2%"],
  ["15:30 IST", "EU", "ECB Lagarde Speech", "High", "— / —"],
  ["17:00 IST", "UK", "GDP q/q", "Medium", "0.2% / 0.1%"],
  ["19:15 IST", "US", "FOMC Member Talk", "Low", "— / —"],
];

const cot = [
  ["Gold", "+183k", "+9k", "1.7", "Crowded Long"],
  ["EUR", "-11k", "-6k", "-0.9", "Weak Bearish"],
  ["JPY", "-74k", "+4k", "-1.3", "Short Covering"],
  ["USD Index", "+24k", "+2k", "0.6", "Mild Bullish"],
];

const macro = [
  "US 10Y real yield rising: pressure on non-yielding metals.",
  "Oil bid supports inflation persistence narrative.",
  "China metals import surprise offers near-term gold sentiment support.",
];

const rooms = [
  "#xauusd-desk (2,431 online)",
  "#eurusd-london-flow (1,019 online)",
  "#news-volatility-warroom (888 online)",
  "#backtesting-builders (502 online)",
];

const backtestRuns = [
  "London Breakout | XAUUSD | PF 1.34 | Max DD 9.1%",
  "Gold Mean Reversion | XAUUSD | PF 1.58 | Max DD 6.4%",
  "DXY Divergence | EURUSD | PF 1.22 | Max DD 11.7%",
];

const $ = (selector) => document.querySelector(selector);

function renderRows(selector, rows) {
  const body = $(selector);
  body.innerHTML = rows
    .map((row) => {
      const change = row[2] || "";
      const cls = change.startsWith("+") ? "gain" : change.startsWith("-") ? "loss" : "";
      return `<tr>${row.map((c, i) => `<td class="${i === 2 ? cls : ""}">${c}</td>`).join("")}</tr>`;
    })
    .join("");
}

function renderList(selector, rows) {
  $(selector).innerHTML = rows.map((item) => `<li>${item}</li>`).join("");
}

function initData() {
  renderRows("#markets-table", markets);
  $("#correlation-grid").innerHTML = correlations
    .map(([k, v]) => `<div><strong>${k}</strong><br /><span class="${v.startsWith("-") ? "loss" : "gain"}">${v}</span></div>`)
    .join("");
  renderList("#signal-feed", signals);
  $("#analysis-cards").innerHTML = analysisCards
    .map((card) => `<article class="card"><h3>${card.title}</h3><p>${card.text}</p></article>`)
    .join("");
  renderRows("#calendar-table", calendar);
  renderRows("#cot-table", cot);
  $("#macro-feed").innerHTML = macro.map((x) => `<div>${x}</div>`).join("");
  $("#rooms").innerHTML = rooms.map((x) => `<div>${x}</div>`).join("");
  renderList("#backtest-runs", backtestRuns);

  $("#chart-grid").innerHTML = ["XAUUSD H1", "EURUSD M15", "GBPUSD H4", "USDJPY M30"]
    .map((x) => `<article class="chart"><strong>${x}</strong><small>Pivot / VWAP / Session Range Overlay</small></article>`)
    .join("");
}

function initNavigation() {
  const tabs = document.querySelectorAll(".nav-tab");
  const panels = document.querySelectorAll(".tab-panel");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      panels.forEach((p) => p.classList.remove("active"));
      const target = document.getElementById(tab.dataset.target);
      if (target) target.classList.add("active");
    });
  });
}

function initForms() {
  $("#backtest-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const score = (1 + Math.random() * 0.9).toFixed(2);
    const drawdown = (5 + Math.random() * 12).toFixed(1);
    $("#backtest-result").textContent = `Simulation complete. Profit factor ${score}, max drawdown ${drawdown}%.`;
  });

  $("#journal-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const data = new FormData(e.target);
    const pair = data.get("pair");
    const setup = data.get("setup");
    const r = data.get("r");
    const notes = data.get("notes");
    const li = document.createElement("li");
    li.textContent = `${pair}: ${setup} | R=${r}. Notes: ${notes || "none"}`;
    $("#journal-list").prepend(li);
    e.target.reset();
  });
}

function initEngineTicker() {
  const status = $("#engine-status");
  const states = [
    { text: "Operational", cls: "ok" },
    { text: "Degraded – fallback indicators", cls: "warn" },
    { text: "Operational", cls: "ok" },
  ];
  let i = 0;
  setInterval(() => {
    i = (i + 1) % states.length;
    status.textContent = states[i].text;
    status.className = states[i].cls;
  }, 9000);
}

initData();
initNavigation();
initForms();
initEngineTicker();
