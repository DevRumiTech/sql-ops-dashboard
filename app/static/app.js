(() => {
  "use strict";

  const endpoints = {
    summary: "/api/summary",
    revenue: "/api/revenue/products",
    categories: "/api/revenue/categories",
    margins: "/api/margins/products",
    rankings: "/api/rankings/products",
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

  const statusRegion = document.querySelector("#dashboard-status");
  const statusText = document.querySelector("#dashboard-status-text");
  const retryButton = document.querySelector("#retry-button");
  const revenueChart = document.querySelector("#product-revenue-chart");
  const categoryList = document.querySelector("#category-revenue-list");
  const marginList = document.querySelector("#margin-list");
  const tableBody = document.querySelector("#product-table-body");
  const resultCount = document.querySelector("#table-result-count");
  const searchInput = document.querySelector("#product-search");
  const categoryFilter = document.querySelector("#category-filter");
  const filterForm = document.querySelector("#product-filters");

  let products = [];

  async function fetchJson(url) {
    const response = await fetch(url, {
      headers: { Accept: "application/json" },
    });

    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    return response.json();
  }

  function formatCurrency(value) {
    return currencyFormatter.format(Number(value) || 0);
  }

  function setStatus(message, state) {
    statusText.textContent = message;
    statusRegion.classList.remove("is-success", "is-error");
    if (state) {
      statusRegion.classList.add(`is-${state}`);
    }
    retryButton.hidden = state !== "error";
  }

  function setLoadingState() {
    setStatus("Loading dashboard data…", "");

    document.querySelectorAll(".summary-card").forEach((card) => {
      card.classList.add("is-loading");
      card.querySelector(".summary-value").textContent = "—";
    });

    setRegionLoading(
      revenueChart,
      "Loading product revenue chart",
      "loading-bars"
    );
    setRegionLoading(
      categoryList,
      "Loading category revenue",
      "loading-stack"
    );
    setRegionLoading(marginList, "Loading product margins", "loading-stack");

    tableBody.replaceChildren(
      createTableState("Loading product ranking…")
    );
    resultCount.textContent = "";
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

  function renderSummary(summary) {
    const moneyKeys = new Set(["total_revenue", "total_gross_margin"]);

    document.querySelectorAll("[data-summary-key]").forEach((element) => {
      const key = element.dataset.summaryKey;
      const value = summary[key];
      element.textContent = moneyKeys.has(key)
        ? formatCurrency(value)
        : integerFormatter.format(Number(value) || 0);
      element.closest(".summary-card").classList.remove("is-loading");
    });
  }

  function renderSummaryError() {
    document.querySelectorAll(".summary-card").forEach((card) => {
      card.classList.remove("is-loading");
      card.querySelector(".summary-value").textContent = "Unavailable";
    });
  }

  function renderRevenueChart(rows) {
    prepareRegion(revenueChart);
    if (!rows.length) {
      renderEmptyState(revenueChart, "No product revenue", "No valid sales are available.");
      return;
    }

    const maximum = Math.max(...rows.map((row) => Number(row.revenue)));
    const list = document.createElement("ol");
    list.className = "chart-list";

    rows.forEach((row) => {
      const item = document.createElement("li");
      item.className = "chart-row";

      const label = document.createElement("span");
      label.className = "chart-label";
      label.textContent = row.product_name;

      const track = document.createElement("span");
      track.className = "chart-track";
      track.setAttribute("aria-hidden", "true");

      const bar = document.createElement("span");
      bar.className = "chart-bar";
      bar.style.setProperty(
        "--bar-value",
        `${maximum ? (Number(row.revenue) / maximum) * 100 : 0}%`
      );
      track.append(bar);

      const value = document.createElement("span");
      value.className = "chart-value";
      value.textContent = formatCurrency(row.revenue);

      item.setAttribute(
        "aria-label",
        `${row.product_name}: ${formatCurrency(row.revenue)} revenue`
      );
      item.append(label, track, value);
      list.append(item);
    });

    revenueChart.setAttribute(
      "aria-label",
      "Horizontal bar chart of revenue by product"
    );
    revenueChart.replaceChildren(list);
  }

  function renderCategories(rows) {
    prepareRegion(categoryList);
    if (!rows.length) {
      renderEmptyState(
        categoryList,
        "No category revenue",
        "No category sales are available."
      );
      return;
    }

    const maximum = Math.max(...rows.map((row) => Number(row.revenue)));
    const list = document.createElement("ul");
    list.className = "category-list";

    rows.forEach((row) => {
      const item = document.createElement("li");
      item.className = "category-item";

      const heading = document.createElement("div");
      heading.className = "category-heading";

      const name = document.createElement("span");
      name.className = "category-name";
      name.textContent = row.category_name;

      const value = document.createElement("span");
      value.className = "category-value";
      value.textContent = formatCurrency(row.revenue);
      heading.append(name, value);

      const track = document.createElement("div");
      track.className = "category-track";
      track.setAttribute("aria-hidden", "true");

      const bar = document.createElement("div");
      bar.className = "category-bar";
      bar.style.setProperty(
        "--bar-value",
        `${maximum ? (Number(row.revenue) / maximum) * 100 : 0}%`
      );
      track.append(bar);

      item.append(heading, track);
      list.append(item);
    });

    categoryList.replaceChildren(list);
  }

  function renderMargins(rows) {
    prepareRegion(marginList);
    if (!rows.length) {
      renderEmptyState(
        marginList,
        "No margin data",
        "No product margin results are available."
      );
      return;
    }

    const maximum = Math.max(...rows.map((row) => Number(row.gross_margin)));
    const list = document.createElement("ul");
    list.className = "margin-list";

    rows.forEach((row) => {
      const item = document.createElement("li");
      item.className = "margin-item";

      const name = document.createElement("p");
      name.className = "margin-name";
      name.textContent = row.product_name;

      const value = document.createElement("p");
      value.className = "margin-value";
      value.textContent = formatCurrency(row.gross_margin);

      const track = document.createElement("div");
      track.className = "margin-track";
      track.setAttribute("aria-hidden", "true");

      const bar = document.createElement("div");
      bar.className = "margin-bar";
      bar.style.setProperty(
        "--bar-value",
        `${maximum ? (Number(row.gross_margin) / maximum) * 100 : 0}%`
      );
      track.append(bar);

      const rate = document.createElement("span");
      rate.className = "margin-rate";
      rate.textContent = `${percentFormatter.format(
        Number(row.gross_margin_rate)
      )}% of revenue`;

      item.append(name, value, track, rate);
      list.append(item);
    });

    marginList.replaceChildren(list);
  }

  function mergeProductData(revenueRows, marginRows, rankingRows) {
    const marginsById = new Map(
      marginRows.map((row) => [Number(row.product_id), row])
    );
    const rankingsById = new Map(
      rankingRows.map((row) => [Number(row.product_id), row])
    );

    return revenueRows.map((revenue) => {
      const productId = Number(revenue.product_id);
      const margin = marginsById.get(productId) || {};
      const ranking = rankingsById.get(productId) || {};

      return {
        productId,
        name: revenue.product_name,
        category: revenue.category_name,
        revenue: Number(revenue.revenue),
        grossMargin: Number(margin.gross_margin) || 0,
        marginRate: Number(margin.gross_margin_rate) || 0,
        rank: Number(ranking.revenue_rank) || 0,
      };
    });
  }

  function populateCategoryFilter() {
    const currentValue = categoryFilter.value;
    const defaultOption = document.createElement("option");
    defaultOption.value = "";
    defaultOption.textContent = "All categories";
    categoryFilter.replaceChildren(defaultOption);

    [...new Set(products.map((product) => product.category))]
      .sort((left, right) => left.localeCompare(right))
      .forEach((category) => {
        const option = document.createElement("option");
        option.value = category;
        option.textContent = category;
        categoryFilter.append(option);
      });

    if ([...categoryFilter.options].some((option) => option.value === currentValue)) {
      categoryFilter.value = currentValue;
    }
  }

  function renderProductTable() {
    const searchTerm = searchInput.value.trim().toLocaleLowerCase();
    const selectedCategory = categoryFilter.value;
    const filteredProducts = products.filter((product) => {
      const matchesSearch = product.name
        .toLocaleLowerCase()
        .includes(searchTerm);
      const matchesCategory =
        !selectedCategory || product.category === selectedCategory;
      return matchesSearch && matchesCategory;
    });

    if (!filteredProducts.length) {
      tableBody.replaceChildren(
        createTableState(
          products.length
            ? "No products match the current filters."
            : "No product ranking data is available."
        )
      );
      resultCount.textContent = "Showing 0 products";
      return;
    }

    const fragment = document.createDocumentFragment();
    filteredProducts.forEach((product) => {
      const row = document.createElement("tr");
      row.append(
        createRankCell(product.rank),
        createCell(product.name, "product-cell"),
        createCategoryCell(product.category),
        createCell(formatCurrency(product.revenue), "numeric"),
        createCell(formatCurrency(product.grossMargin), "numeric margin-positive"),
        createCell(
          `${percentFormatter.format(product.marginRate)}%`,
          "numeric"
        )
      );
      fragment.append(row);
    });

    tableBody.replaceChildren(fragment);
    const suffix = filteredProducts.length === 1 ? "product" : "products";
    resultCount.textContent = `Showing ${filteredProducts.length} ${suffix}`;
  }

  function createCell(text, className = "") {
    const cell = document.createElement("td");
    cell.className = className;
    cell.textContent = text;
    return cell;
  }

  function createRankCell(rank) {
    const cell = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = "rank-badge";
    badge.textContent = rank;
    badge.setAttribute("aria-label", `Rank ${rank}`);
    cell.append(badge);
    return cell;
  }

  function createCategoryCell(category) {
    const cell = document.createElement("td");
    const pill = document.createElement("span");
    pill.className = "category-pill";
    pill.textContent = category;
    cell.append(pill);
    return cell;
  }

  function createTableState(message) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.className = "table-state";
    cell.colSpan = 6;
    cell.textContent = message;
    row.append(cell);
    return row;
  }

  function prepareRegion(region) {
    region.classList.remove("loading-region");
    region.setAttribute("aria-busy", "false");
  }

  function renderEmptyState(region, title, message) {
    prepareRegion(region);
    const state = document.createElement("div");
    state.className = "empty-state";
    const heading = document.createElement("strong");
    heading.textContent = title;
    const detail = document.createElement("span");
    detail.textContent = message;
    state.append(heading, detail);
    region.replaceChildren(state);
  }

  function renderErrorState(region, title) {
    prepareRegion(region);
    const state = document.createElement("div");
    state.className = "error-state";
    const heading = document.createElement("strong");
    heading.textContent = `${title} unavailable`;
    const detail = document.createElement("span");
    detail.textContent = "The API request could not be completed.";
    state.append(heading, detail);
    region.replaceChildren(state);
  }

  async function loadDashboard() {
    setLoadingState();

    const [summaryResult, revenueResult, categoryResult, marginResult, rankingResult] =
      await Promise.allSettled([
        fetchJson(endpoints.summary),
        fetchJson(endpoints.revenue),
        fetchJson(endpoints.categories),
        fetchJson(endpoints.margins),
        fetchJson(endpoints.rankings),
      ]);

    let failures = 0;

    if (summaryResult.status === "fulfilled") {
      renderSummary(summaryResult.value.summary);
    } else {
      failures += 1;
      renderSummaryError();
    }

    if (revenueResult.status === "fulfilled") {
      renderRevenueChart(revenueResult.value.data);
    } else {
      failures += 1;
      renderErrorState(revenueChart, "Product revenue");
    }

    if (categoryResult.status === "fulfilled") {
      renderCategories(categoryResult.value.data);
    } else {
      failures += 1;
      renderErrorState(categoryList, "Category revenue");
    }

    if (marginResult.status === "fulfilled") {
      renderMargins(marginResult.value.data);
    } else {
      failures += 1;
      renderErrorState(marginList, "Product margin");
    }

    const tableResults = [revenueResult, marginResult, rankingResult];
    if (tableResults.every((result) => result.status === "fulfilled")) {
      products = mergeProductData(
        revenueResult.value.data,
        marginResult.value.data,
        rankingResult.value.data
      );
      populateCategoryFilter();
      renderProductTable();
    } else {
      if (rankingResult.status === "rejected") {
        failures += 1;
      }
      products = [];
      tableBody.replaceChildren(
        createTableState("Product ranking is temporarily unavailable.")
      );
      resultCount.textContent = "";
    }

    if (failures) {
      const label = failures === 1 ? "section" : "sections";
      setStatus(
        `${failures} dashboard ${label} could not be loaded.`,
        "error"
      );
    } else {
      setStatus(
        "Dashboard loaded · generated demonstration records",
        "success"
      );
    }
  }

  searchInput.addEventListener("input", renderProductTable);
  categoryFilter.addEventListener("change", renderProductTable);
  filterForm.addEventListener("reset", () => {
    window.setTimeout(renderProductTable, 0);
  });
  retryButton.addEventListener("click", loadDashboard);

  loadDashboard();
})();
