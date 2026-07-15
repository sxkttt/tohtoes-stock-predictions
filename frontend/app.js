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

  let levelPriceLines = [];
  let ws = null;
  let currentSymbol = symbolInput.value.trim().toUpperCase();
  let currentPeriod = "LIVE";
  let currentInterval = "";

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
    candleSeries.setMarkers(
      markers.map((m) => ({
        time: m.time,
        position: m.direction === "bearish" ? "aboveBar" : "belowBar",
        color: dirColor[m.direction] || "#5b8cff",
        shape: dirShape[m.direction] || "circle",
        text: m.pattern,
      }))
    );
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
      const url = `/api/history/${encodeURIComponent(currentSymbol)}?period=${period}` + (intervalParam ? `&interval=${intervalParam}` : "");
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

  function renderAdvisorResults(data) {
    lastAdvisorResult = data;
    const verdictEl = document.getElementById("advisor-verdict");
    const confidenceEl = document.getElementById("advisor-confidence");
    verdictEl.textContent = data.verdict;
    verdictEl.className = `advisor-verdict ${data.verdict.toLowerCase().replace(/\s+/g, "-")}`;
    const tfLabels = (data.timeframes || []).map((tf) => tf.label).join("+");
    confidenceEl.textContent = `${Math.round(data.confidence * 100)}% confidence · ${tfLabels ? tfLabels + " analyzed · " : ""}${data.horizon_label || data.horizon}`;

    document.getElementById("advisor-tf-chips").innerHTML = renderAdvisorTimeframes(data.timeframes);

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

  renderRecents();
})();
