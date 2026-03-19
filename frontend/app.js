const API = window.location.origin;

let state = null;
let telegramId = localStorage.getItem("steppe_tg_id") || "";
let username = localStorage.getItem("steppe_username") || "";
let activeTab = localStorage.getItem("steppe_active_tab") || "overview";
let isTelegramMode = false;

const $ = (id) => document.getElementById(id);

function bindTabControls() {
  document.querySelectorAll(".tab, .mobile-nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => activateTab(btn.dataset.tab));
  });
}

function activateTab(tabName) {
  activeTab = tabName;
  localStorage.setItem("steppe_active_tab", tabName);

  document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("active", x.dataset.tab === tabName));
  document.querySelectorAll(".mobile-nav-btn").forEach((x) => x.classList.toggle("active", x.dataset.tab === tabName));
  document.querySelectorAll(".tab-content").forEach((x) => x.classList.toggle("active", x.id === "tab-" + tabName));
}

bindTabControls();
activateTab(activeTab);

async function api(path, method = "GET", body = null) {
  const options = {
    method,
    headers: { "Content-Type": "application/json" },
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(API + path, options);
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || "Ошибка запроса");
  }

  return data;
}

function format(value) {
  return Number(value || 0).toLocaleString("ru-RU", {
    maximumFractionDigits: 2,
  });
}

function formatInt(value) {
  return Number(value || 0).toLocaleString("ru-RU", {
    maximumFractionDigits: 0,
  });
}

