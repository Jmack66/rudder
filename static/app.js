// API endpoints
const API_BASE_URL = "http://localhost:5000/api";

// DOM Elements
const printsList = document.getElementById("prints-list");
const maintenanceList = document.getElementById("maintenance-list");
const timeline = document.getElementById("timeline");
const addPrintBtn = document.getElementById("add-print-btn");
const addMaintenanceBtn = document.getElementById("add-maintenance-btn");
const printModal = document.getElementById("print-modal");
const maintenanceModal = document.getElementById("maintenance-modal");

// Event Listeners
document.addEventListener("DOMContentLoaded", () => {
  loadPrints();
  loadMaintenance();
  loadTimeline();
  setupEventListeners();
});

function setupEventListeners() {
  addPrintBtn.addEventListener("click", () => openModal("print-modal"));
  addMaintenanceBtn.addEventListener("click", () =>
    openModal("maintenance-modal"),
  );

  document
    .getElementById("print-form")
    .addEventListener("submit", handlePrintSubmit);
  document
    .getElementById("maintenance-form")
    .addEventListener("submit", handleMaintenanceSubmit);
}

// Modal Functions
function openModal(modalId) {
  document.getElementById(modalId).style.display = "block";
}

function closeModal(modalId) {
  document.getElementById(modalId).style.display = "none";
}

// Add a variable to store all events
let allTimelineEvents = [];

let printsCache = [];

// Compare parameters to previous print and return a set of changed keys
function getChangedParams(current, previous) {
  if (!current || !previous) return new Set();
  const changed = new Set();
  for (const key in current) {
    if (current[key] !== previous[key]) {
      changed.add(key);
    }
  }
  return changed;
}

// API Functions
async function loadPrints() {
  try {
    const response = await fetch(`${API_BASE_URL}/prints`);
    const prints = await response.json();
    displayPrints(prints);
    // Update timeline with all events
    await loadTimeline();
  } catch (error) {
    console.error("Error loading prints:", error);
  }
}

async function loadMaintenance() {
  try {
    const response = await fetch(`${API_BASE_URL}/maintenance`);
    const maintenance = await response.json();
    displayMaintenance(maintenance);
    // Update timeline with all events
    await loadTimeline();
  } catch (error) {
    console.error("Error loading maintenance:", error);
  }
}

async function handlePrintSubmit(event) {
  event.preventDefault();
  const formData = new FormData();
  formData.append("filename", document.getElementById("filename").value);
  formData.append("gcode_file", document.getElementById("gcode-file").files[0]);

  try {
    const response = await fetch(`${API_BASE_URL}/prints`, {
      method: "POST",
      body: formData,
    });

    if (response.ok) {
      const data = await response.json();
      await completePrint(data.id);
      // Reload the print list to ensure fresh data
      await loadPrints();
      closeModal("print-modal");
      event.target.reset();
    }
  } catch (error) {
    console.error("Error submitting print:", error);
  }
}

async function completePrint(printId) {
  const tempVal = document.getElementById("ambient-temp").value;
  const humidityVal = document.getElementById("ambient-humidity").value;
  const data = {
    quality_rating: document.getElementById("quality-rating").value,
    functionality_rating: document.getElementById("functionality-rating").value,
    label: document.getElementById("print-label").value,
    ambient_temperature: tempVal === "" ? null : parseFloat(tempVal),
    ambient_humidity: humidityVal === "" ? null : parseFloat(humidityVal),
    notes: document.getElementById("print-notes").value,
    status: "success",
  };

  try {
    const response = await fetch(`${API_BASE_URL}/prints/${printId}/complete`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error("Failed to complete print");
    }
  } catch (error) {
    console.error("Error completing print:", error);
  }
}

