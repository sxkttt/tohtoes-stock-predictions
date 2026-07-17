// --- floating particle background for the start screen ---
(function initParticles() {
  const canvas = document.getElementById("start-particles");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const startScreen = document.getElementById("start-screen");
  let w, h, particles;

  function resize() {
    w = canvas.width = canvas.offsetWidth;
    h = canvas.height = canvas.offsetHeight;
  }

  function makeParticles(n) {
    particles = Array.from({ length: n }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      r: 1 + Math.random() * 2,
      speed: 0.15 + Math.random() * 0.35,
      drift: (Math.random() - 0.5) * 0.3,
      hue: Math.random() < 0.5 ? "38,217,154" : "91,140,255",
      alpha: 0.15 + Math.random() * 0.35,
    }));
  }

  function tick() {
    if (!startScreen.classList.contains("hidden-screen") && w && h) {
      ctx.clearRect(0, 0, w, h);
      particles.forEach((p) => {
        p.y -= p.speed;
        p.x += p.drift;
        if (p.y < -5) { p.y = h + 5; p.x = Math.random() * w; }
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${p.hue},${p.alpha})`;
        ctx.fill();
      });
    }
    requestAnimationFrame(tick);
  }

  window.addEventListener("resize", resize);
  resize();
  makeParticles(60);
  tick();
})();

const PATTERN_INFO = {
  "Doji": "Open and close are virtually equal, signaling indecision between buyers and sellers. Often a pause point rather than a reversal on its own.",
  "Dragonfly Doji": "A doji with a long lower shadow and little to no upper shadow — sellers pushed price down but buyers reclaimed it by the close. Bullish, especially after a downtrend.",
  "Gravestone Doji": "A doji with a long upper shadow and little to no lower shadow — buyers pushed price up but sellers dragged it back by the close. Bearish, especially after an uptrend.",
  "Long-Legged Doji": "Long shadows on both sides with an open/close near the middle — a sharp tug-of-war that ended in a stalemate. Signals strong indecision.",
  "Bullish Marubozu": "A long bullish candle with little to no shadows — buyers were in control the entire session, opening near the low and closing near the high.",
  "Bearish Marubozu": "A long bearish candle with little to no shadows — sellers were in control the entire session, opening near the high and closing near the low.",
  "Hammer": "A small body near the top of the range with a long lower shadow, appearing after a downtrend. Sellers drove price down but buyers stepped in — a possible bullish reversal.",
  "Hanging Man": "The same shape as a Hammer, but appearing after an uptrend. Sellers are starting to challenge the trend — a possible bearish reversal.",
  "Inverted Hammer": "A small body near the bottom of the range with a long upper shadow, appearing after a downtrend. Buyers tested higher prices — a possible bullish reversal, best confirmed by the next candle.",
  "Shooting Star": "The same shape as an Inverted Hammer, but appearing after an uptrend. Buyers pushed price up but sellers took back control by the close — a possible bearish reversal.",
  "Spinning Top": "A small body with shadows of similar length on both sides. Neither buyers nor sellers won the session — a sign of indecision, often seen before a trend change or pause.",
  "Bullish Engulfing": "A bearish candle followed by a larger bullish candle that fully engulfs its body. Buyers overwhelmed the prior session's selling — a strong bullish reversal signal.",
  "Bearish Engulfing": "A bullish candle followed by a larger bearish candle that fully engulfs its body. Sellers overwhelmed the prior session's buying — a strong bearish reversal signal.",
  "Bullish Harami": "A large bearish candle followed by a small candle contained entirely within its body. Selling momentum is stalling — an early, tentative bullish signal.",
  "Bearish Harami": "A large bullish candle followed by a small candle contained entirely within its body. Buying momentum is stalling — an early, tentative bearish signal.",
  "Harami Cross": "A Harami where the second candle is a doji — an even stronger sign that momentum has stalled and a reversal may follow.",
  "Piercing Line": "A bearish candle followed by a bullish candle that opens below its low but closes above the midpoint of its body. A meaningful bullish reversal.",
  "Dark Cloud Cover": "A bullish candle followed by a bearish candle that opens above its high but closes below the midpoint of its body. A meaningful bearish reversal.",
  "Tweezer Top": "Two opposite-colored candles with matching highs — price rejected the same level twice in a row. A bearish signal, especially at resistance.",
  "Tweezer Bottom": "Two opposite-colored candles with matching lows — price found support at the same level twice in a row. A bullish signal, especially at support.",
  "Bullish Kicker": "A strong bearish candle followed by a gap-up strong bullish candle with no overlap. A sudden, decisive shift in sentiment — one of the strongest bullish signals.",
  "Bearish Kicker": "A strong bullish candle followed by a gap-down strong bearish candle with no overlap. A sudden, decisive shift in sentiment — one of the strongest bearish signals.",
  "Morning Star": "A three-candle bottom pattern: a large bearish candle, a small indecisive candle that gaps down, and a bullish candle closing back above the first candle's midpoint. A classic bullish reversal.",
  "Morning Doji Star": "A Morning Star where the middle candle is a doji — the pause between selling and buying is even more pronounced, making the reversal signal stronger.",
  "Evening Star": "A three-candle top pattern: a large bullish candle, a small indecisive candle that gaps up, and a bearish candle closing back below the first candle's midpoint. A classic bearish reversal.",
  "Evening Doji Star": "An Evening Star where the middle candle is a doji — the pause between buying and selling is even more pronounced, making the reversal signal stronger.",
  "Three White Soldiers": "Three consecutive strong bullish candles, each opening within the prior body and closing higher. Sustained, steady buying pressure.",
  "Three Black Crows": "Three consecutive strong bearish candles, each opening within the prior body and closing lower. Sustained, steady selling pressure.",
  "Three Inside Up": "A Bullish Harami confirmed by a third candle closing above the first candle's open — turning a tentative signal into a more reliable bullish reversal.",
  "Three Inside Down": "A Bearish Harami confirmed by a third candle closing below the first candle's open — turning a tentative signal into a more reliable bearish reversal.",
  "Three Outside Up": "A Bullish Engulfing confirmed by a third candle closing even higher — reinforcing the bullish reversal.",
  "Three Outside Down": "A Bearish Engulfing confirmed by a third candle closing even lower — reinforcing the bearish reversal.",
  "Bullish Abandoned Baby": "A rare, strong reversal: a bearish candle, a doji that gaps below it, then a bullish candle that gaps back above the doji — leaving it 'abandoned' in the middle.",
  "Bearish Abandoned Baby": "A rare, strong reversal: a bullish candle, a doji that gaps above it, then a bearish candle that gaps back below the doji — leaving it 'abandoned' in the middle.",
};

(() => {
  const chartEl = document.getElementById("chart");
  const symbolInput = document.getElementById("symbol-input");
  const loadBtn = document.getElementById("load-btn");
  const connDot = document.getElementById("conn-dot");
  const connLabel = document.getElementById("conn-label");
  const lastPriceEl = document.getElementById("last-price");
  const priceChangeEl = document.getElementById("price-change");
  const trendBadge = document.getElementById("trend-badge");
  const chartSymbolEl = document.getElementById("chart-symbol");
  const chartSymbolDescEl = document.getElementById("chart-symbol-desc");
  const patternListEl = document.getElementById("pattern-list");
  const levelListEl = document.getElementById("level-list");
  const periodButtonsEl = document.getElementById("period-buttons");
  const intervalRowEl = document.getElementById("interval-row");
  const intervalButtonsEl = document.getElementById("interval-buttons");
  const dataNoteEl = document.getElementById("data-note");
  const suggestionsEl = document.getElementById("symbol-suggestions");
  const confidenceFilterEl = document.getElementById("confidence-filter");

  const startScreen = document.getElementById("start-screen");
  const appShell = document.getElementById("app-shell");
  const homeBtn = document.getElementById("home-btn");
  const aboutModal = document.getElementById("about-modal");
  const settingsModal = document.getElementById("settings-modal");
  const apiKeyInput = document.getElementById("api-key-input");
  const apiKeyCurrentEl = document.getElementById("api-key-current");
  const apiKeyMessageEl = document.getElementById("api-key-message");
  const apiKeyToggleBtn = document.getElementById("api-key-toggle");
  const apiKeyCheckBtn = document.getElementById("api-key-check");
  const apiKeySaveBtn = document.getElementById("api-key-save");
  const patternDetailModal = document.getElementById("pattern-detail-modal");
  const advisorModal = document.getElementById("advisor-modal");
  const advisorSymbolLabelEl = document.getElementById("advisor-symbol-label");
  const advisorHorizonEl = document.getElementById("advisor-horizon");
  const advisorAnalyzeBtn = document.getElementById("advisor-analyze");
  const advisorLoadingEl = document.getElementById("advisor-loading");
  const advisorErrorEl = document.getElementById("advisor-error");
  const advisorResultsEl = document.getElementById("advisor-results");
  const advisorShowChartCheckbox = document.getElementById("advisor-show-chart");

  const chart = LightweightCharts.createChart(chartEl, {
    layout: { background: { color: "transparent" }, textColor: "#c7ccd8" },
    grid: {
      vertLines: { color: "rgba(255,255,255,0.04)" },
      horzLines: { color: "rgba(255,255,255,0.04)" },
    },
    timeScale: { timeVisible: true, secondVisible: true, borderColor: "#232a38" },
    rightPriceScale: { borderColor: "#232a38" },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
  });

  const candleSeries = chart.addCandlestickSeries({
    upColor: "#26d99a", downColor: "#ff5c7a",
    borderUpColor: "#26d99a", borderDownColor: "#ff5c7a",
    wickUpColor: "#26d99a", wickDownColor: "#ff5c7a",
  });

  const resistanceSeries = chart.addLineSeries({ color: "#ff5c7a", lineWidth: 2, lineStyle: LightweightCharts.LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false });
  const supportSeries = chart.addLineSeries({ color: "#26d99a", lineWidth: 2, lineStyle: LightweightCharts.LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false });
  const trendSeries = chart.addLineSeries({ color: "#5b8cff", lineWidth: 2, priceLineVisible: false, lastValueVisible: false });

  // --- light/dark theme ---

  const THEME_KEY = "tohtoe_theme";
  const CHART_THEMES = {
    dark: { textColor: "#c7ccd8", grid: "rgba(255,255,255,0.04)", border: "#232a38" },
    light: { textColor: "#3a3f4b", grid: "rgba(0,0,0,0.06)", border: "#dde1e8" },
  };
  const MOON_ICON = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>';
  const SUN_ICON = '<circle cx="12" cy="12" r="4"></circle><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"></path>';

  function applyChartTheme(theme) {
    const t = CHART_THEMES[theme] || CHART_THEMES.dark;
    chart.applyOptions({
      layout: { textColor: t.textColor },
      grid: { vertLines: { color: t.grid }, horzLines: { color: t.grid } },
      timeScale: { borderColor: t.border },
      rightPriceScale: { borderColor: t.border },
    });
  }

  function setTheme(theme) {
    localStorage.setItem(THEME_KEY, theme);
    document.documentElement.setAttribute("data-theme", theme);
    applyChartTheme(theme);
    const t = CHART_THEMES[theme] || CHART_THEMES.dark;
    Object.values(indicatorCharts).forEach((ic) => {
      ic.chart.applyOptions({
        layout: { textColor: t.textColor },
        grid: { vertLines: { color: t.grid }, horzLines: { color: t.grid } },
        rightPriceScale: { borderColor: t.border },
      });
    });
    drawAllDrawings();
    drawVolumeProfile();
    const icon = theme === "light" ? SUN_ICON : MOON_ICON;
    ["theme-icon-dash", "theme-icon-start"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = icon;
    });
  }

  function toggleTheme() {
    const current = localStorage.getItem(THEME_KEY) || "dark";
    setTheme(current === "dark" ? "light" : "dark");
  }

  // --- PNG export ---

  function exportChartPng() {
    const shot = chart.takeScreenshot();
    const theme = localStorage.getItem(THEME_KEY) || "dark";
    const bg = theme === "light" ? "#f5f6f9" : "#0b0e14";
    const canvas = document.createElement("canvas");
    canvas.width = shot.width;
    canvas.height = shot.height;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(shot, 0, 0);
    const link = document.createElement("a");
    link.download = `${currentSymbol || "chart"}_${currentPeriod || "chart"}.png`;
    link.href = canvas.toDataURL("image/png");
    link.click();
  }

  let levelPriceLines = [];
  let ws = null;
  let currentSymbol = symbolInput.value.trim().toUpperCase();
  let currentPeriod = "LIVE";
  let currentInterval = "";

  // --- extended-hours (pre/post-market) toggle ---
  const PREPOST_KEY = "tohtoe_prepost";
  const PREPOST_PERIODS = new Set(["1D", "1W"]);
  let prepostEnabled = localStorage.getItem(PREPOST_KEY) === "1";
  const prepostBtn = document.getElementById("toggle-prepost");

  function updatePrepostToggle(period) {
    const applicable = PREPOST_PERIODS.has(period);
    prepostBtn.classList.toggle("hidden-screen", !applicable);
    prepostBtn.classList.toggle("active", applicable && prepostEnabled);
  }

  // Which candle intervals Yahoo will serve for each period's range, and the
  // default interval that period already used before this selector existed --
  // mirrors backend/history.py's INTERVAL_COMPAT / RANGE_INTERVAL_PRESETS.
  const INTERVAL_COMPAT = {
    "1D": ["1m", "5m", "15m", "30m", "1h", "1d"],
    "1W": ["1m", "5m", "15m", "30m", "1h", "1d"],
    "1M": ["5m", "15m", "30m", "1h", "1d"],
    "3M": ["1h", "1d"],
    "1Y": ["1h", "1d", "1wk"],
    "5Y": ["1d", "1wk"],
  };
  const INTERVAL_DEFAULTS = { "1D": "5m", "1W": "15m", "1M": "1d", "3M": "1d", "1Y": "1wk", "5Y": "1wk" };
  const INTERVAL_LABELS = { "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "1h", "1d": "1D", "1wk": "1W" };
  let lastClose = null;
  let firstClose = null;
  let lastMarkers = [];
  let lastCandles = [];
  const activeConfidence = new Set(["high", "medium", "low"]);

  new ResizeObserver(() => {
    chart.applyOptions({ width: chartEl.clientWidth, height: chartEl.clientHeight });
    drawVolumeProfile();
    drawAllDrawings();
  }).observe(chartEl);

  chart.subscribeClick((param) => {
    if (!param || param.time === undefined) return;
    const match = lastMarkers.find((m) => m.time === param.time && activeConfidence.has(m.confidence));
    if (match) openPatternDetail(match);
  });

  function setConn(state, label) {
    connDot.classList.remove("online", "offline", "historical");
    connDot.classList.add(state);
    connLabel.textContent = label;
  }

  function setDataNote(text) {
    dataNoteEl.textContent = text || "";
  }

  function fmt(n) {
    if (n === null || n === undefined || Number.isNaN(n)) return "--";
    return n.toFixed(n >= 100 ? 2 : 4);
  }

  // --- Thailand time (ICT, UTC+7, no DST) ---
  // Lightweight Charts renders timestamps as UTC digits, so every incoming
  // timestamp is shifted by the Thailand offset once at ingestion; the chart
  // then displays the shifted value's UTC digits, which are Thailand's
  // actual wall-clock time. All downstream state (lastCandles, lastMarkers,
  // click-to-detail matching) works in this same shifted space, and any
  // human-readable formatting below must format it as UTC too -- otherwise
  // the browser would apply its own local timezone on top and double-shift.
  const THAILAND_OFFSET_SECONDS = 7 * 3600;

  function shiftTime(t) {
    return t + THAILAND_OFFSET_SECONDS;
  }

  function shiftCandle(c) {
    return { ...c, time: shiftTime(c.time) };
  }

  function shiftPoint(p) {
    return p ? { time: shiftTime(p.time), value: p.value } : p;
  }

  function shiftOverlay(overlay) {
    if (!overlay) return overlay;
    return {
      resistance: overlay.resistance ? { start: shiftPoint(overlay.resistance.start), end: shiftPoint(overlay.resistance.end) } : null,
      support: overlay.support ? { start: shiftPoint(overlay.support.start), end: shiftPoint(overlay.support.end) } : null,
      trend: overlay.trend ? { start: shiftPoint(overlay.trend.start), end: shiftPoint(overlay.trend.end), direction: overlay.trend.direction } : null,
      levels: overlay.levels,
    };
  }

  function shiftMarkers(markers) {
    return (markers || []).map((m) => ({ ...m, time: shiftTime(m.time) }));
  }

  function formatThaiTime(shiftedSeconds) {
    return new Date(shiftedSeconds * 1000).toLocaleString(undefined, { timeZone: "UTC" }) + " ICT";
  }

  function updatePriceHeader(price) {
    const prevClose = lastClose;
    lastPriceEl.textContent = fmt(price);
    if (firstClose === null) firstClose = price;
    const change = price - firstClose;
    const pct = firstClose ? (change / firstClose) * 100 : 0;
    priceChangeEl.textContent = `${change >= 0 ? "+" : ""}${fmt(change)} (${pct.toFixed(2)}%)`;
    priceChangeEl.classList.toggle("up", change >= 0);
    priceChangeEl.classList.toggle("down", change < 0);

    if (prevClose !== null && price !== prevClose) {
      lastPriceEl.classList.remove("flash-up", "flash-down");
      void lastPriceEl.offsetWidth; // restart animation
      lastPriceEl.classList.add(price > prevClose ? "flash-up" : "flash-down");
    }
    lastClose = price;
  }

  function applyOverlay(overlay) {
    if (!overlay) return;
    resistanceSeries.setData(overlay.resistance ? [overlay.resistance.start, overlay.resistance.end] : []);
    supportSeries.setData(overlay.support ? [overlay.support.start, overlay.support.end] : []);
    trendSeries.setData(overlay.trend ? [overlay.trend.start, overlay.trend.end] : []);

    trendBadge.textContent = `trend: ${overlay.trend ? overlay.trend.direction : "--"}`;

    levelPriceLines.forEach((pl) => candleSeries.removePriceLine(pl));
    levelPriceLines = [];
    (overlay.levels || []).forEach((lvl) => {
      const pl = candleSeries.createPriceLine({
        price: lvl, color: "#ffb84d", lineWidth: 1,
        lineStyle: LightweightCharts.LineStyle.Dotted, axisLabelVisible: true,
        title: "S/R",
      });
      levelPriceLines.push(pl);
    });

    levelListEl.innerHTML = "";
    if (!overlay.levels || overlay.levels.length === 0) {
      levelListEl.innerHTML = '<li class="empty">No clear levels yet</li>';
    } else {
      overlay.levels.slice().reverse().forEach((lvl, idx) => {
        const li = document.createElement("li");
        li.style.setProperty("--i", `${idx * 35}ms`);
        li.innerHTML = `<span>Level</span><strong>${fmt(lvl)}</strong>`;
        levelListEl.appendChild(li);
      });
    }
  }

  function renderMarkerChart(markers) {
    const dirColor = { bullish: "#26d99a", bearish: "#ff5c7a", neutral: "#ffb84d" };
    const dirShape = { bullish: "arrowUp", bearish: "arrowDown", neutral: "circle" };
    const patternMarkers = markers.map((m) => ({
      time: m.time,
      position: m.direction === "bearish" ? "aboveBar" : "belowBar",
      color: dirColor[m.direction] || "#5b8cff",
      shape: dirShape[m.direction] || "circle",
      text: m.pattern,
    }));
    const allMarkers = [...patternMarkers, ...computeCalendarChartMarkers()].sort((a, b) => a.time - b.time);
    candleSeries.setMarkers(allMarkers);
  }

  function ohlcCell(label, value) {
    return `<div class="ohlc-cell"><span class="ohlc-label">${label}</span><span class="ohlc-value">${fmt(value)}</span></div>`;
  }

  function openPatternDetail(marker) {
    document.getElementById("pd-name").textContent = marker.pattern;

    const dirEl = document.getElementById("pd-direction");
    dirEl.textContent = marker.direction;
    dirEl.className = `pattern-tag ${marker.direction}`;

    const confEl = document.getElementById("pd-confidence");
    confEl.textContent = `${marker.confidence} confidence · ${marker.strength}`;
    confEl.className = `confidence-pill ${marker.confidence}`;

    document.getElementById("pd-time").textContent = formatThaiTime(marker.time);
    document.getElementById("pd-description").textContent =
      PATTERN_INFO[marker.pattern] || "No description available for this pattern yet.";

    const candle = lastCandles.find((c) => c.time === marker.time);
    const ohlcEl = document.getElementById("pd-ohlc");
    ohlcEl.innerHTML = candle
      ? [ohlcCell("Open", candle.open), ohlcCell("High", candle.high), ohlcCell("Low", candle.low), ohlcCell("Close", candle.close)].join("")
      : "";

    patternDetailModal.classList.add("open");
  }

  function renderMarkerList(markers) {
    patternListEl.innerHTML = "";
    if (markers.length === 0) {
      patternListEl.innerHTML = '<li class="empty">No patterns match the current filter</li>';
      return;
    }
    markers.slice().reverse().slice(0, 12).forEach((m, idx) => {
      const li = document.createElement("li");
      li.style.setProperty("--i", `${idx * 35}ms`);
      const time = formatThaiTime(m.time);
      li.innerHTML = `
        <span class="pattern-left">
          <span class="confidence-dot ${m.confidence}" title="${m.confidence} confidence"></span>
          <span class="pattern-name">${m.pattern}</span>
          <span class="text-dim">@ ${time}</span>
        </span>
        <span class="pattern-tag ${m.direction}">${m.direction}</span>`;
      li.addEventListener("click", () => openPatternDetail(m));
      patternListEl.appendChild(li);
    });
  }

  function renderMarkers() {
    const filtered = lastMarkers.filter((m) => activeConfidence.has(m.confidence));
    renderMarkerChart(filtered);
    renderMarkerList(filtered);
  }

  function applyMarkers(markers) {
    lastMarkers = markers || [];
    renderMarkers();
  }

  confidenceFilterEl.querySelectorAll(".conf-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const conf = btn.dataset.conf;
      if (activeConfidence.has(conf)) {
        if (activeConfidence.size === 1) return; // always keep at least one tier visible
        activeConfidence.delete(conf);
        btn.classList.remove("active");
      } else {
        activeConfidence.add(conf);
        btn.classList.add("active");
      }
      renderMarkers();
    });
  });

  function updatePeriodButtons() {
    periodButtonsEl.querySelectorAll(".period-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.period === currentPeriod);
    });
  }

  function renderIntervalButtons(period) {
    const options = INTERVAL_COMPAT[period];
    if (!options) {
      // LIVE has no Yahoo interval to pick (it's our own 1-second tick candles).
      intervalRowEl.classList.add("hidden-screen");
      intervalButtonsEl.innerHTML = "";
      return;
    }
    intervalRowEl.classList.remove("hidden-screen");
    const active = currentInterval && options.includes(currentInterval) ? currentInterval : INTERVAL_DEFAULTS[period];
    intervalButtonsEl.innerHTML = options.map((iv) =>
      `<button class="period-btn${iv === active ? " active" : ""}" data-interval="${iv}">${INTERVAL_LABELS[iv] || iv}</button>`
    ).join("");
    intervalButtonsEl.querySelectorAll(".period-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        currentInterval = btn.dataset.interval;
        selectPeriod(currentPeriod, { allowFallback: false });
      });
    });
  }

  function applyTimeScaleFormatting(period) {
    chart.applyOptions({
      timeScale: {
        timeVisible: period === "LIVE" || period === "1D" || period === "1W",
        secondVisible: period === "LIVE",
      },
    });
  }

  function teardownWs() {
    if (ws) {
      ws.onclose = null;
      ws.close();
      ws = null;
    }
  }

  function clearChart() {
    candleSeries.setData([]);
    resistanceSeries.setData([]);
    supportSeries.setData([]);
    trendSeries.setData([]);
    lastCandles = [];
    patternListEl.innerHTML = '<li class="empty">Loading…</li>';
    levelListEl.innerHTML = '<li class="empty">Loading…</li>';
    trendBadge.textContent = "trend: --";
    clearAdvisorChartLines();
  }

  async function selectPeriod(period, { auto = false, resetPrice = true, allowFallback = true } = {}) {
    currentPeriod = period;
    updatePeriodButtons();
    renderIntervalButtons(period);
    updatePrepostToggle(period);
    applyTimeScaleFormatting(period);
    teardownWs();
    clearChart();
    setDataNote(auto ? "Live data isn't flowing right now — showing the most recent session instead." : "");
    if (resetPrice) { firstClose = null; lastClose = null; }

    try {
      const options = INTERVAL_COMPAT[period];
      const intervalParam = options
        ? (currentInterval && options.includes(currentInterval) ? currentInterval : INTERVAL_DEFAULTS[period])
        : "";
      const prepostParam = PREPOST_PERIODS.has(period) && prepostEnabled ? "&prepost=1" : "";
      const url = `/api/history/${encodeURIComponent(currentSymbol)}?period=${period}` + (intervalParam ? `&interval=${intervalParam}` : "") + prepostParam;
      const resp = await fetch(url);
      const data = await resp.json();

      if (data.interval) {
        // Reflect the interval the backend actually used (it silently
        // clamps incompatible combos) so the active button stays honest.
        currentInterval = data.interval;
        renderIntervalButtons(period);
      }

      if (data.candles && data.candles.length) {
        const shiftedCandles = data.candles.map(shiftCandle);
        firstClose = data.candles[0].open;
        lastCandles = shiftedCandles;
        candleSeries.setData(shiftedCandles);
        updatePriceHeader(shiftedCandles[shiftedCandles.length - 1].close);
        applyOverlay(shiftOverlay(data.overlay));
        applyMarkers(shiftMarkers(data.candlestick_markers));
        chart.timeScale().fitContent();
        refreshChartExtras();
      } else if (period === "LIVE" && !auto && allowFallback) {
        // Used only for the initial/default load so users don't land on a
        // blank chart -- an explicit click on the Live tab must actually
        // switch to Live, not silently bounce back to a historical tab.
        await selectPeriod("1D", { auto: true, resetPrice: false });
        return;
      } else if (period === "LIVE") {
        setDataNote("No live ticks yet — waiting for the market to open or the feed to connect.");
        patternListEl.innerHTML = '<li class="empty">Waiting for live data…</li>';
        levelListEl.innerHTML = '<li class="empty">Waiting for live data…</li>';
      } else {
        setDataNote("No data available for this range right now.");
      }
    } catch (e) {
      console.error("history fetch failed", e);
      setDataNote("Couldn't load data for this range.");
    }

    if (period === "LIVE") {
      connectWs(currentSymbol);
    } else {
      setConn("historical", `historical · ${period} · ${currentSymbol}`);
    }
  }

  let symbolTitleRequestId = 0;

  async function updateSymbolTitle(symbol) {
    chartSymbolEl.textContent = symbol;
    chartSymbolDescEl.textContent = "";
    const requestId = ++symbolTitleRequestId;
    try {
      const resp = await fetch(`/api/symbols/search?q=${encodeURIComponent(symbol)}`);
      const data = await resp.json();
      if (requestId !== symbolTitleRequestId) return; // a newer symbol was picked meanwhile
      const exact = (data.results || []).find((r) => r.symbol === symbol);
      chartSymbolDescEl.textContent = exact ? `${exact.description} · ${exact.exchange}` : "";
    } catch (e) {
      // no company name available (e.g. crypto pairs) -- title-only is fine
    }
  }

  async function loadSymbol(symbol) {
    symbol = symbol.trim().toUpperCase();
    if (!symbol) return;
    currentSymbol = symbol;
    firstClose = null;
    lastClose = null;
    pushRecent(symbol);
    updateSymbolTitle(symbol);
    refreshWatchlistStar();
    clearCompare();
    await selectPeriod("LIVE");
  }

  function connectWs(symbol) {
    teardownWs();
    setConn("offline", "connecting…");
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/ws/${encodeURIComponent(symbol)}`);

    ws.onopen = () => setConn("online", `live · ${symbol}`);
    ws.onclose = () => { if (currentPeriod === "LIVE") setConn("offline", "disconnected"); };
    ws.onerror = () => { if (currentPeriod === "LIVE") setConn("offline", "error"); };

    ws.onmessage = (evt) => {
      if (currentPeriod !== "LIVE") return;
      const msg = JSON.parse(evt.data);
      if (msg.symbol !== currentSymbol) return;

      if (msg.type === "candle_update" && msg.candle) {
        const shifted = shiftCandle(msg.candle);
        candleSeries.update(shifted);
        updatePriceHeader(shifted.close);
        if (lastCandles.length && lastCandles[lastCandles.length - 1].time === shifted.time) {
          lastCandles[lastCandles.length - 1] = shifted;
        } else {
          lastCandles.push(shifted);
        }
      } else if (msg.type === "analysis") {
        applyOverlay(shiftOverlay(msg.overlay));
        applyMarkers(shiftMarkers(msg.candlestick_markers));
      }
    };
  }

  // --- symbol search dropdown ---

  let suggestionResults = [];
  let suggestionActiveIndex = -1;
  let searchDebounce = null;

  function closeSuggestions() {
    suggestionsEl.classList.remove("open");
    suggestionsEl.innerHTML = "";
    suggestionResults = [];
    suggestionActiveIndex = -1;
  }

  function renderSuggestions() {
    suggestionsEl.innerHTML = "";
    if (suggestionResults.length === 0) {
      suggestionsEl.innerHTML = '<li class="empty">No matches</li>';
    } else {
      suggestionResults.forEach((item, idx) => {
        const li = document.createElement("li");
        li.className = idx === suggestionActiveIndex ? "active" : "";
        li.innerHTML = `<span class="sym-ticker">${item.symbol}</span><span class="sym-desc">${item.description}</span><span class="sym-exchange">${item.exchange}</span>`;
        li.addEventListener("mousedown", (e) => {
          e.preventDefault();
          pickSuggestion(item);
        });
        suggestionsEl.appendChild(li);
      });
    }
    suggestionsEl.classList.add("open");
  }

  function pickSuggestion(item) {
    symbolInput.value = item.symbol;
    closeSuggestions();
    loadSymbol(item.symbol);
  }

  async function fetchSuggestions(query) {
    try {
      const resp = await fetch(`/api/symbols/search?q=${encodeURIComponent(query)}`);
      const data = await resp.json();
      suggestionResults = data.results || [];
      suggestionActiveIndex = -1;
      renderSuggestions();
    } catch (e) {
      console.error("symbol search failed", e);
    }
  }

  symbolInput.addEventListener("input", () => {
    const q = symbolInput.value.trim();
    clearTimeout(searchDebounce);
    if (q.length < 1) {
      closeSuggestions();
      return;
    }
    searchDebounce = setTimeout(() => fetchSuggestions(q), 200);
  });

  symbolInput.addEventListener("keydown", (e) => {
    if (suggestionsEl.classList.contains("open") && suggestionResults.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        suggestionActiveIndex = Math.min(suggestionActiveIndex + 1, suggestionResults.length - 1);
        renderSuggestions();
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        suggestionActiveIndex = Math.max(suggestionActiveIndex - 1, 0);
        renderSuggestions();
        return;
      }
      if (e.key === "Escape") {
        closeSuggestions();
        return;
      }
      if (e.key === "Enter" && suggestionActiveIndex >= 0) {
        e.preventDefault();
        pickSuggestion(suggestionResults[suggestionActiveIndex]);
        return;
      }
    }
    if (e.key === "Enter") {
      closeSuggestions();
      loadSymbol(symbolInput.value);
    }
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".symbol-search-wrap")) closeSuggestions();
  });

  loadBtn.addEventListener("click", () => { closeSuggestions(); loadSymbol(symbolInput.value); });
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      symbolInput.value = chip.dataset.symbol;
      closeSuggestions();
      loadSymbol(chip.dataset.symbol);
    });
  });
  periodButtonsEl.querySelectorAll(".period-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      currentInterval = ""; // switching ranges resets to that range's default granularity
      selectPeriod(btn.dataset.period, { allowFallback: false });
    });
  });

  prepostBtn.addEventListener("click", () => {
    prepostEnabled = !prepostEnabled;
    localStorage.setItem(PREPOST_KEY, prepostEnabled ? "1" : "0");
    selectPeriod(currentPeriod, { allowFallback: false });
  });

  // --- start screen: recent symbols, navigation, about modal ---

  const RECENTS_KEY = "tohtoe_recents";

  function getRecents() {
    try { return JSON.parse(localStorage.getItem(RECENTS_KEY)) || []; } catch (e) { return []; }
  }

  function pushRecent(symbol) {
    let list = getRecents().filter((s) => s !== symbol);
    list.unshift(symbol);
    localStorage.setItem(RECENTS_KEY, JSON.stringify(list.slice(0, 6)));
  }

  function renderRecents() {
    const list = getRecents();
    const chipsEl = document.getElementById("recent-chips");
    const subEl = document.getElementById("recent-sub");
    chipsEl.innerHTML = "";
    if (list.length === 0) {
      subEl.textContent = "Nothing yet";
      chipsEl.style.display = "none";
      return;
    }
    subEl.textContent = list.slice(0, 3).join(" · ");
    chipsEl.style.display = "flex";
    list.forEach((sym) => {
      const chip = document.createElement("button");
      chip.className = "recent-chip";
      chip.textContent = sym;
      chip.addEventListener("click", () => enterApp(sym));
      chipsEl.appendChild(chip);
    });
  }

  // --- "what changed" digest ---

  const DIGEST_KEY = "tohtoe_digest_snapshot";
  const DIGEST_MOVE_THRESHOLD = 3; // percent
  let digestRequestId = 0;

  async function renderDigest() {
    const requestId = ++digestRequestId;
    const digestCard = document.getElementById("digest-card");
    const digestItemsEl = document.getElementById("digest-items");
    try {
      const resp = await fetch("/api/watchlist/quotes");
      const data = await resp.json();
      if (requestId !== digestRequestId) return; // a newer call already landed
      const quotes = data.quotes || [];
      if (!quotes.length) { digestCard.classList.add("hidden-screen"); return; }

      let snapshot = {};
      try { snapshot = JSON.parse(localStorage.getItem(DIGEST_KEY)) || {}; } catch (e) { snapshot = {}; }

      const items = [];
      quotes.forEach((q) => {
        const prev = snapshot[q.symbol];
        if (!prev) return;
        if (prev.price != null && q.price != null && prev.price !== 0) {
          const movePct = ((q.price - prev.price) / prev.price) * 100;
          if (Math.abs(movePct) >= DIGEST_MOVE_THRESHOLD) {
            items.push({
              symbol: q.symbol, cls: movePct >= 0 ? "up" : "down",
              text: `${movePct >= 0 ? "+" : ""}${movePct.toFixed(1)}% since last check`,
            });
          }
        }
        if (prev.verdict && q.last_verdict && prev.verdict !== q.last_verdict) {
          items.push({ symbol: q.symbol, cls: "flip", text: `Verdict changed: ${prev.verdict} → ${q.last_verdict}` });
        }
      });

      const newSnapshot = {};
      quotes.forEach((q) => { newSnapshot[q.symbol] = { price: q.price, verdict: q.last_verdict }; });
      localStorage.setItem(DIGEST_KEY, JSON.stringify(newSnapshot));

      if (!items.length) { digestCard.classList.add("hidden-screen"); return; }
      digestItemsEl.innerHTML = items.map((it) => `
        <div class="digest-item ${it.cls}">
          <span class="digest-item-symbol">${escapeHtml(it.symbol)}</span>
          <span class="digest-item-text">${escapeHtml(it.text)}</span>
        </div>`).join("");
      digestCard.classList.remove("hidden-screen");
    } catch (e) {
      digestCard.classList.add("hidden-screen");
    }
  }

  function enterApp(symbol) {
    startScreen.classList.add("leaving");
    setTimeout(() => {
      startScreen.classList.add("hidden-screen");
      startScreen.classList.remove("leaving");
      appShell.classList.remove("hidden-screen");
    }, 420);
    symbolInput.value = symbol;
    loadSymbol(symbol);
  }

  function showStartScreen() {
    teardownWs();
    appShell.classList.add("leaving-app");
    setTimeout(() => {
      appShell.classList.add("hidden-screen");
      appShell.classList.remove("leaving-app");
      startScreen.classList.remove("hidden-screen");
      renderRecents();
      renderDigest();
    }, 300);
  }

  document.getElementById("menu-live").addEventListener("click", () => {
    const recents = getRecents();
    enterApp(recents[0] || "AAPL");
  });
  document.getElementById("menu-search").addEventListener("click", () => {
    const recents = getRecents();
    enterApp(recents[0] || "AAPL");
    setTimeout(() => { symbolInput.focus(); symbolInput.select(); }, 480);
  });
  document.getElementById("menu-recent").addEventListener("click", () => {
    const recents = getRecents();
    if (recents.length === 0) return;
    enterApp(recents[0]);
  });
  document.getElementById("menu-about").addEventListener("click", () => aboutModal.classList.add("open"));
  document.getElementById("about-close").addEventListener("click", () => aboutModal.classList.remove("open"));
  aboutModal.addEventListener("click", (e) => { if (e.target === aboutModal) aboutModal.classList.remove("open"); });

  document.getElementById("pattern-detail-close").addEventListener("click", () => patternDetailModal.classList.remove("open"));
  patternDetailModal.addEventListener("click", (e) => { if (e.target === patternDetailModal) patternDetailModal.classList.remove("open"); });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      aboutModal.classList.remove("open");
      settingsModal.classList.remove("open");
      patternDetailModal.classList.remove("open");
      advisorModal.classList.remove("open");
    }
  });

  homeBtn.addEventListener("click", showStartScreen);

  // --- settings: API key management ---

  async function refreshApiKeyStatus() {
    apiKeyCurrentEl.textContent = "Loading…";
    try {
      const resp = await fetch("/api/settings/api-key");
      const data = await resp.json();
      apiKeyCurrentEl.textContent = data.is_set ? `Current key: ${data.masked}` : "No API key saved yet.";
    } catch (e) {
      apiKeyCurrentEl.textContent = "Couldn't load current key status.";
    }
  }

  function openSettings() {
    apiKeyInput.value = "";
    apiKeyInput.type = "password";
    apiKeyToggleBtn.textContent = "Show";
    apiKeyMessageEl.textContent = "";
    apiKeyMessageEl.className = "api-key-message";
    settingsModal.classList.add("open");
    refreshApiKeyStatus();
  }

  apiKeyToggleBtn.addEventListener("click", () => {
    const showing = apiKeyInput.type === "text";
    apiKeyInput.type = showing ? "password" : "text";
    apiKeyToggleBtn.textContent = showing ? "Show" : "Hide";
  });

  apiKeyCheckBtn.addEventListener("click", async () => {
    const key = apiKeyInput.value.trim();
    if (!key) {
      apiKeyMessageEl.textContent = "Enter a key first.";
      apiKeyMessageEl.className = "api-key-message warn";
      return;
    }
    apiKeyMessageEl.textContent = "Checking…";
    apiKeyMessageEl.className = "api-key-message";
    try {
      const resp = await fetch("/api/settings/api-key/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: key }),
      });
      const data = await resp.json();
      apiKeyMessageEl.textContent = data.message;
      apiKeyMessageEl.className = `api-key-message ${data.valid ? "ok" : "err"}`;
    } catch (e) {
      apiKeyMessageEl.textContent = "Couldn't reach the app backend to check the key.";
      apiKeyMessageEl.className = "api-key-message err";
    }
  });

  apiKeySaveBtn.addEventListener("click", async () => {
    const key = apiKeyInput.value.trim();
    if (!key) {
      apiKeyMessageEl.textContent = "Enter a key first.";
      apiKeyMessageEl.className = "api-key-message warn";
      return;
    }
    apiKeyMessageEl.textContent = "Saving…";
    apiKeyMessageEl.className = "api-key-message";
    try {
      const resp = await fetch("/api/settings/api-key", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: key }),
      });
      const data = await resp.json();
      apiKeyMessageEl.textContent = data.message;
      apiKeyMessageEl.className = `api-key-message ${data.ok ? "ok" : "err"}`;
      if (data.ok) {
        apiKeyInput.value = "";
        refreshApiKeyStatus();
      }
    } catch (e) {
      apiKeyMessageEl.textContent = "Couldn't reach the app backend to save the key.";
      apiKeyMessageEl.className = "api-key-message err";
    }
  });

  document.getElementById("settings-btn-start").addEventListener("click", openSettings);
  document.getElementById("settings-btn-dash").addEventListener("click", openSettings);
  document.getElementById("settings-close").addEventListener("click", () => settingsModal.classList.remove("open"));
  settingsModal.addEventListener("click", (e) => { if (e.target === settingsModal) settingsModal.classList.remove("open"); });

  // --- advisor: buy/sell recommendations ---

  let advisorHorizon = "medium";
  let advisorPriceLines = [];
  let lastAdvisorResult = null;

  function selectAdvisorHorizon(horizon) {
    advisorHorizon = horizon;
    advisorHorizonEl.querySelectorAll(".period-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.horizon === horizon);
    });
  }

  function clearAdvisorChartLines() {
    advisorPriceLines.forEach((pl) => candleSeries.removePriceLine(pl));
    advisorPriceLines = [];
  }

  function applyAdvisorChartLines(result) {
    clearAdvisorChartLines();
    if (!advisorShowChartCheckbox.checked || !result || !result.buy) return;
    result.buy.forEach((tier) => {
      advisorPriceLines.push(candleSeries.createPriceLine({
        price: tier.price, color: "#26d99a", lineWidth: 1,
        lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: true,
        title: `Buy (${tier.tier})`,
      }));
    });
    result.sell.forEach((tier) => {
      advisorPriceLines.push(candleSeries.createPriceLine({
        price: tier.price, color: "#ff5c7a", lineWidth: 1,
        lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: true,
        title: `Sell (${tier.tier})`,
      }));
    });
    if (result.stop_loss) {
      advisorPriceLines.push(candleSeries.createPriceLine({
        price: result.stop_loss, color: "#ff8080", lineWidth: 2,
        lineStyle: LightweightCharts.LineStyle.Solid, axisLabelVisible: true,
        title: "Stop",
      }));
    }
  }

  function advisorTierHtml(tier) {
    return `
      <div class="advisor-tier">
        <div class="advisor-tier-head">
          <span class="advisor-tier-label">${tier.tier}</span>
          <span class="advisor-tier-price">${fmt(tier.price)}</span>
        </div>
        <div class="advisor-tier-rationale">${tier.rationale}</div>
      </div>`;
  }

  function renderAdvisorTimeframes(timeframes) {
    if (!timeframes || !timeframes.length) return "";
    const arrow = { up: "▲", down: "▼", flat: "→" };
    return timeframes.map((tf) => `
      <span class="advisor-tf-chip ${tf.direction}">
        <span class="advisor-tf-chip-label">${tf.label}</span>${arrow[tf.direction] || "→"}
      </span>`).join("");
  }

  function renderAdvisorFactors(factors) {
    const labels = { technical: "Technical", fundamental: "Fundamental", street: "Analyst / News / Insiders", macro: "Market & External" };
    return Object.entries(factors).map(([key, group]) => {
      const items = group.items.map((item) => `
        <div class="advisor-factor-item">
          <span class="advisor-factor-item-name">${item.name} (${item.score >= 0 ? "+" : ""}${item.score})</span>
          <span class="advisor-factor-item-detail">${item.detail}</span>
        </div>`).join("");
      return `
        <details class="advisor-factor-group">
          <summary>${labels[key] || key} <span class="advisor-factor-group-weight">weight ${Math.round(group.weight * 100)}% · score ${group.score >= 0 ? "+" : ""}${group.score}</span></summary>
          ${items}
        </details>`;
    }).join("");
  }

  function renderPositionSizer(data) {
    const outEl = document.getElementById("sizer-output");
    if (!data || data.stop_loss == null || data.current_price == null) { outEl.innerHTML = ""; return; }
    const account = parseFloat(document.getElementById("sizer-account").value) || 0;
    const riskPct = parseFloat(document.getElementById("sizer-risk-pct").value) || 0;
    const perShareRisk = data.current_price - data.stop_loss;
    if (perShareRisk <= 0 || account <= 0 || riskPct <= 0) {
      outEl.innerHTML = `<span class="warn">Enter an account size and risk % to size a position.</span>`;
      return;
    }
    const riskBudget = account * (riskPct / 100);
    const shares = Math.floor(riskBudget / perShareRisk);
    if (shares <= 0) {
      outEl.innerHTML = `<span class="warn">Risk budget too small for even 1 share at this stop distance ($${fmt(perShareRisk)}/share).</span>`;
      return;
    }
    const cost = shares * data.current_price;
    outEl.innerHTML = `<strong>${shares}</strong> shares (~$${fmt(cost)}) risks <strong>$${fmt(riskBudget)}</strong> (${riskPct}% of account) if the stop at ${fmt(data.stop_loss)} is hit.`;
  }

  function renderConfidenceSparkline(runs) {
    const rowEl = document.getElementById("advisor-sparkline-row");
    if (!runs || runs.length < 2) { rowEl.innerHTML = ""; return; }
    const w = 160, h = 32, pad = 2;
    const confs = runs.map((r) => r.confidence);
    const min = Math.min(...confs), max = Math.max(...confs);
    const range = max - min || 1;
    const points = runs.map((r, i) => {
      const x = pad + (i / (runs.length - 1)) * (w - pad * 2);
      const y = h - pad - ((r.confidence - min) / range) * (h - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
    const last = runs[runs.length - 1];
    rowEl.innerHTML = `
      <span class="advisor-sparkline-label">Confidence trend (${runs.length} calls)</span>
      <svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><polyline points="${points}" fill="none" stroke="var(--accent)" stroke-width="1.5"></polyline></svg>
      <span class="advisor-sparkline-label">now ${Math.round(last.confidence * 100)}%</span>`;
  }

  async function loadAdvisorHistory(symbol) {
    try {
      const resp = await fetch(`/api/advisor-history/${encodeURIComponent(symbol)}?limit=30`);
      const data = await resp.json();
      renderConfidenceSparkline(data.runs || []);
    } catch (e) {
      document.getElementById("advisor-sparkline-row").innerHTML = "";
    }
  }

  async function loadTrackRecord() {
    const el = document.getElementById("advisor-track-record");
    try {
      const resp = await fetch("/api/advisor-accuracy");
      const data = await resp.json();
      const stats = data.stats || [];
      const totalHits = stats.reduce((s, x) => s + x.hits, 0);
      const totalCalls = stats.reduce((s, x) => s + x.total, 0);
      if (totalCalls === 0) { el.innerHTML = ""; return; }
      const rate = Math.round((totalHits / totalCalls) * 100);
      el.innerHTML = `Advisor track record: <strong>${rate}%</strong> over ${totalCalls} scored call${totalCalls === 1 ? "" : "s"}`;
    } catch (e) {
      el.innerHTML = "";
    }
  }

  function renderAdvisorResults(data) {
    lastAdvisorResult = data;
    const verdictEl = document.getElementById("advisor-verdict");
    const confidenceEl = document.getElementById("advisor-confidence");
    verdictEl.textContent = data.verdict;
    verdictEl.className = `advisor-verdict ${data.verdict.toLowerCase().replace(/\s+/g, "-")}`;
    const tfLabels = (data.timeframes || []).map((tf) => tf.label).join("+");
    confidenceEl.textContent = `${Math.round(data.confidence * 100)}% confidence · ${tfLabels ? tfLabels + " analyzed · " : ""}${data.horizon_label || data.horizon}`;

    document.getElementById("advisor-tf-chips").innerHTML = renderAdvisorTimeframes(data.timeframes);
    document.getElementById("advisor-summary").textContent = data.summary || "";
    renderPositionSizer(data);
    renderOptionsSentiment(data.options);

    document.getElementById("advisor-buy-tiers").innerHTML = data.buy.map(advisorTierHtml).join("");
    document.getElementById("advisor-sell-tiers").innerHTML = data.sell.map(advisorTierHtml).join("");
    document.getElementById("advisor-stop-loss").innerHTML = `<strong>Stop-loss:</strong> ${fmt(data.stop_loss)}`;

    const rrEl = document.getElementById("advisor-risk-reward");
    if (data.risk_reward) {
      rrEl.innerHTML = `<strong>Risk/Reward:</strong> ${data.risk_reward}:1 to the mid sell target`;
      rrEl.className = `advisor-risk-reward${data.risk_reward < 1.5 ? " poor" : ""}`;
      rrEl.classList.remove("hidden-screen");
    } else {
      rrEl.classList.add("hidden-screen");
    }

    const warningsEl = document.getElementById("advisor-warnings");
    warningsEl.innerHTML = (data.warnings || []).map((w) => `<div class="advisor-warning">⚠ ${w}</div>`).join("");

    document.getElementById("advisor-factors").innerHTML = renderAdvisorFactors(data.factors);

    advisorResultsEl.classList.remove("hidden-screen");
    applyAdvisorChartLines(data);
  }

  async function runAdvisorAnalysis() {
    advisorErrorEl.classList.add("hidden-screen");
    advisorResultsEl.classList.add("hidden-screen");
    advisorLoadingEl.classList.remove("hidden-screen");
    clearAdvisorChartLines();
    try {
      const resp = await fetch(`/api/advisor/${encodeURIComponent(currentSymbol)}?horizon=${advisorHorizon}`);
      const data = await resp.json();
      advisorLoadingEl.classList.add("hidden-screen");
      if (data.error) {
        advisorErrorEl.textContent = data.error;
        advisorErrorEl.classList.remove("hidden-screen");
        return;
      }
      renderAdvisorResults(data);
      loadAdvisorHistory(currentSymbol);
      loadTrackRecord();
    } catch (e) {
      advisorLoadingEl.classList.add("hidden-screen");
      advisorErrorEl.textContent = "Couldn't reach the app backend to run the analysis.";
      advisorErrorEl.classList.remove("hidden-screen");
    }
  }

  function openAdvisor() {
    advisorSymbolLabelEl.textContent = `· ${currentSymbol}`;
    advisorResultsEl.classList.add("hidden-screen");
    advisorErrorEl.classList.add("hidden-screen");
    advisorLoadingEl.classList.add("hidden-screen");
    advisorModal.classList.add("open");
  }

  // --- indicator sub-panes (RSI / MACD / ADX) ---

  const INDICATOR_PANES_KEY = "tohtoe_indicator_panes";
  const indicatorCharts = {};
  let syncingRange = false;

  function getEnabledPanes() {
    try { return JSON.parse(localStorage.getItem(INDICATOR_PANES_KEY)) || []; } catch (e) { return []; }
  }
  function setEnabledPanes(panes) {
    localStorage.setItem(INDICATOR_PANES_KEY, JSON.stringify(panes));
  }

  function createIndicatorPane(kind) {
    const el = document.getElementById(`${kind}-pane`);
    const theme = localStorage.getItem(THEME_KEY) || "dark";
    const t = CHART_THEMES[theme] || CHART_THEMES.dark;
    const paneChart = LightweightCharts.createChart(el, {
      layout: { background: { color: "transparent" }, textColor: t.textColor },
      grid: { vertLines: { color: t.grid }, horzLines: { color: t.grid } },
      timeScale: { visible: false, borderColor: t.border },
      rightPriceScale: { borderColor: t.border },
      crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
      handleScroll: false,
      handleScale: false,
    });
    const series = {};
    if (kind === "rsi") {
      series.rsi = paneChart.addLineSeries({ color: "#9d7bff", lineWidth: 1.5, priceLineVisible: false });
      series.rsi.createPriceLine({ price: 70, color: "#ff5c7a", lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dotted, axisLabelVisible: false });
      series.rsi.createPriceLine({ price: 30, color: "#26d99a", lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dotted, axisLabelVisible: false });
    } else if (kind === "macd") {
      series.hist = paneChart.addHistogramSeries({ priceLineVisible: false, lastValueVisible: false });
      series.macd = paneChart.addLineSeries({ color: "#5b8cff", lineWidth: 1.5, priceLineVisible: false });
      series.signal = paneChart.addLineSeries({ color: "#ffb84d", lineWidth: 1.5, priceLineVisible: false });
    } else if (kind === "adx") {
      series.adx = paneChart.addLineSeries({ color: "#5b8cff", lineWidth: 1.5, priceLineVisible: false });
      series.adx.createPriceLine({ price: 25, color: "#8a93a6", lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dotted, axisLabelVisible: false });
    }

    paneChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (syncingRange || !range) return;
      syncingRange = true;
      chart.timeScale().setVisibleLogicalRange(range);
      syncingRange = false;
    });

    // Unlike the main chart, createChart() only sizes to the container
    // once, at creation time -- if the pane is toggled on (or restored
    // from localStorage) while its container is momentarily zero-size
    // (e.g. mid start-screen transition), it would otherwise stay stuck
    // at 0x0 forever. Keep it sized the same way the main chart is.
    const resizeObserver = new ResizeObserver(() => {
      paneChart.applyOptions({ width: el.clientWidth, height: el.clientHeight });
    });
    resizeObserver.observe(el);

    indicatorCharts[kind] = { chart: paneChart, series, resizeObserver };
  }

  async function loadIndicatorData() {
    if (!Object.keys(indicatorCharts).length) return;
    try {
      const params = new URLSearchParams({ period: currentPeriod });
      if (currentInterval) params.set("interval", currentInterval);
      const resp = await fetch(`/api/indicators/${encodeURIComponent(currentSymbol)}?${params}`);
      const data = await resp.json();
      const series = (data.series || []).map(shiftCandle);
      if (indicatorCharts.rsi) {
        indicatorCharts.rsi.series.rsi.setData(series.filter((s) => s.rsi != null).map((s) => ({ time: s.time, value: s.rsi })));
      }
      if (indicatorCharts.macd) {
        indicatorCharts.macd.series.hist.setData(series.filter((s) => s.hist != null).map((s) => ({ time: s.time, value: s.hist, color: s.hist >= 0 ? "#26d99a" : "#ff5c7a" })));
        indicatorCharts.macd.series.macd.setData(series.filter((s) => s.macd != null).map((s) => ({ time: s.time, value: s.macd })));
        indicatorCharts.macd.series.signal.setData(series.filter((s) => s.signal != null).map((s) => ({ time: s.time, value: s.signal })));
      }
      if (indicatorCharts.adx) {
        indicatorCharts.adx.series.adx.setData(series.filter((s) => s.adx != null).map((s) => ({ time: s.time, value: s.adx })));
      }
    } catch (e) { /* non-critical */ }
  }

  function toggleIndicatorPane(kind) {
    const btn = document.getElementById(`toggle-${kind}`);
    const paneEl = document.getElementById(`${kind}-pane`);
    const enabled = getEnabledPanes();
    if (indicatorCharts[kind]) {
      indicatorCharts[kind].resizeObserver.disconnect();
      indicatorCharts[kind].chart.remove();
      delete indicatorCharts[kind];
      paneEl.classList.add("hidden-screen");
      btn.classList.remove("active");
      setEnabledPanes(enabled.filter((k) => k !== kind));
    } else {
      paneEl.classList.remove("hidden-screen");
      btn.classList.add("active");
      createIndicatorPane(kind);
      setEnabledPanes([...enabled, kind]);
      loadIndicatorData();
    }
  }

  ["rsi", "macd", "adx"].forEach((kind) => {
    document.getElementById(`toggle-${kind}`).addEventListener("click", () => toggleIndicatorPane(kind));
  });

  // --- VWAP bands (drawn on the main chart) ---

  const VWAP_KEY = "tohtoe_vwap";
  let vwapEnabled = false;
  let vwapSeries = null;

  function computeVwapSeries(candles) {
    let cumPV = 0, cumV = 0, cumPV2 = 0;
    const mid = [], upper1 = [], lower1 = [];
    candles.forEach((c) => {
      const typical = (c.high + c.low + c.close) / 3;
      const vol = c.volume || 0;
      cumPV += typical * vol;
      cumV += vol;
      cumPV2 += typical * typical * vol;
      if (cumV > 0) {
        const vwap = cumPV / cumV;
        const variance = Math.max(cumPV2 / cumV - vwap * vwap, 0);
        const std = Math.sqrt(variance);
        mid.push({ time: c.time, value: vwap });
        upper1.push({ time: c.time, value: vwap + std });
        lower1.push({ time: c.time, value: vwap - std });
      }
    });
    return { mid, upper1, lower1 };
  }

  function refreshVwap() {
    if (!vwapEnabled) return;
    const intraday = currentPeriod === "LIVE" || currentPeriod === "1D";
    if (!intraday || !lastCandles.length) {
      if (vwapSeries) { vwapSeries.mid.setData([]); vwapSeries.upper1.setData([]); vwapSeries.lower1.setData([]); }
      return;
    }
    if (!vwapSeries) {
      vwapSeries = {
        mid: chart.addLineSeries({ color: "#ffb84d", lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false }),
        upper1: chart.addLineSeries({ color: "rgba(255,184,77,0.4)", lineWidth: 1, priceLineVisible: false, lastValueVisible: false }),
        lower1: chart.addLineSeries({ color: "rgba(255,184,77,0.4)", lineWidth: 1, priceLineVisible: false, lastValueVisible: false }),
      };
    }
    const { mid, upper1, lower1 } = computeVwapSeries(lastCandles);
    vwapSeries.mid.setData(mid);
    vwapSeries.upper1.setData(upper1);
    vwapSeries.lower1.setData(lower1);
  }

  function toggleVwap() {
    vwapEnabled = !vwapEnabled;
    localStorage.setItem(VWAP_KEY, vwapEnabled ? "1" : "0");
    document.getElementById("toggle-vwap").classList.toggle("active", vwapEnabled);
    if (vwapEnabled) {
      refreshVwap();
    } else if (vwapSeries) {
      chart.removeSeries(vwapSeries.mid);
      chart.removeSeries(vwapSeries.upper1);
      chart.removeSeries(vwapSeries.lower1);
      vwapSeries = null;
    }
  }
  document.getElementById("toggle-vwap").addEventListener("click", toggleVwap);

  // --- volume profile (canvas overlay) ---

  const VOLPROFILE_KEY = "tohtoe_volprofile";
  let volProfileEnabled = false;

  function computeVolumeProfile(candles, bins = 24) {
    const prices = candles.flatMap((c) => [c.high, c.low]);
    const min = Math.min(...prices), max = Math.max(...prices);
    const range = max - min || 1;
    const buckets = new Array(bins).fill(0);
    candles.forEach((c) => {
      const mid = (c.high + c.low) / 2;
      let idx = Math.floor(((mid - min) / range) * bins);
      idx = Math.max(0, Math.min(bins - 1, idx));
      buckets[idx] += c.volume || 0;
    });
    return { buckets, min, max };
  }

  function drawVolumeProfile(retriesLeft = 40) {
    const canvas = document.getElementById("volprofile-canvas");
    const ctx = canvas.getContext("2d");
    const wrap = document.getElementById("chart-wrap");
    const w = wrap.clientWidth, h = wrap.clientHeight;
    if (!volProfileEnabled) {
      canvas.width = w;
      canvas.height = h;
      return;
    }
    if ((w === 0 || h === 0) && retriesLeft > 0) {
      // The chart container can still be mid-transition (e.g. the 420ms
      // start-screen -> app-shell fade) when a fetch resolves faster than
      // that -- retry shortly instead of drawing into a zero-size canvas.
      // Bounded so this can't spin forever if the chart is legitimately
      // off-screen (e.g. user backed out to the start screen).
      setTimeout(() => drawVolumeProfile(retriesLeft - 1), 30);
      return;
    }
    canvas.width = w;
    canvas.height = h;
    ctx.clearRect(0, 0, w, h);
    if (!lastCandles.length) return;

    const { buckets, min, max } = computeVolumeProfile(lastCandles);
    const maxBucket = Math.max(...buckets, 1);
    const barMaxWidth = w * 0.18;
    const theme = localStorage.getItem(THEME_KEY) || "dark";
    ctx.fillStyle = theme === "light" ? "rgba(59,111,224,0.25)" : "rgba(91,140,255,0.25)";

    buckets.forEach((v, i) => {
      const priceLo = min + (i / buckets.length) * (max - min);
      const priceHi = min + ((i + 1) / buckets.length) * (max - min);
      const yHi = candleSeries.priceToCoordinate(priceHi);
      const yLo = candleSeries.priceToCoordinate(priceLo);
      if (yHi == null || yLo == null) return;
      const barW = (v / maxBucket) * barMaxWidth;
      ctx.fillRect(w - barW, Math.min(yHi, yLo), barW, Math.max(Math.abs(yLo - yHi), 1));
    });
  }

  function toggleVolProfile() {
    volProfileEnabled = !volProfileEnabled;
    localStorage.setItem(VOLPROFILE_KEY, volProfileEnabled ? "1" : "0");
    document.getElementById("toggle-volprofile").classList.toggle("active", volProfileEnabled);
    document.getElementById("volprofile-canvas").classList.toggle("hidden-screen", !volProfileEnabled);
    drawVolumeProfile();
  }
  document.getElementById("toggle-volprofile").addEventListener("click", toggleVolProfile);

  // --- compare mode ---

  let compareSeries = null;
  let compareSymbol = null;

  async function loadCompareSymbol(symbol) {
    symbol = symbol.trim().toUpperCase();
    if (!symbol) return;
    try {
      const options = INTERVAL_COMPAT[currentPeriod];
      const intervalParam = options ? (currentInterval && options.includes(currentInterval) ? currentInterval : INTERVAL_DEFAULTS[currentPeriod]) : "";
      const url = `/api/history/${encodeURIComponent(symbol)}?period=${currentPeriod}` + (intervalParam ? `&interval=${intervalParam}` : "");
      const resp = await fetch(url);
      const data = await resp.json();
      if (!data.candles || !data.candles.length) return;
      const shifted = data.candles.map(shiftCandle);
      const base = shifted[0].close;
      const pctData = shifted.map((c) => ({ time: c.time, value: ((c.close - base) / base) * 100 }));
      if (!compareSeries) {
        compareSeries = chart.addLineSeries({ color: "#ff9d5c", lineWidth: 2, priceScaleId: "compare", priceLineVisible: false, title: symbol });
        chart.priceScale("compare").applyOptions({ scaleMargins: { top: 0.1, bottom: 0.1 } });
      } else {
        compareSeries.applyOptions({ title: symbol });
      }
      compareSeries.setData(pctData);
      compareSymbol = symbol;
    } catch (e) { /* non-critical */ }
  }

  function clearCompare() {
    if (compareSeries) {
      chart.removeSeries(compareSeries);
      compareSeries = null;
    }
    compareSymbol = null;
    document.getElementById("compare-input").value = "";
  }

  document.getElementById("compare-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") loadCompareSymbol(e.target.value);
  });
  document.getElementById("compare-clear-btn").addEventListener("click", clearCompare);

  // --- drawing tools ---

  const DRAWINGS_KEY = "tohtoe_drawings_v1";
  let activeDrawTool = "none";
  let pendingDrawPoints = [];

  function getAllDrawings() {
    try { return JSON.parse(localStorage.getItem(DRAWINGS_KEY)) || {}; } catch (e) { return {}; }
  }
  function getDrawingsForSymbol(symbol) {
    return getAllDrawings()[symbol] || [];
  }
  function saveDrawingsForSymbol(symbol, list) {
    const all = getAllDrawings();
    all[symbol] = list;
    localStorage.setItem(DRAWINGS_KEY, JSON.stringify(all));
  }

  function setActiveDrawTool(tool) {
    activeDrawTool = tool;
    pendingDrawPoints = [];
    document.querySelectorAll(".draw-tool-btn").forEach((b) => b.classList.toggle("active", b.dataset.draw === tool));
    document.getElementById("drawing-canvas").classList.toggle("drawing-active", tool !== "none");
  }

  function canvasClickToPoint(evt) {
    const canvas = document.getElementById("drawing-canvas");
    const rect = canvas.getBoundingClientRect();
    const x = evt.clientX - rect.left;
    const y = evt.clientY - rect.top;
    const time = chart.timeScale().coordinateToTime(x);
    const price = candleSeries.coordinateToPrice(y);
    if (time == null || price == null) return null;
    return { time, price };
  }

  document.getElementById("drawing-canvas").addEventListener("click", (evt) => {
    if (activeDrawTool === "none") return;
    const point = canvasClickToPoint(evt);
    if (!point) return;

    if (activeDrawTool === "horizontal") {
      const list = getDrawingsForSymbol(currentSymbol);
      list.push({ type: "horizontal", price: point.price });
      saveDrawingsForSymbol(currentSymbol, list);
      drawAllDrawings();
      return;
    }

    pendingDrawPoints.push(point);
    if (pendingDrawPoints.length === 2) {
      const list = getDrawingsForSymbol(currentSymbol);
      list.push({ type: activeDrawTool, points: [...pendingDrawPoints] });
      saveDrawingsForSymbol(currentSymbol, list);
      pendingDrawPoints = [];
      drawAllDrawings();
    }
  });

  function drawAllDrawings(retriesLeft = 40) {
    const canvas = document.getElementById("drawing-canvas");
    const ctx = canvas.getContext("2d");
    const wrap = document.getElementById("chart-wrap");
    const w = wrap.clientWidth, h = wrap.clientHeight;
    if ((w === 0 || h === 0) && retriesLeft > 0) {
      // Same "container mid-transition" race as drawVolumeProfile() -- see
      // its comment.
      setTimeout(() => drawAllDrawings(retriesLeft - 1), 30);
      return;
    }
    canvas.width = w;
    canvas.height = h;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!currentSymbol) return;

    const list = getDrawingsForSymbol(currentSymbol);
    const theme = localStorage.getItem(THEME_KEY) || "dark";
    const lineColor = theme === "light" ? "#3b6fe0" : "#5b8cff";

    list.forEach((d) => {
      if (d.type === "horizontal") {
        const y = candleSeries.priceToCoordinate(d.price);
        if (y == null) return;
        ctx.strokeStyle = lineColor;
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 3]);
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = lineColor;
        ctx.font = "10px sans-serif";
        ctx.fillText(fmt(d.price), 4, y - 3);
      } else if (d.type === "trendline") {
        const [p1, p2] = d.points;
        const x1 = chart.timeScale().timeToCoordinate(p1.time);
        const y1 = candleSeries.priceToCoordinate(p1.price);
        const x2 = chart.timeScale().timeToCoordinate(p2.time);
        const y2 = candleSeries.priceToCoordinate(p2.price);
        if (x1 == null || y1 == null || x2 == null || y2 == null) return;
        ctx.strokeStyle = lineColor;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      } else if (d.type === "fib") {
        const [p1, p2] = d.points;
        const x1 = chart.timeScale().timeToCoordinate(p1.time);
        const x2 = chart.timeScale().timeToCoordinate(p2.time);
        if (x1 == null || x2 == null) return;
        const xLeft = Math.min(x1, x2), xRight = Math.max(x1, x2);
        [0, 0.236, 0.382, 0.5, 0.618, 1].forEach((lvl) => {
          const price = p1.price + (p2.price - p1.price) * lvl;
          const y = candleSeries.priceToCoordinate(price);
          if (y == null) return;
          ctx.strokeStyle = "rgba(255,184,77,0.6)";
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(xLeft, y);
          ctx.lineTo(xRight, y);
          ctx.stroke();
          ctx.fillStyle = "#ffb84d";
          ctx.font = "10px sans-serif";
          ctx.fillText(`${(lvl * 100).toFixed(1)}% ${fmt(price)}`, xRight + 4, y + 3);
        });
      }
    });
  }

  document.getElementById("clear-drawings-btn").addEventListener("click", () => {
    saveDrawingsForSymbol(currentSymbol, []);
    drawAllDrawings();
  });
  document.querySelectorAll(".draw-tool-btn").forEach((btn) => {
    btn.addEventListener("click", () => setActiveDrawTool(btn.dataset.draw));
  });

  chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
    if (!syncingRange && range) {
      syncingRange = true;
      Object.values(indicatorCharts).forEach((ic) => ic.chart.timeScale().setVisibleLogicalRange(range));
      syncingRange = false;
    }
    drawVolumeProfile();
    drawAllDrawings();
  });

  function refreshChartExtras() {
    loadIndicatorData();
    refreshVwap();
    drawVolumeProfile();
    drawAllDrawings();
    if (compareSymbol) loadCompareSymbol(compareSymbol);
    loadEconCalendar(currentSymbol);
  }

  // --- sector heatmap ---

  const sectorsModal = document.getElementById("sectors-modal");

  function sectorTileHtml(s) {
    const pct = s.change_pct;
    const cls = pct == null ? "" : pct >= 0 ? "up" : "down";
    const intensity = pct == null ? 0 : Math.min(Math.abs(pct) / 3, 0.5);
    const bg = pct == null ? "var(--panel)" : pct >= 0 ? `rgba(38,217,154,${intensity})` : `rgba(255,92,122,${intensity})`;
    return `
      <div class="sector-tile" style="background:${bg}" data-etf="${s.etf}">
        <div class="sector-tile-etf">${s.etf}</div>
        <div class="sector-tile-name">${s.name}</div>
        <div class="sector-tile-change ${cls}">${pct == null ? "--" : `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%`}</div>
      </div>`;
  }

  async function loadSectors() {
    const gridEl = document.getElementById("sectors-grid");
    gridEl.innerHTML = '<div class="watchlist-empty">Loading…</div>';
    try {
      const resp = await fetch("/api/sectors");
      const data = await resp.json();
      gridEl.innerHTML = (data.sectors || []).map(sectorTileHtml).join("");
    } catch (e) {
      gridEl.innerHTML = '<div class="watchlist-empty">Couldn\'t load sector data.</div>';
    }
  }

  document.getElementById("sectors-grid").addEventListener("click", (e) => {
    const tile = e.target.closest(".sector-tile");
    if (!tile) return;
    sectorsModal.classList.remove("open");
    enterApp(tile.dataset.etf);
  });
  document.getElementById("sectors-close").addEventListener("click", () => sectorsModal.classList.remove("open"));
  sectorsModal.addEventListener("click", (e) => { if (e.target === sectorsModal) sectorsModal.classList.remove("open"); });
  document.getElementById("menu-sectors").addEventListener("click", () => {
    sectorsModal.classList.add("open");
    loadSectors();
  });

  // --- news tab ---

  const newsModal = document.getElementById("news-modal");
  const newsSymbolLabelEl = document.getElementById("news-symbol-label");
  const newsLoadingEl = document.getElementById("news-loading");
  const newsEmptyEl = document.getElementById("news-empty");
  const newsListEl = document.getElementById("news-list");

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str == null ? "" : String(str);
    return div.innerHTML;
  }

  function newsArticleHtml(a) {
    const dirClass = a.direction === "bullish" ? "up" : a.direction === "bearish" ? "down" : "";
    const dt = a.datetime
      ? new Date(a.datetime * 1000).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
      : "";
    const meta = [dt, a.source].filter(Boolean).map(escapeHtml).join(" · ");
    return `
      <a class="news-item" href="${escapeHtml(a.url) || "#"}" target="_blank" rel="noopener noreferrer">
        <div class="news-item-top">
          <span class="news-category ${dirClass}">${escapeHtml(a.category_label)}</span>
          <span class="news-time">${meta}</span>
        </div>
        <div class="news-headline">${escapeHtml(a.headline)}</div>
        <div class="news-note ${dirClass}">${escapeHtml(a.note)}</div>
      </a>`;
  }

  async function openNews() {
    newsSymbolLabelEl.textContent = `· ${currentSymbol}`;
    newsModal.classList.add("open");
    newsListEl.innerHTML = "";
    newsEmptyEl.classList.add("hidden-screen");
    newsLoadingEl.classList.remove("hidden-screen");
    try {
      const resp = await fetch(`/api/news/${encodeURIComponent(currentSymbol)}`);
      const data = await resp.json();
      newsLoadingEl.classList.add("hidden-screen");
      const articles = data.articles || [];
      if (!articles.length) {
        newsEmptyEl.classList.remove("hidden-screen");
        return;
      }
      newsListEl.innerHTML = articles.map(newsArticleHtml).join("");
    } catch (e) {
      newsLoadingEl.classList.add("hidden-screen");
      newsEmptyEl.textContent = "Couldn't load news right now.";
      newsEmptyEl.classList.remove("hidden-screen");
    }
  }

  document.getElementById("news-close").addEventListener("click", () => newsModal.classList.remove("open"));
  newsModal.addEventListener("click", (e) => { if (e.target === newsModal) newsModal.classList.remove("open"); });
  document.getElementById("news-btn-dash").addEventListener("click", openNews);
  document.getElementById("menu-news").addEventListener("click", () => {
    const recents = getRecents();
    enterApp(recents[0] || "AAPL");
    setTimeout(openNews, 480);
  });

  // --- economic calendar ---

  let lastCalendarEvents = [];
  const CALENDAR_TYPE_LABELS = { fomc: "FOMC", cpi: "CPI", nfp: "Jobs Report", earnings: "Earnings" };
  const CALENDAR_TYPE_COLORS = { fomc: "#9d7bff", cpi: "#ffb84d", nfp: "#5b8cff", earnings: "#26d99a" };

  function computeCalendarChartMarkers() {
    // Calendar events are date-level, not intraday -- only worth plotting
    // once each bar represents at least roughly a day, otherwise the
    // "closest candle" match below would be misleadingly precise.
    if (!lastCandles.length || !lastCalendarEvents.length) return [];
    if (!["1M", "3M", "1Y", "5Y"].includes(currentPeriod)) return [];

    const out = [];
    lastCalendarEvents.forEach((e) => {
      const eventMs = new Date(`${e.date}T00:00:00Z`).getTime();
      let closest = null, closestDiff = Infinity;
      lastCandles.forEach((c) => {
        const diff = Math.abs(c.time * 1000 - eventMs);
        if (diff < closestDiff) { closestDiff = diff; closest = c; }
      });
      if (closest && closestDiff < 3 * 86400 * 1000) {
        out.push({
          time: closest.time, position: "aboveBar",
          color: CALENDAR_TYPE_COLORS[e.type] || "#5b8cff", shape: "circle",
          text: CALENDAR_TYPE_LABELS[e.type] || e.type,
        });
      }
    });
    return out;
  }

  function renderEventList() {
    const el = document.getElementById("event-list");
    if (!lastCalendarEvents.length) {
      el.innerHTML = '<li class="empty">No upcoming events</li>';
      return;
    }
    el.innerHTML = lastCalendarEvents.slice(0, 6).map((e, idx) => `
      <li style="--i:${idx * 35}ms"><span>${e.date} · ${CALENDAR_TYPE_LABELS[e.type] || e.type}</span><strong>${e.label}</strong></li>
    `).join("");
  }

  async function loadEconCalendar(symbol) {
    try {
      const resp = await fetch(`/api/calendar/${encodeURIComponent(symbol)}`);
      const data = await resp.json();
      lastCalendarEvents = data.events || [];
    } catch (e) {
      lastCalendarEvents = [];
    }
    renderEventList();
    renderMarkers();
  }

  // --- options sentiment (rendered inside the advisor modal) ---

  function renderOptionsSentiment(optionsData) {
    const bodyEl = document.getElementById("advisor-options-body");
    if (!optionsData || !optionsData.available) {
      bodyEl.innerHTML = `<div class="advisor-options-row"><span class="advisor-options-label">${(optionsData && optionsData.reason) || "Options data unavailable for this symbol."}</span></div>`;
      return;
    }
    const rows = [];
    if (optionsData.atm_iv != null) rows.push(["ATM implied volatility", `${(optionsData.atm_iv * 100).toFixed(1)}%`]);
    if (optionsData.put_call_volume_ratio != null) rows.push(["Put/call volume ratio", optionsData.put_call_volume_ratio.toFixed(2)]);
    if (optionsData.put_call_oi_ratio != null) rows.push(["Put/call open-interest ratio", optionsData.put_call_oi_ratio.toFixed(2)]);
    if (optionsData.expiration) rows.push(["Nearest expiration", new Date(optionsData.expiration * 1000).toLocaleDateString()]);

    let html = rows.map(([label, val]) => `<div class="advisor-options-row"><span class="advisor-options-label">${label}</span><span>${val}</span></div>`).join("");
    if (optionsData.unusual_activity && optionsData.unusual_activity.length) {
      html += `<div class="advisor-options-unusual"><strong>Unusual activity</strong>` +
        optionsData.unusual_activity.map((u) => `<div class="advisor-options-unusual-item">${u.type.toUpperCase()} ${fmt(u.strike)} — volume ${u.volume} vs. OI ${u.open_interest}</div>`).join("") +
        `</div>`;
    }
    bodyEl.innerHTML = html || `<div class="advisor-options-row"><span class="advisor-options-label">No options data to show.</span></div>`;
  }

  // --- watchlist ---

  const watchlistModal = document.getElementById("watchlist-modal");
  const watchlistStarIcon = document.getElementById("watchlist-star-icon");
  const watchlistStarBtn = document.getElementById("watchlist-star-btn");

  function renderPriceSparkline(points, w, h) {
    if (!points || points.length < 2) return "";
    const min = Math.min(...points), max = Math.max(...points);
    const range = max - min || 1;
    const pad = 2;
    const coords = points.map((p, i) => {
      const x = pad + (i / (points.length - 1)) * (w - pad * 2);
      const y = h - pad - ((p - min) / range) * (h - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
    const color = points[points.length - 1] >= points[0] ? "var(--green)" : "var(--red)";
    return `<svg class="watchlist-item-spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><polyline points="${coords}" fill="none" stroke="${color}" stroke-width="1.5"></polyline></svg>`;
  }

  function watchlistItemHtml(entry, quote) {
    const q = quote || {};
    const changeCls = q.change_pct == null ? "" : (q.change_pct >= 0 ? "up" : "down");
    const changeText = q.change_pct == null ? "--" : `${q.change_pct >= 0 ? "+" : ""}${q.change_pct.toFixed(2)}%`;
    const verdict = q.last_verdict || "";
    const verdictCls = verdict.toLowerCase().replace(/\s+/g, "-");
    return `
      <div class="watchlist-item" data-symbol="${entry.symbol}">
        ${renderPriceSparkline(q.sparkline, 56, 28)}
        <div class="watchlist-item-main">
          <span class="watchlist-item-symbol">${entry.symbol}</span>
          ${verdict ? `<span class="watchlist-item-verdict ${verdictCls}">${verdict}</span>` : ""}
          <div class="watchlist-item-price">${fmt(q.price)} <span class="watchlist-item-change ${changeCls}">${changeText}</span></div>
        </div>
        <div class="watchlist-item-actions">
          <button class="wl-analyze-btn" data-symbol="${entry.symbol}">Analyze</button>
          <button class="wl-remove-btn" data-symbol="${entry.symbol}">Remove</button>
        </div>
      </div>`;
  }

  async function loadWatchlist() {
    const itemsEl = document.getElementById("watchlist-items");
    const emptyEl = document.getElementById("watchlist-empty");
    try {
      const [listResp, quotesResp] = await Promise.all([
        fetch("/api/watchlist"), fetch("/api/watchlist/quotes"),
      ]);
      const listData = await listResp.json();
      const quotesData = await quotesResp.json();
      const entries = listData.watchlist || [];
      const quotesBySymbol = {};
      (quotesData.quotes || []).forEach((q) => { quotesBySymbol[q.symbol] = q; });

      document.getElementById("watchlist-sub").textContent = entries.length
        ? entries.map((e) => e.symbol).slice(0, 3).join(" · ") : "Nothing pinned yet";

      if (!entries.length) {
        emptyEl.classList.remove("hidden-screen");
        itemsEl.innerHTML = "";
      } else {
        emptyEl.classList.add("hidden-screen");
        itemsEl.innerHTML = entries.map((e) => watchlistItemHtml(e, quotesBySymbol[e.symbol])).join("");
      }
      updateWatchlistStar(entries.map((e) => e.symbol));
    } catch (e) {
      itemsEl.innerHTML = "";
      emptyEl.textContent = "Couldn't load the watchlist.";
      emptyEl.classList.remove("hidden-screen");
    }
  }

  function updateWatchlistStar(symbols) {
    const inList = (symbols || []).includes(currentSymbol);
    watchlistStarIcon.setAttribute("fill", inList ? "currentColor" : "none");
    watchlistStarBtn.classList.toggle("watchlist-star-btn-active", inList);
  }

  async function refreshWatchlistStar() {
    try {
      const resp = await fetch("/api/watchlist");
      const data = await resp.json();
      updateWatchlistStar((data.watchlist || []).map((e) => e.symbol));
    } catch (e) { /* non-critical */ }
  }

  async function toggleWatchlistStar() {
    const inList = watchlistStarBtn.classList.contains("watchlist-star-btn-active");
    try {
      if (inList) {
        await fetch(`/api/watchlist/${encodeURIComponent(currentSymbol)}`, { method: "DELETE" });
      } else {
        await fetch(`/api/watchlist/${encodeURIComponent(currentSymbol)}`, { method: "POST" });
      }
      refreshWatchlistStar();
    } catch (e) { /* non-critical */ }
  }

  async function analyzeAllWatchlist() {
    const btn = document.getElementById("watchlist-analyze-all-btn");
    btn.disabled = true;
    btn.textContent = "Analyzing…";
    try {
      const resp = await fetch("/api/watchlist");
      const data = await resp.json();
      for (const entry of data.watchlist || []) {
        try { await fetch(`/api/advisor/${encodeURIComponent(entry.symbol)}?horizon=medium`); } catch (e) { /* skip */ }
        await new Promise((r) => setTimeout(r, 2000));
      }
    } finally {
      btn.disabled = false;
      btn.textContent = "Analyze All";
      loadWatchlist();
    }
  }

  document.getElementById("watchlist-items").addEventListener("click", (e) => {
    const analyzeBtn = e.target.closest(".wl-analyze-btn");
    const removeBtn = e.target.closest(".wl-remove-btn");
    if (analyzeBtn) {
      enterApp(analyzeBtn.dataset.symbol);
      watchlistModal.classList.remove("open");
      setTimeout(openAdvisor, 480);
    } else if (removeBtn) {
      fetch(`/api/watchlist/${encodeURIComponent(removeBtn.dataset.symbol)}`, { method: "DELETE" }).then(loadWatchlist);
    }
  });

  document.getElementById("watchlist-add-btn").addEventListener("click", async () => {
    const input = document.getElementById("watchlist-add-input");
    const sym = input.value.trim().toUpperCase();
    if (!sym) return;
    await fetch(`/api/watchlist/${encodeURIComponent(sym)}`, { method: "POST" });
    input.value = "";
    loadWatchlist();
  });
  document.getElementById("watchlist-analyze-all-btn").addEventListener("click", analyzeAllWatchlist);
  document.getElementById("watchlist-close").addEventListener("click", () => watchlistModal.classList.remove("open"));
  watchlistModal.addEventListener("click", (e) => { if (e.target === watchlistModal) watchlistModal.classList.remove("open"); });
  document.getElementById("menu-watchlist").addEventListener("click", () => {
    watchlistModal.classList.add("open");
    loadWatchlist();
  });
  watchlistStarBtn.addEventListener("click", toggleWatchlistStar);

  // --- alerts ---

  const alertsModal = document.getElementById("alerts-modal");
  const alertKindEl = document.getElementById("alert-kind");
  const alertPriceInputEl = document.getElementById("alert-price");
  const seenToastEventIds = new Set();

  const ALERT_KIND_LABELS = {
    price_above: "Price above", price_below: "Price below", pattern: "New pattern (1D)",
    verdict_change: "Verdict change", earnings_reminder: "Earnings reminder",
  };

  function alertItemHtml(alert) {
    let params = {};
    try { params = JSON.parse(alert.params_json); } catch (e) { /* ignore */ }
    const meta = alert.kind === "price_above" || alert.kind === "price_below" ? ` @ ${params.price}` : "";
    return `
      <div class="alert-item" data-id="${alert.id}">
        <div class="alert-item-main">
          <span class="alert-item-symbol">${alert.symbol}</span>
          <span class="alert-item-meta">${ALERT_KIND_LABELS[alert.kind] || alert.kind}${meta}</span>
        </div>
        <button class="alert-delete-btn" data-id="${alert.id}">Delete</button>
      </div>`;
  }

  async function loadAlerts() {
    const listEl = document.getElementById("alerts-list");
    const emptyEl = document.getElementById("alerts-empty");
    try {
      const resp = await fetch("/api/alerts");
      const data = await resp.json();
      const items = data.alerts || [];
      if (!items.length) {
        emptyEl.classList.remove("hidden-screen");
        listEl.innerHTML = "";
      } else {
        emptyEl.classList.add("hidden-screen");
        listEl.innerHTML = items.map(alertItemHtml).join("");
      }
    } catch (e) {
      listEl.innerHTML = "";
    }
  }

  document.getElementById("alerts-list").addEventListener("click", (e) => {
    const btn = e.target.closest(".alert-delete-btn");
    if (btn) fetch(`/api/alerts/${btn.dataset.id}`, { method: "DELETE" }).then(loadAlerts);
  });

  alertKindEl.addEventListener("change", () => {
    const needsPrice = alertKindEl.value === "price_above" || alertKindEl.value === "price_below";
    alertPriceInputEl.classList.toggle("hidden-screen", !needsPrice);
  });

  document.getElementById("alert-create-btn").addEventListener("click", async () => {
    const sym = document.getElementById("alert-symbol").value.trim().toUpperCase();
    if (!sym) return;
    const kind = alertKindEl.value;
    const params = {};
    if (kind === "price_above" || kind === "price_below") {
      const price = parseFloat(alertPriceInputEl.value);
      if (!price) return;
      params.price = price;
    }
    await fetch("/api/alerts", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol: sym, kind, params }),
    });
    loadAlerts();
  });

  document.getElementById("alerts-close").addEventListener("click", () => alertsModal.classList.remove("open"));
  alertsModal.addEventListener("click", (e) => { if (e.target === alertsModal) alertsModal.classList.remove("open"); });
  document.getElementById("alerts-btn-dash").addEventListener("click", () => {
    document.getElementById("alert-symbol").value = currentSymbol || "";
    alertPriceInputEl.classList.toggle("hidden-screen", !(alertKindEl.value === "price_above" || alertKindEl.value === "price_below"));
    alertsModal.classList.add("open");
    loadAlerts();
  });

  function showToast(message) {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = message;
    toast.addEventListener("click", () => toast.remove());
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 12000);
  }

  async function pollAlerts() {
    try {
      const resp = await fetch("/api/alerts/pending");
      const data = await resp.json();
      const events = (data.events || []).filter((e) => !seenToastEventIds.has(e.id));
      const badge = document.getElementById("alerts-badge");
      if (events.length) {
        events.forEach((e) => { seenToastEventIds.add(e.id); showToast(e.message); });
        badge.textContent = String(events.length);
        badge.classList.remove("hidden-screen");
        await fetch("/api/alerts/seen", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ids: events.map((e) => e.id) }),
        });
        setTimeout(() => badge.classList.add("hidden-screen"), 8000);
      }
    } catch (e) { /* non-critical, try again next interval */ }
  }
  setInterval(pollAlerts, 20000);
  pollAlerts();

  // --- market status badge ---

  const marketStatusBadge = document.getElementById("market-status-badge");
  async function refreshMarketStatus() {
    try {
      const resp = await fetch("/api/market-status");
      const data = await resp.json();
      marketStatusBadge.textContent = data.label;
      marketStatusBadge.className = `market-status-badge status-${data.status}`;
    } catch (e) { /* non-critical, try again next interval */ }
  }
  setInterval(refreshMarketStatus, 60000);
  refreshMarketStatus();

  // --- paper trading portfolio ---

  const portfolioModal = document.getElementById("portfolio-modal");

  function portfolioPositionHtml(pos) {
    const uCls = pos.unrealized_pnl > 0 ? "pos" : (pos.unrealized_pnl < 0 ? "neg" : "");
    const rCls = pos.realized_pnl > 0 ? "pos" : (pos.realized_pnl < 0 ? "neg" : "");
    return `
      <div class="portfolio-position">
        <div class="portfolio-position-head">
          <span class="portfolio-position-symbol">${pos.symbol}</span>
          <span class="portfolio-position-pnl ${uCls}">${pos.qty > 0 ? `${pos.unrealized_pnl >= 0 ? "+" : ""}${fmt(pos.unrealized_pnl)} unrealized` : ""}</span>
        </div>
        <div class="portfolio-position-detail">
          ${pos.qty > 0 ? `${pos.qty} sh @ avg ${fmt(pos.avg_cost)}, now ${fmt(pos.current_price)}` : "Position closed"} ·
          <span class="${rCls}">${pos.realized_pnl >= 0 ? "+" : ""}${fmt(pos.realized_pnl)} realized</span>
        </div>
      </div>`;
  }

  async function loadPortfolio() {
    const posEl = document.getElementById("portfolio-positions");
    const emptyEl = document.getElementById("portfolio-empty");
    const summaryEl = document.getElementById("portfolio-summary");
    try {
      const resp = await fetch("/api/portfolio");
      const data = await resp.json();
      const positions = data.positions || [];
      if (!positions.length) {
        emptyEl.classList.remove("hidden-screen");
        posEl.innerHTML = "";
        summaryEl.innerHTML = "";
        return;
      }
      emptyEl.classList.add("hidden-screen");
      const totalUnrealized = positions.reduce((s, p) => s + (p.unrealized_pnl || 0), 0);
      const uCls = totalUnrealized > 0 ? "pos" : (totalUnrealized < 0 ? "neg" : "");
      const rCls = data.realized_total > 0 ? "pos" : (data.realized_total < 0 ? "neg" : "");
      summaryEl.innerHTML = `Unrealized: <strong class="${uCls}">${totalUnrealized >= 0 ? "+" : ""}${fmt(totalUnrealized)}</strong> ·
        Realized: <strong class="${rCls}">${data.realized_total >= 0 ? "+" : ""}${fmt(data.realized_total)}</strong>`;
      posEl.innerHTML = positions.map(portfolioPositionHtml).join("");
    } catch (e) {
      posEl.innerHTML = "";
    }
  }

  document.getElementById("trade-log-btn").addEventListener("click", async () => {
    const errEl = document.getElementById("portfolio-error");
    errEl.classList.add("hidden-screen");
    const symbol = document.getElementById("trade-symbol").value.trim().toUpperCase();
    const side = document.getElementById("trade-side").value;
    const qty = parseFloat(document.getElementById("trade-qty").value);
    const price = parseFloat(document.getElementById("trade-price").value);
    if (!symbol || !qty || !price) {
      errEl.textContent = "Enter a symbol, quantity, and price.";
      errEl.classList.remove("hidden-screen");
      return;
    }
    const resp = await fetch("/api/portfolio/trades", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol, side, qty, price }),
    });
    const data = await resp.json();
    if (!data.ok) {
      errEl.textContent = data.message || "Couldn't log that trade.";
      errEl.classList.remove("hidden-screen");
      return;
    }
    document.getElementById("trade-qty").value = "";
    document.getElementById("trade-price").value = "";
    loadPortfolio();
  });

  document.getElementById("portfolio-close").addEventListener("click", () => portfolioModal.classList.remove("open"));
  portfolioModal.addEventListener("click", (e) => { if (e.target === portfolioModal) portfolioModal.classList.remove("open"); });
  document.getElementById("menu-portfolio").addEventListener("click", () => {
    document.getElementById("trade-symbol").value = currentSymbol || "";
    portfolioModal.classList.add("open");
    loadPortfolio();
  });

  advisorHorizonEl.querySelectorAll(".period-btn").forEach((btn) => {
    btn.addEventListener("click", () => selectAdvisorHorizon(btn.dataset.horizon));
  });
  advisorAnalyzeBtn.addEventListener("click", runAdvisorAnalysis);
  advisorShowChartCheckbox.addEventListener("change", () => applyAdvisorChartLines(lastAdvisorResult));

  document.getElementById("menu-advisor").addEventListener("click", () => {
    const recents = getRecents();
    enterApp(recents[0] || "AAPL");
    setTimeout(openAdvisor, 480);
  });
  document.getElementById("advisor-btn-dash").addEventListener("click", openAdvisor);
  document.getElementById("advisor-close").addEventListener("click", () => advisorModal.classList.remove("open"));
  advisorModal.addEventListener("click", (e) => { if (e.target === advisorModal) advisorModal.classList.remove("open"); });

  ["sizer-account", "sizer-risk-pct"].forEach((id) => {
    document.getElementById(id).addEventListener("input", () => renderPositionSizer(lastAdvisorResult));
  });

  document.getElementById("theme-btn-dash").addEventListener("click", toggleTheme);
  document.getElementById("theme-btn-start").addEventListener("click", toggleTheme);
  document.getElementById("export-btn-dash").addEventListener("click", exportChartPng);
  setTheme(localStorage.getItem(THEME_KEY) || "dark");

  getEnabledPanes().forEach((kind) => {
    if (document.getElementById(`toggle-${kind}`)) toggleIndicatorPane(kind);
  });
  if (localStorage.getItem(VWAP_KEY) === "1") toggleVwap();
  if (localStorage.getItem(VOLPROFILE_KEY) === "1") toggleVolProfile();

  // --- auto-update check ---
  // Disabled server-side (returns enabled: false) for any edition that
  // doesn't set UPDATE_REPO before importing the backend -- see main.py.
  async function checkForUpdate() {
    try {
      const resp = await fetch("/api/update-check");
      const data = await resp.json();
      if (!data.enabled || !data.update_available) return;
      if (sessionStorage.getItem(`update_dismissed_${data.latest}`)) return;
      const isMac = /Mac/i.test(navigator.userAgent) && !/iPhone|iPad/i.test(navigator.userAgent);
      const url = isMac ? data.download_url.mac : data.download_url.win;
      document.getElementById("update-banner-text").textContent = `A new version (${data.latest}) is available — you're on ${data.current}.`;
      const link = document.getElementById("update-banner-link");
      link.href = url;
      link.dataset.latest = data.latest;
      document.getElementById("update-banner").classList.remove("hidden-screen");
    } catch (e) { /* non-critical */ }
  }
  document.getElementById("update-banner-dismiss").addEventListener("click", () => {
    const latest = document.getElementById("update-banner-link").dataset.latest;
    if (latest) sessionStorage.setItem(`update_dismissed_${latest}`, "1");
    document.getElementById("update-banner").classList.add("hidden-screen");
  });
  checkForUpdate();

  renderRecents();
  renderDigest();
})();
