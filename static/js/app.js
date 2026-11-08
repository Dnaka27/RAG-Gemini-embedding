(function () {
  "use strict";

  var HISTORY_KEY = "rag-history";
  var HISTORY_MAX = 20;
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  var app = document.getElementById("app");
  var emptyAsk = null;
  var stageTimer = null;

  function $(selector, root) { return (root || document).querySelector(selector); }
  function $$(selector, root) { return Array.prototype.slice.call((root || document).querySelectorAll(selector)); }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function store(storage, key, value) {
    try {
      if (value === undefined) return storage.getItem(key);
      storage.setItem(key, value);
    } catch (e) {}
    return null;
  }

  function formatMs(ms) {
    ms = Number(ms);
    if (isNaN(ms)) return "--";
    return ms >= 1000 ? (ms / 1000).toFixed(1) + " s" : ms + " ms";
  }

  /* ---------- htmx: swap the HTML error partials ---------- */

  document.addEventListener("htmx:beforeSwap", function (event) {
    if ([400, 409, 429, 502].indexOf(event.detail.xhr.status) !== -1) {
      event.detail.shouldSwap = true;
      event.detail.isError = false;
    }
  });

  /* ---------- Tabs: Sources / All passages ---------- */

  var tabs = $$(".tab");

  function selectTab(id, focus) {
    tabs.forEach(function (tab) {
      var on = tab.id === id;
      tab.setAttribute("aria-selected", String(on));
      tab.tabIndex = on ? 0 : -1;
      $("#" + tab.getAttribute("aria-controls")).hidden = !on;
      if (on && focus) tab.focus();
    });
    if (id === "tab-passages") loadChunks();
  }

  tabs.forEach(function (tab, index) {
    tab.addEventListener("click", function () { selectTab(tab.id); });
    tab.addEventListener("keydown", function (event) {
      if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
      var next = tabs[(index + (event.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
      selectTab(next.id, true);
    });
  });

  function openPassage(number) {
    selectTab("tab-passages");
    focusChunk(String(number));
  }

  document.addEventListener("cloud:open", function (event) { openPassage(event.detail); });

  /* ---------- Theme, dialog, shortcuts ---------- */

  function toggleTheme() {
    var next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    store(localStorage, "rag-theme", next);
    var meta = $('meta[name="theme-color"]');
    if (meta) meta.content = next === "light" ? "#eef1f3" : "#07080a";
    document.documentElement.dataset.theme = next;
  }

  $("#theme-toggle").addEventListener("click", toggleTheme);

  var dialog = $("#about");
  $("#about-open").addEventListener("click", function () { dialog.showModal(); });
  $("#about-close").addEventListener("click", function () { dialog.close(); });
  dialog.addEventListener("click", function (event) { if (event.target === dialog) dialog.close(); });

  document.addEventListener("keydown", function (event) {
    var field = event.target.closest && event.target.closest("input, textarea");
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && event.target.id === "question") {
      event.preventDefault();
      $("#ask-form").requestSubmit();
      return;
    }
    if (field || event.ctrlKey || event.metaKey || event.altKey || dialog.open) return;
    if (event.key === "/") {
      event.preventDefault();
      $("#question").focus();
    } else if (event.key === "t") toggleTheme();
    else if (event.key === "?") dialog.showModal();
  });

  /* ---------- Toasts ---------- */

  function toast(text, level) {
    var life = 3200;
    var node = el("div", "toast" + (level === "error" ? " is-error" : ""));
    node.style.setProperty("--life", life + "ms");
    node.setAttribute("role", level === "error" ? "alert" : "status");
    var led = el("span", "led");
    led.setAttribute("aria-hidden", "true");
    node.append(led, el("span", "", text));
    $("#toasts").appendChild(node);
    setTimeout(function () {
      node.classList.add("is-leaving");
      setTimeout(function () { node.remove(); }, 260);
    }, life);
  }

  /* ---------- Document: dropzone, sliders, estimate, replace ---------- */

  var fileInput = $("#id_document");
  var dropzone = $("#dropzone");
  var sizeInput = $("#id_max_size");
  var overlapInput = $("#id_overlap");

  function formatBytes(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / 1024 / 1024).toFixed(2) + " MB";
  }

  function updateEstimate() {
    var out = $("#estimate");
    var size = Number(sizeInput.value);
    var overlap = Number(overlapInput.value);
    var file = fileInput.files[0];
    if (!file) {
      out.textContent = "Choose a file to estimate the number of passages.";
      return;
    }
    if (/\.pdf$/i.test(file.name)) {
      out.textContent = "For PDFs, the number of passages is known after processing.";
      return;
    }
    var estimate = Math.max(1, Math.ceil((file.size - overlap) / (size - overlap)));
    out.replaceChildren("About ", el("strong", "", String(estimate)), " passage" + (estimate === 1 ? "" : "s") + " with these settings.");
  }

  function syncSliders() {
    var size = Number(sizeInput.value);
    overlapInput.max = String(Math.min(500, size - 50));
    if (Number(overlapInput.value) > Number(overlapInput.max)) overlapInput.value = overlapInput.max;
    $("#max-size-out").textContent = sizeInput.value;
    $("#overlap-out").textContent = overlapInput.value;
    var isDefault = sizeInput.value === sizeInput.defaultValue && overlapInput.value === overlapInput.defaultValue;
    $("#advanced-meta").textContent = isDefault ? "Recommended" : "Custom: " + sizeInput.value + " / " + overlapInput.value;
    $("#advanced-meta").classList.toggle("is-custom", !isDefault);
    updateEstimate();
  }

  $("#advanced-reset").addEventListener("click", function () {
    sizeInput.value = sizeInput.defaultValue;
    overlapInput.value = overlapInput.defaultValue;
    syncSliders();
  });

  function showFile() {
    var file = fileInput.files[0];
    dropzone.classList.toggle("has-file", Boolean(file));
    $("#process-button").disabled = !file;
    $("#dz-file").hidden = !file;
    if (file) {
      $("#dz-file-name").textContent = file.name;
      $("#dz-file-meta").textContent = formatBytes(file.size);
    }
    updateEstimate();
  }

  function setReplacing(on) {
    app.classList.toggle("is-replacing", on);
    if (on) fileInput.focus();
  }

  sizeInput.addEventListener("input", syncSliders);
  overlapInput.addEventListener("input", syncSliders);
  fileInput.addEventListener("change", showFile);

  function resetUpload() {
    setReplacing(false);
    fileInput.value = "";
    showFile();
  }

  ["dragenter", "dragover"].forEach(function (name) {
    dropzone.addEventListener(name, function (event) {
      event.preventDefault();
      dropzone.classList.add("is-over");
    });
  });
  ["dragleave", "dragend", "drop"].forEach(function (name) {
    dropzone.addEventListener(name, function () { dropzone.classList.remove("is-over"); });
  });
  dropzone.addEventListener("drop", function (event) {
    event.preventDefault();
    if (event.dataTransfer && event.dataTransfer.files.length) {
      fileInput.files = event.dataTransfer.files;
      showFile();
    }
  });

  /* ---------- Document: processing stages ---------- */

  var STAGES = ["extract", "chunk", "embed", "index"];

  function setStages(states) {
    STAGES.forEach(function (name, index) {
      var el = $('.stage[data-stage="' + name + '"]');
      el.classList.remove("is-active", "is-done");
      if (states[index]) el.classList.add(states[index]);
    });
  }

  function runStages() {
    var step = 0;
    clearInterval(stageTimer);
    var tick = function () {
      setStages(STAGES.map(function (_, index) {
        return index < step ? "is-done" : index === step ? "is-active" : "";
      }));
      // Embedding dominates the wait, so the pointer parks on it until the response arrives.
      if (step < 2) step += 1;
    };
    tick();
    stageTimer = setInterval(tick, reduceMotion.matches ? 1200 : 700);
  }

  function stopStages() {
    clearInterval(stageTimer);
    setStages(["", "", "", ""]);
  }

  document.addEventListener("htmx:beforeRequest", function (event) { if (event.detail.elt.id === "upload-form") runStages(); });
  document.addEventListener("htmx:afterRequest", function (event) { if (event.detail.elt.id === "upload-form") stopStages(); });

  /* ---------- Live numbers from the swapped partials ---------- */

  function syncLive() {
    var doc = $("#doc-stats");
    var last = $("#last-timings");
    var has = Boolean(doc && doc.hasAttribute("data-has-doc"));
    var docMs = function (key) { return has ? formatMs(doc.dataset[key]) : "--"; };
    var askMs = function (key) { return last && last.dataset[key] ? formatMs(last.dataset[key]) : "--"; };
    var values = {
      extract_ms: docMs("extractMs"),
      chunk_ms: docMs("chunkMs"),
      embed_ms: docMs("embedMs"),
      chunks: has ? doc.dataset.chunks : "--",
      q_embed_ms: askMs("embedMs"),
      q_retrieve_ms: askMs("retrieveMs"),
      q_generate_ms: askMs("generateMs")
    };
    $$("[data-live]").forEach(function (el) { el.textContent = values[el.dataset.live]; });

    $("#ttl").hidden = !has;
    if (has) startCountdown(Number(doc.dataset.expires));
    else clearInterval(countdownTimer);

    app.classList.toggle("has-doc", has);
    if (!has) app.classList.remove("is-replacing");
    $("#ask-guide").hidden = has;
    $("#ask-button").disabled = !has;
    $("#ask-button").title = has ? "" : "Choose a document first";

    if (window.RagCloud) window.RagCloud.sync();
  }

  var countdownEnd = 0;
  var countdownTimer = null;

  function startCountdown(seconds) {
    countdownEnd = Date.now() + seconds * 1000;
    clearInterval(countdownTimer);
    var render = function () {
      var left = Math.max(0, Math.round((countdownEnd - Date.now()) / 1000));
      var pad = function (n) { return String(n).padStart(2, "0"); };
      $("#ttl-value").textContent = pad(Math.floor(left / 3600)) + ":" + pad(Math.floor(left / 60) % 60) + ":" + pad(left % 60);
      if (!left) clearInterval(countdownTimer);
    };
    render();
    countdownTimer = setInterval(render, 1000);
  }

  /* ---------- Swap handlers ---------- */

  function resetAsk() {
    if (!emptyAsk) return;
    $("#answer-result").innerHTML = emptyAsk.answer;
    $("#retrieval-result").innerHTML = emptyAsk.retrieval;
    var last = $("#last-timings");
    ["embedMs", "retrieveMs", "generateMs"].forEach(function (key) { delete last.dataset[key]; });
    $$(".history-item").forEach(function (item) { item.classList.remove("is-current"); });
    syncChunkMarks();
  }

  document.addEventListener("htmx:afterSwap", function (event) {
    var target = event.detail.target;
    if (target.id === "upload-result") {
      var toasted = $("[data-toast]", target);
      if (toasted) {
        toast(toasted.dataset.toastText, toasted.dataset.toast);
        // htmx fires afterSwap once per OOB element too; show each toast once.
        toasted.removeAttribute("data-toast");
      }
      if ($("[data-upload-ok], [data-upload-cleared]", target)) {
        resetAsk();
        resetUpload();
        selectTab("tab-sources");
      }
      if ($("[data-upload-ok]", target)) $("#question").focus({ preventScroll: true });
    }
    syncLive();
  });

  document.addEventListener("htmx:oobAfterSwap", syncLive);

  document.addEventListener("htmx:afterSettle", function (event) {
    var target = event.detail.target;
    if (target.id === "answer-result") {
      var answer = $(".answer", target);
      if (answer && !answer.dataset.recorded) {
        answer.dataset.recorded = "1";
        recordHistory();
        syncChunkMarks();
      }
      selectTab("tab-sources");
    }
    if (target.id === "chunk-list") {
      applyFilter();
      syncChunkMarks();
      if (pendingChunk) { focusChunk(pendingChunk); pendingChunk = null; }
    }
  });

  document.addEventListener("htmx:sendError", function () { toast("Network error. Try again.", "error"); });

  /* ---------- Ask: chips, counter, copy ---------- */

  var question = $("#question");

  question.addEventListener("input", function () {
    $("#question-count").textContent = question.value.length + " / 2000";
  });

  function setQuestion(text) {
    question.value = text;
    question.dispatchEvent(new Event("input"));
  }

  $$(".chip").forEach(function (chip) {
    chip.addEventListener("click", function () {
      setQuestion(chip.dataset.question);
      question.focus();
      question.classList.remove("flash");
      void question.offsetWidth;
      question.classList.add("flash");
    });
  });

  function copyAnswer(button) {
    var text = $(".answer-text");
    if (!text || !navigator.clipboard) return;
    navigator.clipboard.writeText(text.textContent).then(function () {
      button.textContent = "Copied";
      button.classList.add("is-copied");
      setTimeout(function () { button.textContent = "Copy"; button.classList.remove("is-copied"); }, 1500);
    });
  }

  document.addEventListener("click", function (event) {
    var target = event.target;
    var passage = target.closest("[data-passage]");
    var copy = target.closest(".copy-answer");
    if (passage) openPassage(passage.dataset.passage);
    else if (copy) copyAnswer(copy);
    else if (target.closest("#replace-button")) setReplacing(true);
    else if (target.closest("#replace-cancel")) resetUpload();
  });

  /* ---------- Ask: history ---------- */

  var entries = [];

  function loadHistory() {
    try { entries = JSON.parse(store(sessionStorage, HISTORY_KEY) || "[]"); } catch (e) { entries = []; }
    if (!Array.isArray(entries)) entries = [];
  }

  function saveHistory() { store(sessionStorage, HISTORY_KEY, JSON.stringify(entries)); }

  function renderHistory(currentId) {
    var list = $("#history");
    list.innerHTML = "";
    entries.forEach(function (entry) {
      var button = el("button", "history-item" + (entry.id === currentId ? " is-current" : ""));
      button.type = "button";
      button.dataset.id = entry.id;
      button.append(
        el("span", "history-q", entry.question),
        el("span", "history-time", new Date(entry.id).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }))
      );
      var item = el("li");
      item.appendChild(button);
      list.appendChild(item);
    });
    $("#history-empty").hidden = entries.length > 0;
    $("#history-clear").hidden = entries.length === 0;
    $("#history-count").textContent = String(entries.length);
  }

  function recordHistory() {
    var entry = {
      id: Date.now(),
      question: question.value.trim(),
      answer: $("#answer-result").innerHTML,
      retrieval: $("#retrieval-result").innerHTML,
      timings: $("#last-timings").outerHTML
    };
    entries.unshift(entry);
    entries = entries.slice(0, HISTORY_MAX);
    saveHistory();
    renderHistory(entry.id);
  }

  $("#history").addEventListener("click", function (event) {
    var button = event.target.closest(".history-item");
    if (!button) return;
    var entry = entries.find(function (item) { return String(item.id) === button.dataset.id; });
    if (!entry) return;
    $("#answer-result").innerHTML = entry.answer;
    $("#retrieval-result").innerHTML = entry.retrieval;
    var holder = document.createElement("div");
    holder.innerHTML = entry.timings;
    $("#last-timings").replaceWith(holder.firstChild);
    setQuestion(entry.question);
    renderHistory(entry.id);
    selectTab("tab-sources");
    syncLive();
    syncChunkMarks();
  });

  $("#history-clear").addEventListener("click", function () {
    entries = [];
    saveHistory();
    renderHistory();
  });

  /* ---------- All passages: lazy load, filter, retrieved marks ---------- */

  var pendingChunk = null;

  function loadChunks() {
    var list = $("#chunk-list");
    if (list.querySelector("[data-stale]")) htmx.trigger(list, "chunks:load");
  }

  function applyFilter() {
    var term = $("#chunk-filter").value.trim().toLowerCase();
    var rows = $$(".chunk-row");
    var shown = 0;
    rows.forEach(function (row) {
      var match = !term || row.textContent.toLowerCase().indexOf(term) !== -1;
      row.hidden = !match;
      if (match) shown += 1;
    });
    $("#chunk-count").textContent = rows.length ? shown + " / " + rows.length : "";
  }

  $("#chunk-filter").addEventListener("input", applyFilter);

  function syncChunkMarks() {
    var answer = $(".answer");
    var numbers = answer && answer.dataset.retrieved ? answer.dataset.retrieved.split(",") : [];
    $$(".chunk-row").forEach(function (row) {
      var rank = numbers.indexOf(row.dataset.number);
      row.classList.toggle("is-retrieved", rank !== -1);
      var badge = $(".chunk-rank", row);
      badge.hidden = rank === -1;
      badge.textContent = rank === -1 ? "" : "used #" + (rank + 1);
    });
    $("#retrieved-hint").textContent = numbers.length
      ? numbers.length + " passages used by the last question are marked"
      : "Passages used by a question are marked here";
  }

  function focusChunk(number) {
    var row = document.getElementById("chunk-" + number);
    if (!row) { pendingChunk = number; return; }
    $("#chunk-filter").value = "";
    applyFilter();
    row.scrollIntoView({ block: "center", behavior: reduceMotion.matches ? "auto" : "smooth" });
    row.classList.remove("is-flash");
    void row.offsetWidth;
    row.classList.add("is-flash");
  }

  /* ---------- Boot ---------- */

  function init() {
    emptyAsk = { answer: $("#answer-result").innerHTML, retrieval: $("#retrieval-result").innerHTML };
    loadHistory();
    renderHistory();
    syncSliders();
    showFile();
    syncLive();
    syncChunkMarks();
    if (document.documentElement.classList.contains("boot")) {
      store(sessionStorage, "rag-booted", "1");
      setTimeout(function () { document.documentElement.classList.remove("boot"); }, 1200);
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