function formatTime(seconds) {
  const total = Math.max(0, Math.floor(Number(seconds || 0)));
  const hours = Math.floor(total / 3600);
  const mins = Math.floor((total % 3600) / 60);
  const secs = total % 60;

  if (hours > 0) {
    return `${String(hours).padStart(2, "0")}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  }

  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

function card(html) {
  const div = document.createElement("div");
  div.className = "card";
  div.innerHTML = html;
  return div;
}

function titleizeKey(key) {
  const map = {
    grain: "Зерно",
    flour: "Мука",
    wool: "Шерсть",
    cloth: "Ткань",
    wood: "Древесина",
    planks: "Доски",
    ore: "Руда",
    metal: "Металл",
  };

  return map[key] || key;
}

function resourceIcon(key) {
  const map = {
    grain: "🌾",
    flour: "🥖",
    wool: "🧶",
    cloth: "🪡",
    wood: "🪵",
    planks: "🪚",
    ore: "⛏️",
    metal: "⛓️",
  };

  return map[key] || "📦";
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function showAuthScreen() {
  $("auth_block").classList.remove("hidden");
  $("game_block").classList.add("hidden");
}

function showGameScreen() {
  $("auth_block").classList.add("hidden");
  $("game_block").classList.remove("hidden");
}

function fillAuthInputs() {
  if ($("telegram_id_input")) {
    $("telegram_id_input").value = telegramId;
  }
  if ($("username_input")) {
    $("username_input").value = username;
  }
}

function renderTopBar() {
  if (!state || !state.player) {
    return;
  }

  $("gold_value").textContent = format(state.player.gold);
  $("dirham_value").textContent = format(state.player.dirhams);
  $("storage_value").textContent = `${format(state.player.storage_used)} / ${format(state.player.storage_capacity)}`;
  $("bonus_value").textContent = `${format(state.player.total_bonus_pct)}%`;
  $("title_value").textContent = state.player.title_name || "—";
}

function renderOverview() {
  const profile = $("profile_stats");
  profile.innerHTML = "";

  const stats = [
    ["Имя", state.player.username],
    ["Рейтинг", format(state.player.rank_score)],
    ["Заработано", format(state.player.total_gold_earned)],
    ["Потрачено", format(state.player.total_gold_spent)],
    ["Произведено", format(state.player.total_resources_produced)],
    ["Переработано", format(state.player.total_resources_processed)],
    ["Караваны", formatInt(state.player.total_caravans_sent)],
    ["Успешные", formatInt(state.player.total_caravans_success)],
    ["Клики", formatInt(state.player.total_clicks)],
    ["Уровень шахты", formatInt(state.player.mine_level)],
  ];

  stats.forEach(([label, value]) => {
    const div = document.createElement("div");
    div.className = "stat";
    div.innerHTML = `
      <span class="label">${label}</span>
      <span class="value">${value}</span>
    `;
    profile.appendChild(div);
  });

  $("quick_info").textContent =
    `💠 Дирхам: ${format(state.player.dirham_price)} золота • 📦 Склад: ${format(state.player.storage_upgrade_cost)} • ⛏️ Шахта: ${format(state.player.mine_upgrade_cost)}`;

  const overview = $("overview_resources");
  overview.innerHTML = "";

  safeArray(state.resources).forEach((resource) => {
    overview.appendChild(
      card(`
        <h3>${resourceIcon(resource.key)} ${resource.name}</h3>
        <div class="row"><span>На складе</span><strong>${format(resource.amount)}</strong></div>
        <div class="row"><span>Цена</span><strong>${format(resource.market_price)}</strong></div>
        <div class="row"><span>Тип</span><strong>${resource.kind === "raw" ? "Сырьё" : "Товар"}</strong></div>
      `),
    );
  });
}

function renderBuildings() {
  const list = $("buildings_list");
  list.innerHTML = "";

  safeArray(state.buildings).forEach((item) => {
    list.appendChild(
      card(`
        <h3>🏭 ${item.name}</h3>
        <small>${item.description}</small>
        <div class="row"><span>Уровень</span><strong>${item.level}</strong></div>
        <div class="row"><span>Цена</span><strong>${format(item.price)}</strong></div>
        <button class="primary-btn" data-building="${item.key}">Купить / улучшить</button>
      `),
    );
  });

  list.querySelectorAll("[data-building]").forEach((btn) => {
    btn.onclick = () => buyBuilding(btn.dataset.building);
  });
}

function renderWorkers() {
  const list = $("workers_list");
  list.innerHTML = "";

  safeArray(state.workers).forEach((item) => {
    list.appendChild(
      card(`
        <h3>👷 ${item.name}</h3>
        <small>${item.description}</small>
        <div class="row"><span>Количество</span><strong>${item.count}</strong></div>
        <div class="row"><span>Найм</span><strong>${format(item.hire_cost)} золота</strong></div>
        <div class="row"><span>ЗП</span><strong>${format(item.salary)} / мин</strong></div>
        <div class="row"><span>Эффективность</span><strong>+${item.efficiency_bonus_pct}%</strong></div>
        <button class="primary-btn" data-worker="${item.key}">Нанять</button>
      `),
    );
  });

  list.querySelectorAll("[data-worker]").forEach((btn) => {
    btn.onclick = () => hireWorker(btn.dataset.worker);
  });
}

function renderTrade() {
  const sellList = $("sell_list");
  const caravanSelect = $("caravan_resource_select");

  sellList.innerHTML = "";
  caravanSelect.innerHTML = "";

  const availableResources = safeArray(state.resources).filter((resource) => Number(resource.amount) > 0);

  if (availableResources.length === 0) {
    sellList.appendChild(card(`<small>Пока нечего продавать. Сначала добудь или произведи ресурсы.</small>`));
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "Нет ресурсов";
    caravanSelect.appendChild(option);
    return;
  }

  availableResources.forEach((item) => {
    const sellAmount = Math.max(1, Math.floor(Number(item.amount)));

    sellList.appendChild(
      card(`
        <h3>${resourceIcon(item.key)} ${item.name}</h3>
        <div class="row"><span>Есть</span><strong>${format(item.amount)}</strong></div>
        <div class="row"><span>Цена</span><strong>${format(item.market_price)}</strong></div>
        <button class="primary-btn" data-resource="${item.key}" data-amount="${sellAmount}">Продать ${sellAmount}</button>
      `),
    );

    const option = document.createElement("option");
    option.value = item.key;
    option.textContent = `${item.name} (${format(item.amount)})`;
    caravanSelect.appendChild(option);
  });

  sellList.querySelectorAll("[data-resource]").forEach((btn) => {
    btn.onclick = () => sellResource(btn.dataset.resource, Number(btn.dataset.amount));
  });
}

function formatCargo(cargo) {
  if (!cargo || typeof cargo !== "object") {
    return "—";
  }

  const parts = Object.entries(cargo).map(([key, value]) => `${resourceIcon(key)} ${titleizeKey(key)}: ${format(value)}`);
  return parts.length ? parts.join(", ") : "—";
}

function renderCaravans() {
  const routeSelect = $("route_select");
  const list = $("caravans_list");

  routeSelect.innerHTML = "";
  list.innerHTML = "";

  safeArray(state.caravan_routes).forEach((route) => {
    const option = document.createElement("option");
    option.value = route.key;
    option.textContent = `${route.name} • ${Math.round(route.duration_seconds / 60)} мин • +${Math.round(route.profit_bonus * 100)}%`;
    routeSelect.appendChild(option);
  });

  if (!safeArray(state.active_caravans).length) {
    list.appendChild(card(`<small>Активных караванов пока нет.</small>`));
    return;
  }

  safeArray(state.active_caravans).forEach((caravan) => {
    const status = caravan.resolved
      ? caravan.success
        ? '<span class="ok">Успех</span>'
        : '<span class="bad">Провал</span>'
      : '<span class="warn">В пути</span>';

    const actionBlock = !caravan.resolved
      ? caravan.remaining_seconds > 0
        ? `<button class="primary-btn" disabled>В пути: ${formatTime(caravan.remaining_seconds)}</button>`
        : `<button class="primary-btn claim-btn" data-caravan-id="${caravan.id}">Забрать награду</button>`
      : `<small>Награда: ${format(caravan.result_gold)} золота, ${caravan.result_dirhams} дирхамов</small>`;

    list.appendChild(
      card(`
        <h3>🐫 ${caravan.route_name || caravan.route_key}</h3>
        <div class="row"><span>Статус</span><strong>${status}</strong></div>
        <div class="row"><span>Охрана</span><strong>${caravan.guard_name || caravan.guard_level}</strong></div>
        <div class="row"><span>Груз</span><strong>${formatCargo(caravan.cargo)}</strong></div>
        <div class="row"><span>Риск</span><strong>${format(caravan.risk_percent)}%</strong></div>
        <div class="row"><span>Осталось</span><strong>${formatTime(caravan.remaining_seconds)}</strong></div>
        <div class="row"><span>Потенциал</span><strong>${format(caravan.expected_profit)}</strong></div>
        ${caravan.event_text ? `<div class="row"><span>Событие</span><strong>${caravan.event_text}</strong></div>` : ""}
        ${actionBlock}
      `),
    );
  });

  list.querySelectorAll(".claim-btn").forEach((btn) => {
    btn.onclick = () => claimCaravan(btn.dataset.caravanId);
  });
}

function renderAchievements() {
  const achievementsList = $("achievements_list");
  const titlesList = $("titles_list");

  achievementsList.innerHTML = "";
  titlesList.innerHTML = "";

  safeArray(state.achievements).forEach((item) => {
    achievementsList.appendChild(
      card(`
        <h3>🏆 ${item.name}</h3>
        <small>${item.description}</small>
        <div class="row"><span>Прогресс</span><strong>${format(item.current)} / ${format(item.threshold)}</strong></div>
        <div class="row"><span>Бонус к общему доходу</span><strong>+${item.bonus_pct}%</strong></div>
        <div class="progress"><span style="width:${item.progress_pct}%"></span></div>
        <small>${item.unlocked ? "Получено" : "В процессе"}</small>
      `),
    );
  });

  safeArray(state.titles).forEach((item) => {
    titlesList.appendChild(
      card(`
        <h3>👑 ${item.name}</h3>
        <div class="row"><span>Требование</span><strong>${format(item.score)}</strong></div>
        <div class="row"><span>Бонус к общему доходу</span><strong>+${item.bonus_pct}%</strong></div>
        <div class="progress"><span style="width:${item.progress_pct}%"></span></div>
        <small>${item.unlocked ? "Открыто" : "Не открыто"}</small>
      `),
    );
  });
}

function renderLeaderboard() {
  const list = $("leaderboard_list");
  list.innerHTML = "";

  safeArray(state.leaderboard).forEach((row) => {
    list.appendChild(
      card(`
        <h3>📈 #${row.rank} — ${row.username}</h3>
        <div class="row"><span>Заработано</span><strong>${format(row.gold_earned)}</strong></div>
        <div class="row"><span>Звание</span><strong>${row.title_name}</strong></div>
      `),
    );
  });
}

function renderAll() {
  if (!state) {
    return;
  }

  renderTopBar();
  renderOverview();
  renderBuildings();
  renderWorkers();
  renderTrade();
  renderCaravans();
  renderAchievements();
  renderLeaderboard();
}

async function loadState() {
  if (!telegramId) {
    return;
  }

  state = await api(`/api/state/${telegramId}`);
  showGameScreen();
  renderAll();
}

async function authManual() {
  telegramId = $("telegram_id_input").value.trim();
  username = $("username_input").value.trim() || "Игрок";

  if (!telegramId) {
    alert("Введите Telegram ID");
    return;
  }

  localStorage.setItem("steppe_tg_id", telegramId);
  localStorage.setItem("steppe_username", username);

  state = await api("/api/auth", "POST", {
    telegram_id: telegramId,
    username,
  });

  showGameScreen();
  renderAll();
}

async function authTelegram(initData) {
  state = await api("/api/auth/telegram", "POST", {
    init_data: initData,
  });

  telegramId = String(state.player.telegram_id || "");
  username = state.player.username || "Игрок";

  localStorage.setItem("steppe_tg_id", telegramId);
  localStorage.setItem("steppe_username", username);

  showGameScreen();
  renderAll();
}

async function bootTelegramAuth() {
  const tg = window.Telegram?.WebApp;

  if (!tg) {
    fillAuthInputs();
    if (telegramId) {
      await loadState();
    } else {
      showAuthScreen();
    }
    return;
  }

  try {
    tg.ready();
    tg.expand();
  } catch (_) {}

  const initData = tg.initData || "";
  const user = tg.initDataUnsafe?.user || null;

  if (!initData || !user?.id) {
    fillAuthInputs();
    if (telegramId) {
      await loadState();
    } else {
      showAuthScreen();
    }
    return;
  }

  isTelegramMode = true;
  await authTelegram(initData);
}

async function buyBuilding(buildingKey) {
  state = await api("/api/building/buy", "POST", {
    telegram_id: telegramId,
    building_key: buildingKey,
  });
  renderAll();
}

async function hireWorker(workerKey) {
  state = await api("/api/worker/hire", "POST", {
    telegram_id: telegramId,
    worker_key: workerKey,
  });
  renderAll();
}

async function upgradeWorker(upgradeKey) {
  state = await api("/api/worker/upgrade", "POST", {
    telegram_id: telegramId,
    upgrade_key: upgradeKey,
  });
  renderAll();
}

async function processRecipe(recipeKey) {
  state = await api("/api/process", "POST", {
    telegram_id: telegramId,
    recipe_key: recipeKey,
    amount: 10,
  });
  renderAll();
}

async function sellResource(resourceKey, amount) {
  state = await api("/api/sell", "POST", {
    telegram_id: telegramId,
    resource_key: resourceKey,
    amount,
  });
  renderAll();
}

async function buyDirham() {
  state = await api("/api/dirham/buy", "POST", {
    telegram_id: telegramId,
  });
  renderAll();
}

async function upgradeStorage() {
  state = await api("/api/storage/upgrade", "POST", {
    telegram_id: telegramId,
  });
  renderAll();
}

async function mineClick() {
  const oldGold = Number(state?.player?.gold || 0);
  const clickIncome = Number(state?.player?.mine_click_income || 1);

  state.player.gold = oldGold + clickIncome;
  renderTopBar();

  try {
    state = await api("/api/mine/click", "POST", {
      telegram_id: telegramId,
    });
    renderAll();
  } catch (error) {
    state.player.gold = oldGold;
    renderTopBar();
    showError(error);
  }
}

async function upgradeMine() {
  state = await api("/api/mine/upgrade", "POST", {
    telegram_id: telegramId,
  });
  renderAll();
}

async function sendCaravan() {
  const amount = Number($("caravan_amount_input").value || "0");

  state = await api("/api/caravan/send", "POST", {
    telegram_id: telegramId,
    route_key: $("route_select").value,
    guard_level: $("guard_select").value,
    resource_key: $("caravan_resource_select").value,
    amount,
  });

  renderAll();
}

async function claimCaravan(id) {
  if (!id) {
    alert("Не найден ID каравана");
    return;
  }

  try {
    state = await api("/api/caravan/claim", "POST", {
      telegram_id: telegramId,
      caravan_id: Number(id),
    });
    renderAll();
  } catch (error) {
    alert(error.message || "Не удалось забрать награду");
  }
}

async function openChest() {
  state = await api("/api/chest/open", "POST", {
    telegram_id: telegramId,
  });
  renderAll();
}

function showError(error) {
  alert(error.message || "Ошибка");
}

$("auth_btn").onclick = () => authManual().catch(showError);
$("buy_dirham_btn").onclick = () => buyDirham().catch(showError);
$("upgrade_storage_btn").onclick = () => upgradeStorage().catch(showError);
$("open_chest_btn").onclick = () => openChest().catch(showError);
$("upgrade_mine_btn").onclick = () => upgradeMine().catch(showError);
$("mine_click_btn").addEventListener("pointerdown", (e) => {
  e.preventDefault();
  mineClick().catch(showError);
});
$("send_caravan_btn").onclick = () => sendCaravan().catch(showError);

document.querySelectorAll(".process-btn").forEach((btn) => {
  btn.onclick = () => processRecipe(btn.dataset.recipe).catch(showError);
});

document.querySelectorAll(".worker-upgrade-btn").forEach((btn) => {
  btn.onclick = () => upgradeWorker(btn.dataset.upgrade).catch(showError);
});

setInterval(() => {
  if (!telegramId) {
    return;
  }
  loadState().catch(() => {});
}, 5000);

fillAuthInputs();
bootTelegramAuth().catch(showError);