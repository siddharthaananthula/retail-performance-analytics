"use strict";

(() => {
  const exactCurrency = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const integer = new Intl.NumberFormat("en-US");
  const percent = value => `${value.toFixed(2)}%`;

  const chartData = {
    brandSales: {
      label: "Recorded sales by brand",
      modes: {
        sales: { label: "Recorded sales in US dollars", format: value => exactCurrency.format(value), rows: [["National", 5820201.75], ["Private", 2237261.33]] },
        share: { label: "Share of all recorded sales", format: value => percent(value), rows: [["National", 72.23], ["Private", 27.77]] }
      }
    },
    basketMix: {
      label: "Basket mix",
      modes: {
        revenue: { label: "Recorded sales in US dollars", format: value => exactCurrency.format(value), rows: [["Both brands", 6468441], ["National only", 905664.25], ["Private only", 683357.83]] },
        baskets: { label: "Number of baskets", format: value => integer.format(value), rows: [["Both brands", 157546], ["National only", 80763], ["Private only", 38175]] },
        average: { label: "Average basket value in US dollars", format: value => exactCurrency.format(value), rows: [["Both brands", 41.06], ["National only", 11.21], ["Private only", 17.90]] }
      }
    },
    customerReach: {
      label: "Brand reach",
      modes: {
        households: { label: "Purchasing households (overlapping groups)", format: value => integer.format(value), rows: [["National", 2500], ["Private", 2496]] },
        baskets: { label: "Baskets containing each brand (overlapping groups)", format: value => integer.format(value), rows: [["National", 238309], ["Private", 195721]] }
      }
    },
    demographicCoverage: {
      label: "Demographic record coverage",
      modes: {
        default: { label: "Purchasing households", format: value => integer.format(value), rows: [["Known demographics", 801], ["No demographic record", 1699]] }
      }
    },
    promotionCoverage: {
      label: "Promotion record match coverage",
      modes: {
        share: { label: "Share of transaction lines", format: value => `${value.toFixed(1)}%`, rows: [["Matched record", 21.7], ["Unknown status", 78.3]] },
        count: { label: "Transaction lines", format: value => integer.format(value), rows: [["Matched record", 563774], ["Unknown status", 2031958]] }
      }
    },
    groceryBrand: {
      label: "Grocery recorded sales by brand",
      modes: {
        sales: { label: "Recorded sales in US dollars", format: value => exactCurrency.format(value), rows: [["National", 2987981.47], ["Private", 1105832.67]] },
        share: { label: "Share of Grocery sales", format: value => percent(value), rows: [["National", 72.99], ["Private", 27.01]] }
      }
    },
    basketComposition: {
      label: "Basket composition",
      modes: {
        baskets: { label: "Number of baskets", format: value => integer.format(value), rows: [["Both brands", 157546], ["National only", 80763], ["Private only", 38175]] },
        revenue: { label: "Recorded sales in US dollars", format: value => exactCurrency.format(value), rows: [["Both brands", 6468441], ["National only", 905664.25], ["Private only", 683357.83]] },
        average: { label: "Average basket value in US dollars", format: value => exactCurrency.format(value), rows: [["Both brands", 41.06], ["National only", 11.21], ["Private only", 17.90]] }
      }
    }
  };

  function makeSvgElement(name, attributes = {}) {
    const element = document.createElementNS("http://www.w3.org/2000/svg", name);
    for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
    return element;
  }

  function renderChart(host, chartId, mode) {
    const definition = chartData[chartId];
    const config = definition.modes[mode] || definition.modes.default;
    if (!config) return;

    host.replaceChildren();
    const values = config.rows.map(row => row[1]);
    const max = Math.max(...values);
    const left = 150;
    const right = 95;
    const width = 720;
    const rowHeight = 48;
    const top = 14;
    const height = top + rowHeight * config.rows.length + 10;
    const plotWidth = width - left - right;
    const svg = makeSvgElement("svg", {
      viewBox: `0 0 ${width} ${height}`,
      role: "img",
      "aria-label": `${definition.label}: ${config.label}`
    });

    config.rows.forEach(([label, value], index) => {
      const y = top + index * rowHeight;
      const barWidth = Math.max(2, (value / max) * plotWidth);
      const isAccent = label === "Private" || label === "Unknown status" || label === "No demographic record" || label === "Private only";
      const text = makeSvgElement("text", { x: 0, y: y + 20, class: "bar-label" });
      text.textContent = label;
      svg.appendChild(text);

      svg.appendChild(makeSvgElement("line", { x1: left, y1: y + 29, x2: width - right, y2: y + 29, class: "axis-line" }));
      svg.appendChild(makeSvgElement("rect", { x: left, y: y + 3, width: plotWidth, height: 20, rx: 5, class: "bar-track" }));
      const bar = makeSvgElement("rect", {
        x: left,
        y: y + 3,
        width: barWidth,
        height: 20,
        rx: 5,
        class: isAccent ? "bar accent" : "bar",
        tabindex: "0",
        role: "img",
        "aria-label": `${label}: ${config.format(value)}`
      });
      const title = makeSvgElement("title");
      title.textContent = `${label}: ${config.format(value)}`;
      bar.appendChild(title);
      svg.appendChild(bar);

      const valueText = makeSvgElement("text", { x: Math.min(left + barWidth + 8, width - right + 8), y: y + 19, class: "bar-value" });
      valueText.textContent = config.format(value);
      svg.appendChild(valueText);
    });

    host.appendChild(svg);
    const tooltip = document.createElement("div");
    tooltip.className = "chart-tooltip";
    tooltip.setAttribute("role", "tooltip");
    host.appendChild(tooltip);
    const bars = svg.querySelectorAll(".bar");
    bars.forEach((bar, index) => {
      const [label, value] = config.rows[index];
      const show = () => {
        tooltip.textContent = `${label}: ${config.format(value)}`;
        tooltip.classList.add("is-visible");
        const hostBounds = host.getBoundingClientRect();
        const barBounds = bar.getBoundingClientRect();
        const left = barBounds.left - hostBounds.left + barBounds.width / 2 - tooltip.offsetWidth / 2;
        const top = barBounds.top - hostBounds.top - tooltip.offsetHeight - 6;
        tooltip.style.left = `${Math.max(4, Math.min(host.clientWidth - tooltip.offsetWidth - 4, left))}px`;
        tooltip.style.top = `${Math.max(4, top)}px`;
      };
      bar.addEventListener("pointerenter", show);
      bar.addEventListener("pointerleave", () => tooltip.classList.remove("is-visible"));
      bar.addEventListener("focus", show);
      bar.addEventListener("blur", () => tooltip.classList.remove("is-visible"));
    });
    addDataTable(host, config);
  }

  function addDataTable(host, config) {
    const details = document.createElement("details");
    details.className = "chart-data";
    const summary = document.createElement("summary");
    summary.textContent = "View chart data as a table";
    details.appendChild(summary);
    const table = document.createElement("table");
    table.className = "data-table";
    const head = document.createElement("thead");
    const headerRow = document.createElement("tr");
    ["Category", config.label].forEach(label => {
      const cell = document.createElement("th");
      cell.scope = "col";
      cell.textContent = label;
      headerRow.appendChild(cell);
    });
    head.appendChild(headerRow);
    table.appendChild(head);
    const body = document.createElement("tbody");
    config.rows.forEach(([label, value]) => {
      const row = document.createElement("tr");
      const category = document.createElement("th");
      category.scope = "row";
      category.textContent = label;
      const result = document.createElement("td");
      result.textContent = config.format(value);
      row.append(category, result);
      body.appendChild(row);
    });
    table.appendChild(body);
    details.appendChild(table);
    host.appendChild(details);
  }

  document.querySelectorAll("[data-chart-host]").forEach(host => {
    const id = host.dataset.chartHost;
    const initialMode = document.querySelector(`[data-chart="${id}"][aria-pressed="true"]`)?.dataset.mode || "default";
    renderChart(host, id, initialMode);
  });

  document.querySelectorAll("[data-chart][data-mode]").forEach(button => {
    button.addEventListener("click", () => {
      const chartId = button.dataset.chart;
      document.querySelectorAll(`[data-chart="${chartId}"]`).forEach(control => {
        const selected = control === button;
        control.setAttribute("aria-pressed", String(selected));
        control.classList.toggle("is-active", selected);
      });
      const host = document.querySelector(`[data-chart-host="${chartId}"]`);
      if (host) renderChart(host, chartId, button.dataset.mode);
    });
  });

  const tabs = [...document.querySelectorAll('[role="tab"][data-page]')];
  const panels = [...document.querySelectorAll("[data-panel]")];
  const screenshots = [
    ["Overview", "Executive Overview", "assets/screenshots/01-overview.png", "Static screenshot preview of the Executive Overview Power BI report page"],
    ["Customers", "Customer Behaviour", "assets/screenshots/02-customers.png", "Static screenshot preview of the Customer Behaviour Power BI report page"],
    ["Demographics", "Customer Demographics", "assets/screenshots/03-demographics.png", "Static screenshot preview of the Customer Demographics Power BI report page"],
    ["Promotions", "Promotions & Coupons", "assets/screenshots/04-promotions.png", "Static screenshot preview of the Promotions and Coupons Power BI report page"],
    ["Products", "Supplier & Product Performance", "assets/screenshots/05-products.png", "Static screenshot preview of the Supplier and Product Performance Power BI report page"],
    ["Insights", "Business Insights", "assets/screenshots/06-insights.png", "Static screenshot preview of the Business Insights Power BI report page"],
    ["Recommendations", "Business Recommendations", "assets/screenshots/07-recommendations.png", "Static screenshot preview of the Business Recommendations Power BI report page"]
  ];
  const previewImage = document.getElementById("preview-image");
  const previewButton = document.querySelector(".preview-frame");
  const viewerOpenButton = document.querySelector(".viewer-open");
  function showPage(page, updateHash = true) {
    const screenshotIndex = screenshots.findIndex(([id]) => id.toLowerCase() === page);
    if (screenshotIndex < 0) return;
    const [, title, source, alt] = screenshots[screenshotIndex];
    tabs.forEach(tab => {
      const selected = tab.dataset.page === page;
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
    });
    panels.forEach(panel => {
      panel.hidden = panel.dataset.panel !== page;
    });
    if (updateHash && location.hash !== `#${page}`) history.replaceState(null, "", `#${page}`);
    previewImage.src = source;
    previewImage.alt = alt;
    document.getElementById("viewer-title").textContent = title;
    document.getElementById("viewer-count").textContent = `Page ${screenshotIndex + 1} of ${screenshots.length}`;
    previewButton.setAttribute("aria-label", `Open ${title} Power BI screenshot at full size`);
    viewerOpenButton.setAttribute("aria-label", `Enlarge ${title} screenshot`);
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => showPage(tab.dataset.page));
    tab.addEventListener("keydown", event => {
      let nextIndex = index;
      if (event.key === "ArrowRight") nextIndex = (index + 1) % tabs.length;
      else if (event.key === "ArrowLeft") nextIndex = (index - 1 + tabs.length) % tabs.length;
      else if (event.key === "Home") nextIndex = 0;
      else if (event.key === "End") nextIndex = tabs.length - 1;
      else return;
      event.preventDefault();
      tabs[nextIndex].focus();
      showPage(tabs[nextIndex].dataset.page);
    });
  });
  const hashPage = location.hash.slice(1);
  if (tabs.some(tab => tab.dataset.page === hashPage)) showPage(hashPage, false);

  const dialog = document.querySelector(".image-dialog");
  const dialogImage = dialog.querySelector(".dialog-image");
  const dialogCaption = dialog.querySelector(".dialog-caption");
  let screenshotIndex = 0;
  function openScreenshot(index) {
    screenshotIndex = (index + screenshots.length) % screenshots.length;
    const [, title, src, alt] = screenshots[screenshotIndex];
    dialogImage.src = src;
    dialogImage.alt = alt;
    dialogCaption.textContent = `${title} — static Power BI screenshot preview`;
    if (!dialog.open) dialog.showModal();
  }
  document.querySelectorAll("[data-screenshot-open]").forEach(button => {
    button.addEventListener("click", () => openScreenshot(screenshots.findIndex(([id]) => id.toLowerCase() === (tabs.find(tab => tab.getAttribute("aria-selected") === "true")?.dataset.page || "overview"))));
  });
  dialog.querySelector(".dialog-prev").addEventListener("click", () => openScreenshot(screenshotIndex - 1));
  dialog.querySelector(".dialog-next").addEventListener("click", () => openScreenshot(screenshotIndex + 1));
  dialog.querySelector(".dialog-close").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", event => {
    if (event.target === dialog) dialog.close();
  });
})();