async function handleMaintenanceSubmit(event) {
  event.preventDefault();
  const data = {
    description: document.getElementById("description").value,
    todo_tasks: document.getElementById("todo-tasks").value,
  };

  try {
    const response = await fetch(`${API_BASE_URL}/maintenance`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    if (response.ok) {
      closeModal("maintenance-modal");
      // Reload everything
      await Promise.all([loadPrints(), loadMaintenance(), loadTimeline()]);
      event.target.reset();
    }
  } catch (error) {
    console.error("Error submitting maintenance:", error);
  }
}

// Display Functions
function displayPrints(prints) {
  printsCache = prints;
  // Sort prints chronologically
  const sortedPrints = [...prints].sort(
    (a, b) => new Date(b.start_time) - new Date(a.start_time),
  );
  let previousParams = null;

  printsList.innerHTML = sortedPrints
    .map((print, idx) => {
      const allParams = print.all_slicer_params || {};
      const changedKeys = getChangedParams(allParams, previousParams);
      previousParams = allParams;
      const changedKeysArr = Array.from(changedKeys);
      const showDropdown = changedKeysArr.length > 8;
      return `
        <div class="print-item" data-id="${print.id}">
            <h3>${print.filename}</h3>
            <p>Status: ${print.status}</p>
            <p>Started: ${new Date(print.start_time).toLocaleString()}</p>
            ${print.quality_rating ? `<p>Quality Rating: ${print.quality_rating}/10</p>` : ""}
            ${print.functionality_rating ? `<p>Functionality Rating: ${print.functionality_rating}/10</p>` : ""}
            ${print.label ? `<p>Label: ${print.label}</p>` : ""}
            ${
              changedKeys.size > 0
                ? `
                <div class="parameters">
                    <h4>Changed Parameters:</h4>
                    <ul>
                        ${changedKeysArr
                          .slice(0, 8)
                          .map(
                            (key) =>
                              `<li class="changed-param">${key}: ${allParams[key]}</li>`,
                          )
                          .join("")}
                    </ul>
                    ${showDropdown ? `<button class="show-all-params-btn" type="button">Show All (${changedKeysArr.length})</button>` : ""}
                </div>
            `
                : ""
            }
        </div>
        `;
    })
    .join("");

  // Add click handlers for print details modal
  document.querySelectorAll(".print-item").forEach((item) => {
    item.addEventListener("click", function (e) {
      // Prevent click on links/buttons inside
      if (e.target.tagName === "BUTTON" || e.target.tagName === "A") return;
      const id = this.getAttribute("data-id");
      showPrintDetailsModal(id);
    });
  });
  // Add handler for Show All button to open modal
  document.querySelectorAll(".show-all-params-btn").forEach((btn) => {
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      const id = btn.closest(".print-item").getAttribute("data-id");
      showPrintDetailsModal(id);
    });
  });
}

async function showPrintDetailsModal(printId) {
  // Always fetch the latest print data from the backend
  try {
    const response = await fetch(`${API_BASE_URL}/prints`);
    const prints = await response.json();
    const print = prints.find((p) => p.id == printId);
    if (!print) return;

    // Store the print ID for the save function
    document
      .getElementById("print-details-form")
      .setAttribute("data-print-id", printId);

    // Populate the form fields
    document.getElementById("edit-quality-rating").value =
      print.quality_rating || "";
    document.getElementById("edit-functionality-rating").value =
      print.functionality_rating || "";
    document.getElementById("edit-label").value = print.label || "structural";
    document.getElementById("edit-ambient-temp").value =
      print.ambient_temperature || "";
    document.getElementById("edit-ambient-humidity").value =
      print.ambient_humidity || "";
    document.getElementById("edit-notes").value = print.notes || "";

    // Find previous print for changed parameter comparison
    let previousParams = null;
    const sortedPrints = [...prints].sort(
      (a, b) => new Date(a.start_time) - new Date(b.start_time),
    );
    for (let i = 0; i < sortedPrints.length; i++) {
      if (sortedPrints[i].id == print.id && i > 0) {
        previousParams = sortedPrints[i - 1].all_slicer_params || {};
        break;
      }
    }

    // Slicer parameters section
    const allParams = print.all_slicer_params || {};
    const changedKeys = getChangedParams(allParams, previousParams);
    const categories = [
      "filament",
      "support",
      "infill",
      "printer",
      "slicer",
      "extruder",
      "perimeter",
      "layer",
      "speed",
      "temperature",
      "cooling",
      "retraction",
      "skirt",
      "raft",
      "brim",
      "adhesion",
      "travel",
      "wipe",
      "fan",
      "bed",
      "object",
      "top",
      "bottom",
      "shell",
      "material",
      "flow",
      "acceleration",
      "jerk",
      "gcode",
      "machine",
      "tool",
      "wall",
      "seam",
      "iron",
      "bridge",
      "prime",
      "ooze",
      "elephant",
      "z",
      "x",
      "y",
      "general",
    ];
    const groups = {};
    const other = [];
    for (const [key, value] of Object.entries(allParams)) {
      if (!key || value === undefined || value === null) continue;
      let found = false;
      for (const cat of categories) {
        if (key.toLowerCase().startsWith(cat)) {
          if (!groups[cat]) groups[cat] = [];
          groups[cat].push({ key, value });
          found = true;
          break;
        }
      }
      if (!found) {
        other.push({ key, value });
      }
    }
    let paramsHtml = "";
    if (groups["general"]) {
      paramsHtml += `
            <div class="param-group">
                <div class="param-group-title">General</div>
                <ul class="param-list">
                    ${groups["general"].map((p) => `<li class="${changedKeys.has(p.key) ? "changed-param" : ""}"><strong>${p.key}:</strong> ${p.value}</li>`).join("")}
                </ul>
            </div>
            `;
    }
    for (const cat of categories) {
      if (cat === "general") continue;
      if (groups[cat]) {
        paramsHtml += `
                <div class="param-group">
                    <div class="param-group-title">${cat.charAt(0).toUpperCase() + cat.slice(1)}</div>
                    <ul class="param-list">
                        ${groups[cat].map((p) => `<li class="${changedKeys.has(p.key) ? "changed-param" : ""}"><strong>${p.key}:</strong> ${p.value}</li>`).join("")}
                    </ul>
                </div>
                `;
      }
    }
    if (other.length > 0) {
      paramsHtml += `
            <div class="param-group">
                <div class="param-group-title">Other</div>
                <ul class="param-list">
                    ${other.map((p) => `<li class="${changedKeys.has(p.key) ? "changed-param" : ""}"><strong>${p.key}:</strong> ${p.value}</li>`).join("")}
                </ul>
            </div>
            `;
    }
    document.getElementById("print-details-params").innerHTML = paramsHtml;
    openModal("print-details-modal");
  } catch (error) {
    console.error("Error loading print details:", error);
  }
}

