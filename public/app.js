(() => {
  "use strict";

  const endpoints = [
    ["summary", "/api/summary"],
    ["revenue", "/api/revenue/products"],
    ["categories", "/api/revenue/categories"],
    ["margins", "/api/margins/products"],
    ["rankings", "/api/rankings/products"],
    ["trends", "/api/trends/monthly"],
  ];
  const PRODUCT_MIX_LIMIT = 10;
  const MARGIN_CARD_LIMIT = 8;
  const BACK_TO_TOP_THRESHOLD = 600;
  const mobileLayout = window.matchMedia("(max-width: 767.98px)");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const sectionHeadingIds = {
    "overview-section": "overview-heading",
    "product-performance-section": "table-title",
    "profitability-section": "margin-title",
    "revenue-section": "product-mix-title",
    "trend-section": "trend-title",
  };
  const currencyFormatter = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  });
  const integerFormatter = new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 0,
  });
  const percentFormatter = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
  const dateFormatter = new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
  const fullDateFormatter = new Intl.DateTimeFormat("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
  const trendPresentations = {
    daily: {
      description: "Recognized revenue and gross margin by calendar day.",
      periodLabel: "Daily",
      title: "Daily Revenue and Gross Margin",
    },
    monthly: {
      description: "Recognized revenue and gross margin by calendar month.",
      periodLabel: "Monthly",
      title: "Monthly Revenue and Gross Margin",
    },
    weekly: {
      description:
        "Recognized revenue and gross margin by selected seven-day period.",
      periodLabel: "Weekly",
      title: "Weekly Revenue and Gross Margin",
    },
  };

  const elements = {
    backToTop: document.querySelector("#back-to-top"),
    categoryFilter: document.querySelector("#category-filter"),
    csvButton: document.querySelector("#download-csv"),
    dateRangeHelper: document.querySelector("#date-range-helper"),
    endDate: document.querySelector("#end-date"),
    filterControls: document.querySelector("#filter-controls"),
    filterForm: document.querySelector("#global-filters"),
    filterMessage: document.querySelector("#filter-message"),
    filterPanel: document.querySelector(".filter-panel"),
    filterSummary: document.querySelector("#filter-summary"),
    filterToggle: document.querySelector("#filter-toggle"),
    latestDataNotice: document.querySelector("#latest-data-notice"),
    marginList: document.querySelector("#margin-list"),
    metadata: document.querySelector("#analysis-metadata"),
    mobileSectionSelect: document.querySelector("#mobile-section-select"),
    pageTitle: document.querySelector("#page-title"),
    periodPreset: document.querySelector("#period-preset"),
    productChart: document.querySelector("#product-revenue-chart"),
    resultCount: document.querySelector("#table-result-count"),
    retryButton: document.querySelector("#retry-button"),
    revenueCategories: document.querySelector("#category-revenue-list"),
    searchInput: document.querySelector("#product-search"),
    startDate: document.querySelector("#start-date"),
    statusRegion: document.querySelector("#dashboard-status"),
    statusText: document.querySelector("#dashboard-status-text"),
    tableBody: document.querySelector("#product-table-body"),
    trend: document.querySelector("#monthly-trend"),
    trendDescription: document.querySelector("#trend-description"),
    trendTitle: document.querySelector("#trend-title"),
  };

  const state = {
    abortController: null,
    currentPeriod: null,
    displayedProducts: [],
    focusHandler: null,
    focusTimer: null,
    meta: null,
    products: [],
    renderedTrendMode: null,
    renderedTrendWidth: 0,
    requestSequence: 0,
    scrollFrame: null,
    searchTimer: null,
    sortDirection: "desc",
    sortKey: "revenue",
    trendPayload: null,
    trendResizeTimer: null,
  };

  async function fetchJson(url, signal) {
    const response = await fetch(url, {
      headers: { Accept: "application/json" },
      signal,
    });
    if (!response.ok) {
      throw new Error("Dashboard request failed");
    }
    return response.json();
  }

  async function initialize() {
    showStatus("Loading dashboard data…");
    elements.filterMessage.textContent = "";
    elements.latestDataNotice.textContent = "Determining latest data date…";
    try {
      const payload = await fetchJson("/api/meta");
      state.meta = payload.meta;
      renderLatestDataNotice(payload.meta.maximum_completed_order_date);
      populateCategories(payload.meta.available_categories);
      applyPreset("12-months");
      updateFilterSummary();
      setFilterExpanded(true);
      await loadDashboard();
    } catch (_error) {
      renderCompleteFailure();
    }
  }

  function populateCategories(categories) {
    const selected = elements.categoryFilter.value;
    const options = [new Option("All categories", "")];
    categories.forEach((category) => {
      options.push(new Option(category, category));
    });
    elements.categoryFilter.replaceChildren(...options);
    elements.categoryFilter.value = categories.includes(selected) ? selected : "";
  }

  function applyPreset(preset) {
    const minimum = parseIsoDate(state.meta.minimum_completed_order_date);
    const maximum = parseIsoDate(state.meta.maximum_completed_order_date);
    let start = minimum;
    let end = maximum;

    if (preset === "30-days") {
      start = shiftUtcDays(maximum, -29);
    } else if (preset === "90-days") {
      start = shiftUtcDays(maximum, -89);
    } else if (preset === "12-months") {
      start = shiftUtcMonths(
        new Date(Date.UTC(maximum.getUTCFullYear(), maximum.getUTCMonth(), 1)),
        -11
      );
    }

    const custom = preset === "custom";
    elements.startDate.readOnly = !custom;
    elements.endDate.readOnly = !custom;
    [elements.startDate, elements.endDate].forEach((input) => {
      input
        .closest(".date-input-shell")
        .classList.toggle("is-readonly", !custom);
    });
    elements.dateRangeHelper.textContent = custom
      ? "Choose a start and end date."
      : "Dates are set automatically by the selected period.";
    if (!custom) {
      elements.startDate.value = formatIsoDate(start);
      elements.endDate.value = formatIsoDate(end);
    }
    state.currentPeriod = {
      end: elements.endDate.value,
      start: elements.startDate.value,
    };
  }

  function selectedQuery() {
    const preset = elements.periodPreset.value;
    const start = elements.startDate.value;
    const end = elements.endDate.value;
    if (!isIsoDate(start) || !isIsoDate(end)) {
      throw new Error("Choose valid start and end dates.");
    }
    if (start > end) {
      throw new Error("Start date must be on or before end date.");
    }
    const parameters = new URLSearchParams();
    if (preset !== "all") {
      parameters.set("start_date", start);
      parameters.set("end_date", end);
    }
    if (elements.categoryFilter.value) {
      parameters.set("category", elements.categoryFilter.value);
    }
    state.currentPeriod = { end, start };
    return parameters.toString();
  }

  function updateFilterSummary() {
    const selectedOption = elements.periodPreset.selectedOptions[0];
    let periodLabel = selectedOption
      ? selectedOption.textContent.trim()
      : "Selected period";
    if (
      elements.periodPreset.value === "custom" &&
      isIsoDate(elements.startDate.value) &&
      isIsoDate(elements.endDate.value)
    ) {
      periodLabel = `${formatDisplayDate(
        elements.startDate.value
      )}–${formatDisplayDate(elements.endDate.value)}`;
    }
    const categoryLabel =
      elements.categoryFilter.value || "All categories";
    elements.filterSummary.textContent = `${periodLabel} · ${categoryLabel}`;
  }

  function setFilterExpanded(expanded) {
    const hasError = elements.filterMessage.textContent.trim() !== "";
    const shouldExpand = !mobileLayout.matches || expanded || hasError;
    elements.filterControls.hidden = !shouldExpand;
    elements.filterSummary.hidden = shouldExpand;
    elements.filterToggle.setAttribute(
      "aria-expanded",
      String(shouldExpand)
    );
    elements.filterToggle.textContent = shouldExpand
      ? "Hide filters"
      : "Edit filters";
    elements.filterPanel.classList.toggle("is-collapsed", !shouldExpand);
  }

  function preferredScrollBehavior() {
    return reducedMotion.matches ? "auto" : "smooth";
  }

  function focusAfterScroll(element, behavior) {
    window.clearTimeout(state.focusTimer);
    if (state.focusHandler) {
      window.removeEventListener("scrollend", state.focusHandler);
    }
    const finishFocus = () => {
      window.clearTimeout(state.focusTimer);
      window.removeEventListener("scrollend", finishFocus);
      if (state.focusHandler === finishFocus) {
        state.focusHandler = null;
        element.focus({ preventScroll: true });
      }
    };
    state.focusHandler = finishFocus;
    if (behavior === "smooth") {
      window.addEventListener("scrollend", finishFocus, { once: true });
    }
    state.focusTimer = window.setTimeout(
      finishFocus,
      behavior === "smooth" ? 700 : 0
    );
  }

  function navigateToSection(sectionId) {
    const section = document.getElementById(sectionId);
    const heading = document.getElementById(sectionHeadingIds[sectionId]);
    if (!section || !heading) {
      return;
    }
    const behavior = preferredScrollBehavior();
    section.scrollIntoView({ behavior, block: "start" });
    focusAfterScroll(heading, behavior);
  }

  function updateBackToTopVisibility() {
    elements.backToTop.hidden =
      !mobileLayout.matches || window.scrollY < BACK_TO_TOP_THRESHOLD;
  }

  function scheduleBackToTopUpdate() {
    if (state.scrollFrame !== null) {
      return;
    }
    state.scrollFrame = window.requestAnimationFrame(() => {
      state.scrollFrame = null;
      updateBackToTopVisibility();
    });
  }

  function handleLayoutChange() {
    setFilterExpanded(true);
    updateBackToTopVisibility();
    scheduleTrendRender();
  }

  async function loadDashboard({ collapseFilters = false } = {}) {
    let query;
    try {
      query = selectedQuery();
      elements.filterMessage.textContent = "";
      updateFilterSummary();
      if (collapseFilters) {
        setFilterExpanded(false);
      }
    } catch (error) {
      elements.filterMessage.textContent = error.message;
      setFilterExpanded(true);
      return;
    }

    if (state.abortController) {
      state.abortController.abort();
    }
    const controller = new AbortController();
    const sequence = state.requestSequence + 1;
    state.abortController = controller;
    state.requestSequence = sequence;
    setLoadingState();

    const suffix = query ? `?${query}` : "";
    const results = await Promise.allSettled(
      endpoints.map(([, path]) => fetchJson(`${path}${suffix}`, controller.signal))
    );
    if (controller.signal.aborted || sequence !== state.requestSequence) {
      return;
    }

    let failures = 0;
    endpoints.forEach(([name], index) => {
      const result = results[index];
      if (result.status === "fulfilled") {
        renderEndpoint(name, result.value);
      } else {
        failures += 1;
        renderEndpointError(name);
      }
    });
    if (failures) {
      setFilterExpanded(true);
      showStatus(
        "Dashboard data could not be loaded. Please try again.",
        "error"
      );
    } else {
      hideStatus();
    }
  }

  function renderEndpoint(name, payload) {
    if (name === "summary") {
      renderSummary(payload);
    } else if (name === "revenue") {
      renderRevenueChart(payload.data);
    } else if (name === "categories") {
      renderCategories(payload.data);
    } else if (name === "margins") {
      renderMargins(payload.data);
    } else if (name === "rankings") {
      state.products = payload.data;
      renderProductTable();
    } else if (name === "trends") {
      renderTrend(payload);
    }
  }

  function renderEndpointError(name) {
    if (name === "summary") {
      renderSummaryError();
    } else if (name === "revenue") {
      renderErrorState(elements.productChart, "Product mix unavailable");
    } else if (name === "categories") {
      renderErrorState(
        elements.revenueCategories,
        "Category revenue unavailable"
      );
    } else if (name === "margins") {
      renderErrorState(elements.marginList, "Product margins unavailable");
    } else if (name === "rankings") {
      state.products = [];
      renderTableState("Product performance is temporarily unavailable.");
    } else if (name === "trends") {
      renderErrorState(elements.trend, "Performance trend unavailable");
    }
  }

  function setLoadingState() {
    showStatus("Loading dashboard data…");
    document.querySelectorAll(".summary-card").forEach((card) => {
      card.classList.add("is-loading");
      card.querySelector(".summary-value").textContent = "—";
    });
    document.querySelectorAll(".summary-comparison").forEach((comparison) => {
      comparison.className = "summary-comparison";
      comparison.textContent = "Comparing periods…";
    });
    elements.metadata.textContent = "Analyzing the selected data period…";
    elements.trendTitle.textContent = "Revenue and Gross Margin Trend";
    elements.trendDescription.textContent =
      "Loading the selected performance period.";
    state.renderedTrendMode = null;
    state.renderedTrendWidth = 0;
    state.trendPayload = null;
    setRegionLoading(elements.trend, "Loading performance trend", "loading-bars");
    setRegionLoading(elements.productChart, "Loading product revenue", "loading-bars");
    setRegionLoading(
      elements.revenueCategories,
      "Loading category revenue",
      "loading-stack"
    );
    setRegionLoading(elements.marginList, "Loading product margins", "loading-stack");
    renderTableState("Loading product performance…");
  }

  function setRegionLoading(region, message, className) {
    const loading = document.createElement("div");
    loading.className = className;
    loading.setAttribute("aria-hidden", "true");
    for (let index = 0; index < 4; index += 1) {
      loading.append(document.createElement("span"));
    }
    const accessibleMessage = document.createElement("span");
    accessibleMessage.className = "visually-hidden";
    accessibleMessage.textContent = message;
    region.classList.add("loading-region");
    region.setAttribute("aria-busy", "true");
    region.replaceChildren(loading, accessibleMessage);
  }

  function renderSummary(payload) {
    const moneyKeys = new Set(["recognized_revenue", "gross_margin"]);
    document.querySelectorAll("[data-summary-key]").forEach((element) => {
      const key = element.dataset.summaryKey;
      const value = payload.summary[key];
      element.textContent = moneyKeys.has(key)
        ? formatCurrency(value)
        : integerFormatter.format(positiveNumber(value));
      element.closest(".summary-card").classList.remove("is-loading");
    });
    document.querySelectorAll("[data-comparison-key]").forEach((element) => {
      renderComparison(element, payload.comparison[element.dataset.comparisonKey]);
    });
    const period = state.currentPeriod;
    elements.metadata.textContent = [
      `${formatDisplayDate(period.start)}–${formatDisplayDate(period.end)}`,
      `${integerFormatter.format(payload.summary.completed_orders)} completed orders analyzed`,
      `${integerFormatter.format(payload.summary.order_lines_analyzed)} order lines analyzed`,
    ].join(" · ");
  }

  function renderComparison(element, value) {
    element.className = "summary-comparison";
    if (value === null || !Number.isFinite(Number(value))) {
      element.textContent = "N/A · no comparable prior period";
      return;
    }
    const numericValue = Number(value);
    if (numericValue > 0) {
      element.classList.add("comparison-positive");
      element.textContent = `↑ ${percentFormatter.format(Math.abs(numericValue))}% increase vs previous period`;
    } else if (numericValue < 0) {
      element.classList.add("comparison-negative");
      element.textContent = `↓ ${percentFormatter.format(Math.abs(numericValue))}% decrease vs previous period`;
    } else {
      element.textContent = "0.0% · unchanged vs previous period";
    }
  }

  function renderSummaryError() {
    document.querySelectorAll(".summary-card").forEach((card) => {
      card.classList.remove("is-loading");
      card.querySelector(".summary-value").textContent = "Unavailable";
    });
    document.querySelectorAll(".summary-comparison").forEach((comparison) => {
      comparison.textContent = "N/A · comparison unavailable";
    });
    elements.metadata.textContent = "Selected period could not be summarized.";
  }

  function renderRevenueChart(rows) {
    prepareRegion(elements.productChart);
    const values = rows.map((row) => positiveNumber(row.revenue));
    const maximum = Math.max(0, ...values);
    if (!rows.length || maximum <= 0) {
      renderNoData(elements.productChart, "No product revenue matches the current filters.");
      return;
    }
    const visibleRows = [...rows]
      .sort(
        (left, right) =>
          positiveNumber(right.revenue) - positiveNumber(left.revenue)
      )
      .slice(0, PRODUCT_MIX_LIMIT);
    const list = document.createElement("ol");
    list.className = "chart-list";
    visibleRows.forEach((row) => {
      const revenue = positiveNumber(row.revenue);
      const item = document.createElement("li");
      item.className = "chart-row";
      item.setAttribute(
        "aria-label",
        `${row.product_name}: ${formatCurrency(revenue)} recognized revenue`
      );
      const label = createElement("span", "chart-label", row.product_name);
      const track = createElement("span", "chart-track");
      track.setAttribute("aria-hidden", "true");
      const bar = createElement("span", "chart-bar");
      bar.style.width = `${(revenue / maximum) * 100}%`;
      track.append(bar);
      const value = createElement("strong", "chart-value", formatCurrency(revenue));
      item.append(label, track, value);
      list.append(item);
    });
    elements.productChart.replaceChildren(list);
  }

  function renderCategories(rows) {
    prepareRegion(elements.revenueCategories);
    const maximum = Math.max(0, ...rows.map((row) => positiveNumber(row.revenue)));
    if (!rows.length || maximum <= 0) {
      renderNoData(
        elements.revenueCategories,
        "No category revenue matches the current filters."
      );
      return;
    }
    const list = document.createElement("ul");
    list.className = "category-list";
    rows.forEach((row) => {
      const revenue = positiveNumber(row.revenue);
      const item = document.createElement("li");
      item.className = "category-item";
      item.setAttribute(
        "aria-label",
        `${row.category_name}: ${formatCurrency(revenue)} recognized revenue`
      );
      const heading = createElement("div", "category-heading");
      heading.append(
        createElement("span", "category-name", row.category_name),
        createElement("strong", "category-value", formatCurrency(revenue))
      );
      const track = createElement("div", "category-track");
      track.setAttribute("aria-hidden", "true");
      const bar = createElement("span", "category-bar");
      bar.style.width = `${(revenue / maximum) * 100}%`;
      track.append(bar);
      item.append(heading, track);
      list.append(item);
    });
    elements.revenueCategories.replaceChildren(list);
  }

  function renderMargins(rows) {
    prepareRegion(elements.marginList);
    const maximum = Math.max(
      0,
      ...rows.map((row) => positiveNumber(row.gross_margin))
    );
    if (!rows.length || maximum <= 0) {
      renderNoData(elements.marginList, "No product margins match the current filters.");
      return;
    }
    const visibleRows = [...rows]
      .sort(
        (left, right) =>
          positiveNumber(right.gross_margin) -
          positiveNumber(left.gross_margin)
      )
      .slice(0, MARGIN_CARD_LIMIT);
    const list = document.createElement("ul");
    list.className = "margin-list";
    visibleRows.forEach((row) => {
      const margin = positiveNumber(row.gross_margin);
      const item = document.createElement("li");
      item.className = "margin-item";
      const name = createElement("p", "margin-name", row.product_name);
      const value = createElement("p", "margin-value", formatCurrency(margin));
      const track = createElement("div", "margin-track");
      track.setAttribute("aria-hidden", "true");
      const bar = createElement("span", "margin-bar");
      bar.style.width = `${(margin / maximum) * 100}%`;
      track.append(bar);
      const rate = createElement(
        "span",
        "margin-rate",
        `${percentFormatter.format(positiveNumber(row.gross_margin_rate))}% margin rate`
      );
      item.append(name, value, track, rate);
      list.append(item);
    });
    elements.marginList.replaceChildren(list);
  }

  function renderTrend(payload) {
    state.trendPayload = payload;
    const rows = Array.isArray(payload.data) ? payload.data : [];
    const presentation =
      trendPresentations[payload.granularity] || trendPresentations.monthly;
    const renderMode = mobileLayout.matches ? "summary" : "chart";
    state.renderedTrendMode = renderMode;
    state.renderedTrendWidth = 0;
    elements.trendTitle.textContent = presentation.title;
    elements.trendDescription.textContent = presentation.description;
    prepareRegion(elements.trend);
    if (
      !rows.length ||
      !rows.some((row) => row.has_completed_orders === true)
    ) {
      renderNoData(
        elements.trend,
        "No completed orders match the selected period."
      );
      return;
    }

    if (renderMode === "summary") {
      renderTrendSummary(rows, presentation);
      return;
    }

    renderCombinedTrendChart(rows, payload.granularity, presentation);
  }

  function renderTrendSummary(rows, presentation) {
    const summary = createElement("div", "trend-mobile-summary");
    summary.setAttribute(
      "aria-label",
      `${presentation.periodLabel} revenue and gross margin summary`
    );
    summary.append(
      createTrendSummaryGroup(
        rows,
        presentation,
        "revenue",
        "revenue",
        "Monthly Revenue"
      ),
      createTrendSummaryGroup(
        rows,
        presentation,
        "gross_margin",
        "margin",
        "Monthly Gross Margin"
      )
    );
    const accessibleSummary = createElement("p", "visually-hidden");
    accessibleSummary.textContent = createTrendScreenReaderSummary(rows);
    elements.trend.replaceChildren(summary, accessibleSummary);
  }

  function createTrendSummaryGroup(
    rows,
    presentation,
    valueKey,
    colorName,
    monthlyHeading
  ) {
    const valueFor = (row) => Number(row[valueKey]) || 0;
    const latest = rows.at(-1);
    const highest = rows.reduce((currentHighest, row) =>
      valueFor(row) >
      valueFor(currentHighest)
        ? row
        : currentHighest
    );
    const average =
      rows.reduce((total, row) => total + valueFor(row), 0) /
      rows.length;
    const isMonthly = presentation.periodLabel === "Monthly";
    const periodNoun = isMonthly ? "month" : "period";
    const headingText = isMonthly
      ? monthlyHeading
      : `${presentation.periodLabel} ${
          valueKey === "revenue" ? "Revenue" : "Gross Margin"
        }`;

    const group = createElement(
      "section",
      `trend-summary-group trend-summary-${colorName}`
    );
    const heading = createElement("h3", "trend-summary-heading", headingText);
    heading.id = `trend-${colorName}-summary-heading`;
    const headingRow = createElement("div", "trend-summary-heading-row");
    const accent = createElement(
      "span",
      `trend-summary-accent trend-summary-accent-${colorName}`
    );
    accent.setAttribute("aria-hidden", "true");
    headingRow.append(accent, heading);
    group.setAttribute("aria-labelledby", heading.id);

    const statistics = document.createElement("dl");
    statistics.className = "trend-summary-stats";
    statistics.append(
      createTrendSummaryStat(
        `Latest ${periodNoun}`,
        latest.label,
        latest[valueKey]
      ),
      createTrendSummaryStat(
        `Highest ${periodNoun}`,
        highest.label,
        highest[valueKey]
      ),
      createTrendSummaryStat(
        isMonthly ? "Average monthly value" : "Average period value",
        "",
        average
      )
    );
    group.append(headingRow, statistics);
    return group;
  }

  function createTrendSummaryStat(label, period, value) {
    const statistic = document.createElement("div");
    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    if (period) {
      detail.append(createElement("span", "trend-summary-period", period));
    }
    detail.append(
      createElement("strong", "trend-summary-value", formatCurrency(value))
    );
    statistic.append(term, detail);
    return statistic;
  }

  function renderCombinedTrendChart(rows, granularity, presentation) {
    const figure = document.createElement("figure");
    figure.className = "trend-figure";
    const legend = createElement("div", "trend-legend");
    legend.append(
      createLegendItem("legend-revenue", "Recognized revenue"),
      createLegendItem("legend-margin", "Gross margin"),
      createLegendItem("legend-missing", "No completed orders")
    );
    const canvas = createElement("div", "trend-chart-canvas");
    figure.append(legend, canvas);
    elements.trend.replaceChildren(figure);

    const svgWidth = Math.max(
      1,
      Math.floor(getTrendChartInnerWidth(canvas))
    );
    state.renderedTrendWidth = svgWidth;
    const compact = svgWidth < 560;
    const height = compact ? 300 : 340;
    const plot = {
      bottom: compact ? 250 : 286,
      left: compact ? 68 : 82,
      right: svgWidth - (compact ? 24 : 30),
      top: 24,
    };
    const edgeInset = compact ? 24 : 32;
    const dataLeft = plot.left + edgeInset;
    const dataRight = plot.right - edgeInset;
    const xStep =
      rows.length > 1 ? (dataRight - dataLeft) / (rows.length - 1) : 0;
    const xPosition = (index) =>
      rows.length > 1 ? dataLeft + index * xStep : (dataLeft + dataRight) / 2;
    const scaleMaximum = Math.max(
      1,
      ...rows.flatMap((row) => [
        positiveNumber(row.revenue),
        positiveNumber(row.gross_margin),
      ])
    );
    const yPosition = (value) =>
      plot.bottom -
      (positiveNumber(value) / scaleMaximum) * (plot.bottom - plot.top);

    const svg = createSvgElement("svg");
    svg.setAttribute("width", "100%");
    svg.setAttribute("viewBox", `0 0 ${svgWidth} ${height}`);
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-labelledby", "trend-svg-title trend-svg-description");
    const title = createSvgElement("title");
    title.id = "trend-svg-title";
    title.textContent = presentation.title;
    const description = createSvgElement("desc");
    description.id = "trend-svg-description";
    description.textContent = `${presentation.description} Periods without completed orders are marked on the time axis.`;
    svg.append(title, description);

    for (let tick = 0; tick <= 4; tick += 1) {
      const value = (scaleMaximum / 4) * tick;
      const y = yPosition(value);
      const gridLine = createSvgElement("line");
      setSvgAttributes(gridLine, {
        class: "trend-grid-line",
        x1: plot.left,
        x2: plot.right,
        y1: y,
        y2: y,
      });
      const label = createSvgElement("text");
      setSvgAttributes(label, {
        class: "trend-axis-label trend-y-label",
        x: plot.left - 12,
        y: y + 4,
      });
      label.textContent = formatCompactCurrency(value);
      svg.append(gridLine, label);
    }

    const visibleLabelIndexes = getTrendLabelIndexes(
      rows.length,
      getTrendLabelTarget(svgWidth, granularity)
    );
    rows.forEach((row, index) => {
      if (visibleLabelIndexes.has(index)) {
        const label = createSvgElement("text");
        const textAnchor =
          index === 0
            ? "start"
            : index === rows.length - 1
              ? "end"
              : "middle";
        setSvgAttributes(label, {
          class: "trend-axis-label trend-x-label",
          "text-anchor": textAnchor,
          x: xPosition(index),
          y: plot.bottom + 26,
        });
        label.textContent = row.label;
        svg.append(label);
      }
      if (!row.has_completed_orders) {
        const missing = createSvgElement("text");
        setSvgAttributes(missing, {
          class: "trend-missing-marker",
          x: xPosition(index),
          y: plot.bottom - 7,
        });
        missing.textContent = "×";
        svg.append(missing);
      }
    });

    appendTrendSeries(
      svg,
      rows,
      "revenue",
      "trend-line-revenue",
      "recognized revenue",
      xPosition,
      yPosition,
      3.5
    );
    appendTrendSeries(
      svg,
      rows,
      "gross_margin",
      "trend-line-margin",
      "gross margin",
      xPosition,
      yPosition,
      3.5
    );
    canvas.append(svg);
    const caption = createElement("figcaption", "visually-hidden");
    caption.textContent = createTrendScreenReaderSummary(rows);
    figure.append(caption);
  }

  function createTrendScreenReaderSummary(rows) {
    return rows
      .map((row) =>
        row.has_completed_orders
          ? `${row.label}: ${formatCurrency(row.revenue)} revenue and ${formatCurrency(row.gross_margin)} gross margin.`
          : `${row.label}: no completed orders.`
      )
      .join(" ");
  }

  function getTrendLabelTarget(svgWidth, granularity) {
    if (granularity === "monthly" && svgWidth >= 560) {
      return 12;
    }
    if (svgWidth < 340) {
      return granularity === "daily" ? 5 : 4;
    }
    if (svgWidth < 480) {
      return granularity === "daily" ? 6 : 5;
    }
    if (svgWidth < 720) {
      return 7;
    }
    return granularity === "monthly" ? 12 : 7;
  }

  function getTrendLabelIndexes(rowCount, targetCount) {
    if (rowCount <= 1) {
      return new Set([0]);
    }
    const labelCount = Math.min(rowCount, Math.max(2, targetCount));
    const indexes = new Set([0, rowCount - 1]);
    for (let position = 1; position < labelCount - 1; position += 1) {
      indexes.add(
        Math.round((position * (rowCount - 1)) / (labelCount - 1))
      );
    }
    return indexes;
  }

  function scheduleTrendRender() {
    window.clearTimeout(state.trendResizeTimer);
    state.trendResizeTimer = window.setTimeout(() => {
      if (!state.trendPayload) {
        return;
      }
      const nextMode = mobileLayout.matches ? "summary" : "chart";
      if (nextMode !== state.renderedTrendMode) {
        renderTrend(state.trendPayload);
        return;
      }
      const canvas = elements.trend.querySelector(".trend-chart-canvas");
      if (!canvas) {
        return;
      }
      const availableWidth = Math.floor(getTrendChartInnerWidth(canvas));
      if (
        availableWidth > 0 &&
        Math.abs(availableWidth - state.renderedTrendWidth) > 1
      ) {
        renderTrend(state.trendPayload);
      }
    }, 150);
  }

  function getTrendChartInnerWidth(canvas) {
    const bounds = canvas.getBoundingClientRect();
    const styles = window.getComputedStyle(canvas);
    const horizontalPadding =
      cssPixelValue(styles.paddingLeft) + cssPixelValue(styles.paddingRight);
    const horizontalBorder =
      cssPixelValue(styles.borderLeftWidth) +
      cssPixelValue(styles.borderRightWidth);
    return Math.max(
      0,
      bounds.width - horizontalPadding - horizontalBorder
    );
  }

  function cssPixelValue(value) {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function appendTrendSeries(
    svg,
    rows,
    valueKey,
    className,
    pointLabel,
    xPosition,
    yPosition,
    markerRadius
  ) {
    const points = rows.map((row, index) => ({
      row,
      x: xPosition(index),
      y: yPosition(row[valueKey]),
    }));
    if (points.length > 1) {
      const line = createSvgElement("polyline");
      setSvgAttributes(line, {
        class: `trend-line ${className}`,
        points: points.map(({ x, y }) => `${x},${y}`).join(" "),
      });
      svg.append(line);
    }
    points.forEach(({ row, x, y }) => {
      const point = createSvgElement("circle");
      setSvgAttributes(point, {
        class: `trend-point ${className}`,
        cx: x,
        cy: y,
        r: markerRadius,
      });
      const pointTitle = createSvgElement("title");
      pointTitle.textContent = `${row.label}: ${formatCurrency(row[valueKey])} ${pointLabel}`;
      point.append(pointTitle);
      svg.append(point);
    });
  }

  function renderProductTable() {
    const search = elements.searchInput.value.trim().toLocaleLowerCase();
    const filtered = state.products.filter((product) =>
      product.product_name.toLocaleLowerCase().includes(search)
    );
    filtered.sort(compareProducts);
    state.displayedProducts = filtered;
    updateSortHeaders();
    elements.csvButton.disabled = filtered.length === 0;

    if (!filtered.length) {
      const message = state.products.length
        ? "No products match the current search."
        : "No product records match the current filters.";
      renderTableState(message);
      elements.resultCount.textContent = "0 products displayed";
      return;
    }

    const fragment = document.createDocumentFragment();
    filtered.forEach((product) => {
      const row = document.createElement("tr");
      row.append(
        createTableCell(product.product_name, "product-cell"),
        createTableCell(product.category_name),
        createTableCell(formatCurrency(product.revenue), "numeric"),
        createTableCell(formatCurrency(product.gross_margin), "numeric margin-positive"),
        createTableCell(
          `${percentFormatter.format(positiveNumber(product.gross_margin_rate))}%`,
          "numeric"
        ),
        createTableCell(String(product.revenue_rank), "numeric")
      );
      fragment.append(row);
    });
    elements.tableBody.replaceChildren(fragment);
    elements.resultCount.textContent = `${integerFormatter.format(filtered.length)} ${
      filtered.length === 1 ? "product" : "products"
    } displayed`;
  }

  function compareProducts(left, right) {
    const key = state.sortKey;
    const direction = state.sortDirection === "asc" ? 1 : -1;
    const leftValue = left[key];
    const rightValue = right[key];
    let result;
    if (typeof leftValue === "string") {
      result = leftValue.localeCompare(String(rightValue), "en-US", {
        sensitivity: "base",
      });
    } else {
      result = positiveNumber(leftValue) - positiveNumber(rightValue);
    }
    if (result === 0) {
      result = left.product_name.localeCompare(right.product_name, "en-US");
    }
    return result * direction;
  }

  function updateSortHeaders() {
    document.querySelectorAll(".sort-button").forEach((button) => {
      const active = button.dataset.sort === state.sortKey;
      const heading = button.closest("th");
      const marker = button.querySelector("span");
      heading.setAttribute(
        "aria-sort",
        active
          ? state.sortDirection === "asc"
            ? "ascending"
            : "descending"
          : "none"
      );
      marker.textContent = active
        ? state.sortDirection === "asc"
          ? "↑"
          : "↓"
        : "";
    });
  }

  function downloadCsv() {
    if (!state.displayedProducts.length) {
      return;
    }
    const headings = [
      "Product",
      "Category",
      "Revenue",
      "Gross Margin",
      "Gross Margin Rate",
      "Rank",
    ];
    const lines = [
      headings,
      ...state.displayedProducts.map((product) => [
        product.product_name,
        product.category_name,
        product.revenue,
        product.gross_margin,
        product.gross_margin_rate,
        product.revenue_rank,
      ]),
    ].map((row) => row.map(escapeCsvValue).join(","));
    const blob = new Blob(["\uFEFF", lines.join("\r\n")], {
      type: "text/csv;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `sql-ops-dashboard-${state.currentPeriod.start}-to-${state.currentPeriod.end}.csv`;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function escapeCsvValue(value) {
    const text = String(value ?? "");
    return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
  }

  function renderCompleteFailure() {
    renderLatestDataNotice(null);
    setFilterExpanded(true);
    showStatus(
      "Dashboard data could not be loaded. Please try again.",
      "error"
    );
    renderSummaryError();
    renderErrorState(elements.trend, "Performance trend unavailable");
    renderErrorState(elements.productChart, "Product mix unavailable");
    renderErrorState(elements.revenueCategories, "Category revenue unavailable");
    renderErrorState(elements.marginList, "Product margins unavailable");
    renderTableState("Product performance is temporarily unavailable.");
  }

  function renderLatestDataNotice(value) {
    if (typeof value !== "string" || !isIsoDate(value)) {
      elements.latestDataNotice.textContent = "Data date unavailable";
      return;
    }
    const formattedDate = fullDateFormatter.format(parseIsoDate(value));
    elements.latestDataNotice.textContent = `Data through ${formattedDate}`;
  }

  function renderNoData(region, message) {
    prepareRegion(region);
    const stateElement = createElement("div", "empty-state");
    stateElement.append(
      createElement("strong", "", "No matching data"),
      createElement("span", "", message)
    );
    region.replaceChildren(stateElement);
  }

  function renderErrorState(region, heading) {
    prepareRegion(region);
    const stateElement = createElement("div", "error-state");
    stateElement.append(
      createElement("strong", "", heading),
      createElement("span", "", "Please try again.")
    );
    region.replaceChildren(stateElement);
  }

  function prepareRegion(region) {
    region.classList.remove("loading-region");
    region.setAttribute("aria-busy", "false");
  }

  function renderTableState(message) {
    const row = document.createElement("tr");
    const cell = createElement("td", "table-state", message);
    cell.colSpan = 6;
    row.append(cell);
    elements.tableBody.replaceChildren(row);
    state.displayedProducts = [];
    elements.csvButton.disabled = true;
    elements.resultCount.textContent = "";
  }

  function showStatus(message, stateName = "") {
    elements.statusRegion.hidden = false;
    elements.statusText.textContent = message;
    elements.statusRegion.classList.toggle("is-error", stateName === "error");
    elements.retryButton.hidden = stateName !== "error";
  }

  function hideStatus() {
    elements.statusRegion.hidden = true;
    elements.statusRegion.classList.remove("is-error");
    elements.statusText.textContent = "";
    elements.retryButton.hidden = true;
  }

  function createElement(tagName, className = "", text = "") {
    const element = document.createElement(tagName);
    if (className) {
      element.className = className;
    }
    if (text !== "") {
      element.textContent = text;
    }
    return element;
  }

  function createTableCell(text, className = "") {
    return createElement("td", className, text);
  }

  function createSvgElement(tagName) {
    return document.createElementNS("http://www.w3.org/2000/svg", tagName);
  }

  function setSvgAttributes(element, attributes) {
    Object.entries(attributes).forEach(([name, value]) => {
      element.setAttribute(name, String(value));
    });
  }

  function createLegendItem(className, label) {
    const item = createElement("span", "legend-item");
    const swatch = createElement("span", `legend-swatch ${className}`);
    swatch.setAttribute("aria-hidden", "true");
    item.append(swatch, label);
    return item;
  }

  function positiveNumber(value) {
    const numericValue = Number(value);
    return Number.isFinite(numericValue) && numericValue > 0 ? numericValue : 0;
  }

  function formatCurrency(value) {
    return currencyFormatter.format(Number(value) || 0);
  }

  function formatCompactCurrency(value) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(Number(value) || 0);
  }

  function parseIsoDate(value) {
    const [year, month, day] = value.split("-").map(Number);
    return new Date(Date.UTC(year, month - 1, day));
  }

  function isIsoDate(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
      return false;
    }
    return formatIsoDate(parseIsoDate(value)) === value;
  }

  function formatIsoDate(value) {
    return value.toISOString().slice(0, 10);
  }

  function shiftUtcDays(value, days) {
    const shifted = new Date(value);
    shifted.setUTCDate(shifted.getUTCDate() + days);
    return shifted;
  }

  function shiftUtcMonths(value, months) {
    return new Date(
      Date.UTC(value.getUTCFullYear(), value.getUTCMonth() + months, 1)
    );
  }

  function formatDisplayDate(value) {
    return dateFormatter.format(parseIsoDate(value));
  }

  elements.periodPreset.addEventListener("change", () => {
    applyPreset(elements.periodPreset.value);
    loadDashboard({
      collapseFilters: elements.periodPreset.value !== "custom",
    });
  });
  [elements.startDate, elements.endDate].forEach((input) => {
    input.addEventListener("change", () => {
      if (elements.periodPreset.value === "custom") {
        loadDashboard();
      }
    });
  });
  elements.categoryFilter.addEventListener("change", () => {
    loadDashboard({ collapseFilters: true });
  });
  elements.filterForm.addEventListener("reset", (event) => {
    event.preventDefault();
    elements.periodPreset.value = "12-months";
    elements.categoryFilter.value = "";
    elements.searchInput.value = "";
    state.sortKey = "revenue";
    state.sortDirection = "desc";
    applyPreset("12-months");
    updateFilterSummary();
    loadDashboard({ collapseFilters: true });
  });
  elements.filterToggle.addEventListener("click", () => {
    const expanded =
      elements.filterToggle.getAttribute("aria-expanded") === "true";
    setFilterExpanded(!expanded);
  });
  elements.mobileSectionSelect.addEventListener("change", () => {
    navigateToSection(elements.mobileSectionSelect.value);
  });
  elements.backToTop.addEventListener("click", () => {
    const behavior = preferredScrollBehavior();
    window.scrollTo({ behavior, top: 0 });
    focusAfterScroll(elements.pageTitle, behavior);
  });
  elements.searchInput.addEventListener("input", () => {
    window.clearTimeout(state.searchTimer);
    state.searchTimer = window.setTimeout(renderProductTable, 180);
  });
  document.querySelectorAll(".sort-button").forEach((button) => {
    button.addEventListener("click", () => {
      const key = button.dataset.sort;
      if (state.sortKey === key) {
        state.sortDirection = state.sortDirection === "asc" ? "desc" : "asc";
      } else {
        state.sortKey = key;
        state.sortDirection =
          ["product_name", "category_name"].includes(key) ? "asc" : "desc";
      }
      renderProductTable();
    });
  });
  elements.csvButton.addEventListener("click", downloadCsv);
  window.addEventListener("scroll", scheduleBackToTopUpdate, {
    passive: true,
  });
  window.addEventListener("resize", scheduleTrendRender, { passive: true });
  mobileLayout.addEventListener("change", handleLayoutChange);
  elements.retryButton.addEventListener("click", () => {
    if (state.meta) {
      loadDashboard();
    } else {
      initialize();
    }
  });

  updateBackToTopVisibility();
  initialize();
})();
