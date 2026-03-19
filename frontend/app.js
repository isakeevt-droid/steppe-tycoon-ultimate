const API = window.location.origin;

let state = null;
let telegramId = localStorage.getItem("steppe_tg_id") || "";
let username = localStorage.getItem("steppe_username") || "";
let activeTab = localStorage.getItem("steppe_active_tab") || "overview";
let isTelegramMode = false;

const locks = {};
let lastErrorAt = 0;
let chestTickerStarted = false;

const $ = (id) => document.getElementById(id);

function withLock(key, fn) {
  if (locks[key]) {
    return Promise.resolve();
  }

  locks[key] = true;

  return Promise.resolve()
    .then(fn)
    .finally(() => {
      locks[key] = false;
    });
}

function addFastHandler(element, handler) {
  if (!element) {
    return;
  }

  element.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    handler();
  });
}

function bindTabControls() {
  document.querySelectorAll(".tab, .mobile-nav-btn").forEach((btn) => {
    btn.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      activateTab(btn.dataset.tab);
    });
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
    let message = "Ошибка запроса";

    if (typeof data.detail === "string") {
      message = data.detail;
    } else if (Array.isArray(data.detail) && data.detail.length) {
      message = data.detail
        .map((item) => item.msg || item.message || "Ошибка валидации")
        .join(", ");
    } else if (typeof data.message === "string" && data.message) {
      message = data.message;
    }

    throw new Error(message);
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

function getResourceAmount(resourceKey) {
  const item = safeArray(state?.resources).find((resource) => resource.key === resourceKey);
  return Number(item?.amount || 0);
}

function getRecipeInputKey(recipeKey) {
  const map = {
    mill: "grain",
    weavery: "wool",
    planks: "wood",
    forge: "ore",
  };

  return map[recipeKey] || "";
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

function renderQuickActionButtons() {
  if (!state || !state.player) {
    return;
  }

  const dirhamCost = format(state.player.dirham_price || 0);
  const storageCost = format(state.player.storage_upgrade_cost || 0);
  const mineCost = format(state.player.mine_upgrade_cost || 0);

  const dirhamBtn = $("buy_dirham_btn");
  const storageBtn = $("upgrade_storage_btn");
  const mineBtn = $("upgrade_mine_btn");
  const chestBtn = $("open_chest_btn");
  const quickInfo = $("quick_info");

  if (dirhamBtn) {
    dirhamBtn.textContent = `💠 Купить 1 дирхам — ${dirhamCost} золота`;
    dirhamBtn.disabled = Number(state.player.gold || 0) < Number(state.player.dirham_price || 0);
  }

  if (storageBtn) {
    storageBtn.textContent = `📦 Улучшить склад — ${storageCost} золота`;
    storageBtn.disabled = Number(state.player.gold || 0) < Number(state.player.storage_upgrade_cost || 0);
  }

  if (mineBtn) {
    mineBtn.textContent = `⛏️ Улучшить шахту — ${mineCost} золота`;
    mineBtn.disabled = Number(state.player.gold || 0) < Number(state.player.mine_upgrade_cost || 0);
  }

  const hasChestState =
    Object.prototype.hasOwnProperty.call(state.player, "chest_available") ||
    Object.prototype.hasOwnProperty.call(state.player, "chest_ready_in_seconds");

  if (chestBtn) {
    if (hasChestState) {
      const chestAvailable = Boolean(state.player.chest_available);
      const chestSeconds = Number(state.player.chest_ready_in_seconds || 0);

      if (chestAvailable) {
        chestBtn.textContent = "🎁 Открыть сундук";
        chestBtn.disabled = false;
      } else {
        chestBtn.textContent = `🎁 Сундук через ${formatTime(chestSeconds)}`;
        chestBtn.disabled = true;
      }

      if (quickInfo) {
        quickInfo.textContent = chestAvailable
          ? "Сундук готов к открытию."
          : `До открытия сундука: ${formatTime(chestSeconds)}`;
      }
    } else {
      chestBtn.textContent = "🎁 Открыть сундук";
      chestBtn.disabled = false;

      if (quickInfo) {
        quickInfo.textContent =
          `💠 Дирхам: ${dirhamCost} золота • 📦 Склад: ${storageCost} • ⛏️ Шахта: ${mineCost}`;
      }
    }
  }
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
    addFastHandler(btn, () => {
      withLock(`building:${btn.dataset.building}`, () => buyBuilding(btn.dataset.building).catch(showError));
    });
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
    addFastHandler(btn, () => {
      withLock(`worker:${btn.dataset.worker}`, () => hireWorker(btn.dataset.worker).catch(showError));
    });
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
    addFastHandler(btn, () => {
      withLock(`sell:${btn.dataset.resource}`, () =>
        sellResource(btn.dataset.resource, Number(btn.dataset.amount)).catch(showError),
      );
    });
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
    addFastHandler(btn, () => {
      withLock(`claim:${btn.dataset.caravanId}`, () => claimCaravan(btn.dataset.caravanId).catch(showError));
    });
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
  renderQuickActionButtons();
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
    throw new Error("Введите Telegram ID");
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

    if (typeof tg.disableVerticalSwipes === "function") {
      tg.disableVerticalSwipes();
    }
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
  const inputKey = getRecipeInputKey(recipeKey);

  if (inputKey && getResourceAmount(inputKey) < 10) {
    throw new Error("Недостаточно сырья");
  }

  state = await api("/api/process", "POST", {
    telegram_id: telegramId,
    recipe_key: recipeKey,
    amount: 10,
  });
  renderAll();
}

async function sellResource(resourceKey, amount) {
  if (!amount || amount <= 0) {
    throw new Error("Некорректное количество");
  }

  if (getResourceAmount(resourceKey) < amount) {
    throw new Error("Недостаточно ресурса");
  }

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
  state = await api("/api/mine/click", "POST", {
    telegram_id: telegramId,
  });
  renderTopBar();
  renderOverview();
}

async function upgradeMine() {
  state = await api("/api/mine/upgrade", "POST", {
    telegram_id: telegramId,
  });
  renderAll();
}

async function sendCaravan() {
  const routeKey = $("route_select").value;
  const guardLevel = $("guard_select").value;
  const resourceKey = $("caravan_resource_select").value;
  const amount = Number($("caravan_amount_input").value || "0");

  if (!routeKey) {
    throw new Error("Выбери маршрут");
  }

  if (!resourceKey) {
    throw new Error("Выбери ресурс");
  }

  if (!amount || amount <= 0) {
    throw new Error("Укажи количество больше 0");
  }

  if (getResourceAmount(resourceKey) < amount) {
    throw new Error("Недостаточно ресурса для каравана");
  }

  state = await api("/api/caravan/send", "POST", {
    telegram_id: telegramId,
    route_key: routeKey,
    guard_level: guardLevel,
    resource_key: resourceKey,
    amount,
  });

  renderAll();
}

async function claimCaravan(id) {
  if (!id) {
    throw new Error("Не найден ID каравана");
  }

  state = await api("/api/caravan/claim", "POST", {
    telegram_id: telegramId,
    caravan_id: Number(id),
  });
  renderAll();
}

async function openChest() {
  const hasChestState =
    state &&
    state.player &&
    (Object.prototype.hasOwnProperty.call(state.player, "chest_available") ||
      Object.prototype.hasOwnProperty.call(state.player, "chest_ready_in_seconds"));

  if (hasChestState && !state.player.chest_available) {
    throw new Error(`Сундук ещё не готов: ${formatTime(state.player.chest_ready_in_seconds || 0)}`);
  }

  state = await api("/api/chest/open", "POST", {
    telegram_id: telegramId,
  });
  renderAll();
}

function showError(error) {
  const now = Date.now();

  if (now - lastErrorAt < 1200) {
    return;
  }

  lastErrorAt = now;
  alert(error.message || "Ошибка");
}

function bindStaticButtons() {
  addFastHandler($("auth_btn"), () => {
    withLock("auth", () => authManual().catch(showError));
  });

  addFastHandler($("buy_dirham_btn"), () => {
    withLock("dirham", () => buyDirham().catch(showError));
  });

  addFastHandler($("upgrade_storage_btn"), () => {
    withLock("storage", () => upgradeStorage().catch(showError));
  });

  addFastHandler($("open_chest_btn"), () => {
    withLock("chest", () => openChest().catch(showError));
  });

  addFastHandler($("upgrade_mine_btn"), () => {
    withLock("mine_upgrade", () => upgradeMine().catch(showError));
  });

  addFastHandler($("mine_click_btn"), () => {
    withLock("mine_click", () => mineClick().catch(showError));
  });

  addFastHandler($("send_caravan_btn"), () => {
    withLock("send_caravan", () => sendCaravan().catch(showError));
  });

  document.querySelectorAll(".process-btn").forEach((btn) => {
    addFastHandler(btn, () => {
      withLock(`process:${btn.dataset.recipe}`, () => processRecipe(btn.dataset.recipe).catch(showError));
    });
  });

  document.querySelectorAll(".worker-upgrade-btn").forEach((btn) => {
    addFastHandler(btn, () => {
      withLock(`worker_upgrade:${btn.dataset.upgrade}`, () => upgradeWorker(btn.dataset.upgrade).catch(showError));
    });
  });
}

function startChestTicker() {
  if (chestTickerStarted) {
    return;
  }

  chestTickerStarted = true;

  setInterval(() => {
    if (!state || !state.player) {
      return;
    }

    if (
      Object.prototype.hasOwnProperty.call(state.player, "chest_available") &&
      Object.prototype.hasOwnProperty.call(state.player, "chest_ready_in_seconds") &&
      !state.player.chest_available &&
      Number(state.player.chest_ready_in_seconds) > 0
    ) {
      state.player.chest_ready_in_seconds -= 1;

      if (state.player.chest_ready_in_seconds <= 0) {
        state.player.chest_ready_in_seconds = 0;
        state.player.chest_available = true;
      }

      renderQuickActionButtons();
    }
  }, 1000);
}

bindStaticButtons();
startChestTicker();

setInterval(() => {
  if (!telegramId) {
    return;
  }

  loadState().catch(() => {});
}, 5000);

fillAuthInputs();
bootTelegramAuth().catch(showError);