// Add event listener for the print details form submission
document
  .getElementById("print-details-form")
  .addEventListener("submit", async function (event) {
    event.preventDefault();
    const printId = this.getAttribute("data-print-id");
    const tempVal = document.getElementById("edit-ambient-temp").value;
    const humidityVal = document.getElementById("edit-ambient-humidity").value;

    const data = {
      quality_rating: document.getElementById("edit-quality-rating").value,
      functionality_rating: document.getElementById("edit-functionality-rating")
        .value,
      label: document.getElementById("edit-label").value,
      ambient_temperature: tempVal === "" ? null : parseFloat(tempVal),
      ambient_humidity: humidityVal === "" ? null : parseFloat(humidityVal),
      notes: document.getElementById("edit-notes").value,
      status: "success",
    };

    try {
      const response = await fetch(
        `${API_BASE_URL}/prints/${printId}/complete`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(data),
        },
      );

      if (response.ok) {
        closeModal("print-details-modal");
        // Reload the print list to show updated data
        await loadPrints();
      } else {
        throw new Error("Failed to update print");
      }
    } catch (error) {
      console.error("Error updating print:", error);
    }
  });

function displayMaintenance(maintenance) {
  maintenanceList.innerHTML = maintenance
    .map(
      (event) => `
        <div class="maintenance-item" data-id="${event.id}">
            <h3>Maintenance Event</h3>
            <p>${event.description}</p>
            <p>Date: ${new Date(event.timestamp).toLocaleString()}</p>
            ${event.todo_tasks ? `<p>Todo: ${event.todo_tasks}</p>` : ""}
        </div>
    `,
    )
    .join("");

  // Add click handlers for maintenance items
  document.querySelectorAll(".maintenance-item").forEach((item) => {
    item.addEventListener("click", function () {
      const id = this.getAttribute("data-id");
      showMaintenanceDetailsModal(id);
    });
  });
}

function updateTimeline(items) {
  if (!items || items.length === 0) {
    timeline.innerHTML =
      '<div class="timeline-empty">No events to display</div>';
    return;
  }

  timeline.innerHTML = items
    .map(
      (item) => `
        <div class="timeline-item ${item.type}">
            <div class="timeline-date">${item.date.toLocaleDateString()}</div>
            <div class="timeline-content">
                <h4>${item.type === "print" ? item.filename || "Print Job" : "Maintenance Event"}</h4>
                <p>${item.type === "print" ? item.status || "Pending" : item.description || "Maintenance Event"}</p>
            </div>
        </div>
    `,
    )
    .join("");
}

