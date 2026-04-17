const $ = (id) => document.getElementById(id);

const els = {
  windowSelect: $("window-select"),
  btnRefresh: $("btn-refresh-windows"),
  btnSelect: $("btn-select-window"),
  preview: $("preview"),
  prompt: $("prompt"),
  btnStart: $("btn-start"),
  btnPause: $("btn-pause"),
  btnResume: $("btn-resume"),
  btnStop: $("btn-stop"),
  statusBadge: $("status-badge"),
  logArea: $("log-area"),
  statUptime: $("stat-uptime"),
  statBattles: $("stat-battles"),
  statErrors: $("stat-errors"),
  footerModel: $("footer-model"),
};

function sceneClass(scene) {
  if (scene === "field") return "log-field";
  if (scene === "battle_command") return "log-battle_command";
  if (scene === "battle_result") return "log-battle_result";
  if (scene === "error") return "log-error";
  return "";
}

function renderLogs(logs) {
  els.logArea.innerHTML = "";
  for (const log of logs) {
    const line = document.createElement("div");
    line.className = `log-line ${sceneClass(log.scene)}`;
    line.textContent = `${log.timestamp} [${log.scene}] ${log.description}`;
    els.logArea.appendChild(line);
  }
  els.logArea.scrollTop = els.logArea.scrollHeight;
}

function setBadge(state) {
  els.statusBadge.textContent = state.toUpperCase();
  els.statusBadge.className = "badge";
  const map = {
    idle: "badge-idle",
    ready: "badge-ready",
    running: "badge-running",
    paused: "badge-paused",
    error: "badge-error",
  };
  els.statusBadge.classList.add(map[state] || "badge-idle");
}

function applyUiState(state) {
  const s = state;
  const windowLocked = s === "running" || s === "paused";

  els.btnStart.disabled = s !== "ready";
  els.btnPause.disabled = s !== "running";
  els.btnResume.disabled = s !== "paused";
  els.btnStop.disabled = s !== "running" && s !== "paused" && s !== "error";

  els.btnRefresh.disabled = windowLocked;
  els.btnSelect.disabled = windowLocked;
  els.windowSelect.disabled = windowLocked;
  els.prompt.disabled = s === "running";

  setBadge(s);
}

async function fetchJson(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    /* ignore */
  }
  if (!res.ok) {
    const detail = data?.detail ?? text ?? res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

async function refreshWindows() {
  const list = await fetchJson("/api/windows");
  els.windowSelect.innerHTML = "";
  for (const w of list) {
    const opt = document.createElement("option");
    opt.value = String(w.hwnd);
    opt.textContent = w.title;
    els.windowSelect.appendChild(opt);
  }
}

async function selectWindow() {
  const hwnd = Number(els.windowSelect.value);
  if (!hwnd) {
    alert("ウィンドウを選択してください");
    return;
  }
  const data = await fetchJson("/api/windows/select", {
    method: "POST",
    body: JSON.stringify({ hwnd }),
  });
  if (data.thumbnail) {
    els.preview.src = data.thumbnail;
    els.preview.classList.add("visible");
  }
}

async function startMonitor() {
  const prompt = els.prompt.value.trim();
  if (!prompt) {
    alert("プロンプトを入力してください");
    return;
  }
  await fetchJson("/api/monitor/start", {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
}

async function pollStatus() {
  try {
    const st = await fetchJson("/api/status");
    applyUiState(st.state);
    renderLogs(st.logs || []);
    const stats = st.stats || {};
    els.statUptime.textContent = stats.uptime || "—";
    els.statBattles.textContent = String(stats.battle_count ?? 0);
    els.statErrors.textContent = String(stats.error_count ?? 0);
  } catch (e) {
    console.error(e);
  }
}

async function pollHealth() {
  try {
    const h = await fetchJson("/api/health");
    els.footerModel.textContent = h.model_loaded
      ? "VLM: ロード済み（Qwen2.5-VL 系 / 設定は config.py）"
      : "VLM: 未ロード（初回はモデル取得に時間がかかります）";
  } catch {
    els.footerModel.textContent = "VLM: 状態取得に失敗";
  }
}

function wire() {
  els.btnRefresh.addEventListener("click", async () => {
    try {
      await refreshWindows();
    } catch (e) {
      alert(e.message);
    }
  });

  els.btnSelect.addEventListener("click", async () => {
    try {
      await selectWindow();
      await pollStatus();
    } catch (e) {
      alert(e.message);
    }
  });

  els.btnStart.addEventListener("click", async () => {
    try {
      await startMonitor();
      await pollStatus();
    } catch (e) {
      alert(e.message);
    }
  });

  els.btnPause.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/monitor/pause", { method: "POST" });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || res.statusText);
      }
      await pollStatus();
    } catch (e) {
      alert(e.message);
    }
  });

  els.btnResume.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/monitor/resume", { method: "POST" });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || res.statusText);
      }
      await pollStatus();
    } catch (e) {
      alert(e.message);
    }
  });

  els.btnStop.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/monitor/stop", { method: "POST" });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || res.statusText);
      }
      await pollStatus();
    } catch (e) {
      alert(e.message);
    }
  });
}

applyUiState("idle");
wire();
setInterval(pollStatus, 1500);
pollStatus();
pollHealth();
setInterval(pollHealth, 10000);