// Update the loadTimeline function
async function loadTimeline() {
  try {
    // Fetch both prints and maintenance events
    const [printsResponse, maintenanceResponse] = await Promise.all([
      fetch(`${API_BASE_URL}/prints`),
      fetch(`${API_BASE_URL}/maintenance`),
    ]);

    const prints = await printsResponse.json();
    const maintenance = await maintenanceResponse.json();

    // Create timeline items
    const items = new vis.DataSet([
      // Add print events
      ...prints.map((print) => ({
        id: `print-${print.id}`,
        content: `Print: ${print.filename}`,
        start: new Date(print.start_time),
        type: "box",
        className: "print-event",
        group: "prints",
        title: `Print: ${print.filename}\nStatus: ${print.status}\nQuality: ${print.quality_rating || "N/A"}/10`,
        data: { type: "print", id: print.id },
      })),
      // Add maintenance events
      ...maintenance.map((maint) => ({
        id: `maintenance-${maint.id}`,
        content: `Maintenance: ${maint.description.substring(0, 30)}${maint.description.length > 30 ? "..." : ""}`,
        start: new Date(maint.timestamp),
        type: "box",
        className: "maintenance-event",
        group: "maintenance",
        title: `Maintenance: ${maint.description}`,
        data: { type: "maintenance", id: maint.id },
      })),
    ]);

    // Create timeline groups
    const groups = new vis.DataSet([
      { id: "prints", content: "Prints" },
      { id: "maintenance", content: "Maintenance" },
    ]);

    // Create timeline options
    const options = {
      height: "350px",
      stack: false,
      showMajorLabels: true,
      showCurrentTime: false,
      zoomable: true,
      moveable: true,
      orientation: "top",
      groupHeightMode: "auto",
      clickToUse: true,
    };

    // Create the timeline
    const container = document.getElementById("interactive-timeline");
    const timeline = new vis.Timeline(container, items, groups, options);

    // Add click handler for timeline events
    timeline.on("click", function (properties) {
      if (properties.item) {
        const item = items.get(properties.item);
        if (item.data.type === "print") {
          showPrintDetailsModal(item.data.id);
        } else if (item.data.type === "maintenance") {
          showMaintenanceDetailsModal(item.data.id);
        }
      }
    });
  } catch (error) {
    console.error("Error loading timeline:", error);
  }
}

// Add function to show maintenance details modal
async function showMaintenanceDetailsModal(maintenanceId) {
  try {
    const response = await fetch(`${API_BASE_URL}/maintenance`);
    const maintenance = await response.json();
    const maint = maintenance.find((m) => m.id == maintenanceId);
    if (!maint) return;

    // Store the maintenance ID for the save function
    document
      .getElementById("maintenance-details-form")
      .setAttribute("data-maintenance-id", maintenanceId);

    // Populate the form fields
    document.getElementById("edit-maintenance-description").value =
      maint.description || "";
    document.getElementById("edit-maintenance-todo").value =
      maint.todo_tasks || "";

    openModal("maintenance-details-modal");
  } catch (error) {
    console.error("Error showing maintenance details:", error);
  }
}

// Add event listener for the maintenance details form submission
document
  .getElementById("maintenance-details-form")
  .addEventListener("submit", async function (event) {
    event.preventDefault();
    const maintenanceId = this.getAttribute("data-maintenance-id");

    const data = {
      description: document.getElementById("edit-maintenance-description")
        .value,
      todo_tasks: document.getElementById("edit-maintenance-todo").value,
    };

    try {
      const response = await fetch(
        `${API_BASE_URL}/maintenance/${maintenanceId}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(data),
        },
      );

      if (response.ok) {
        closeModal("maintenance-details-modal");
        // Reload the maintenance list to show updated data
        await loadMaintenance();
      } else {
        throw new Error("Failed to update maintenance event");
      }
    } catch (error) {
      console.error("Error updating maintenance event:", error);
    }
  });

function updatePrinterStatusIndicator(connected) {
  const indicator = document.getElementById("printer-status-indicator");
  if (!indicator) return;
  const dot = indicator.querySelector(".status-dot");
  const text = indicator.querySelector(".status-text");
  if (connected === true) {
    dot.className = "status-dot status-dot-connected";
    text.textContent = "Connected";
  } else if (connected === false) {
    dot.className = "status-dot status-dot-disconnected";
    text.textContent = "Not Connected";
  } else {
    dot.className = "status-dot status-dot-unknown";
    text.textContent = "Checking...";
  }
}

async function pollPrinterStatus() {
  try {
    const resp = await fetch("/api/printer_status");
    const data = await resp.json();
    updatePrinterStatusIndicator(data.connected);
  } catch (e) {
    updatePrinterStatusIndicator(false);
  }
}

// Initial check and poll every 10 seconds
pollPrinterStatus();
setInterval(pollPrinterStatus, 10000);

// Allow modals to be closed by pressing Escape
window.addEventListener("keydown", function (e) {
  if (e.key === "Escape") {
    document.querySelectorAll(".modal").forEach((modal) => {
      if (modal.style.display === "block" || modal.classList.contains("open")) {
        closeModal(modal.id);
      }
    });
  }
});

// Export button handler
const exportBtn = document.getElementById("export-btn");
if (exportBtn) {
  exportBtn.addEventListener("click", () => {
    window.location.href = "/api/export";
  });
}
