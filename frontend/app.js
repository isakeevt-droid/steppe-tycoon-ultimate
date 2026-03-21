const API = window.location.origin;
const AUTO_CLEAR_KEY = 'steppe_hidden_completed_caravans';
const TG_ID_CACHE_KEY = 'steppe_tg_id';
const TG_NAME_CACHE_KEY = 'steppe_tg_name';
const TG_INIT_CACHE_KEY = 'steppe_tg_init';
const ACTIVE_TAB_KEY = 'steppe_active_tab';
const BUILDING_FILTER_KEY = 'steppe_building_filter';

let state = null;
let telegramId = '';
let username = '';
let activeTab = localStorage.getItem(ACTIVE_TAB_KEY) || 'buildings';
let buildingFilter = localStorage.getItem(BUILDING_FILTER_KEY) || 'producing';
let refreshTimer = null;
let recentBuiltBuildingKey = null;
let mineQueuedClicks = 0;
let mineWorkerRunning = false;
let mineVisualSeed = 0;

const $ = (id) => document.getElementById(id);
const ICONS = {
  gold: '🪙', dirhams: '💠', storage: '📦', title: '👑',
  grain: '🌾', wool: '🐑', wood: '🪵', ore: '⛏️', flour: '🥣', cloth: '🧵', planks: '🪚', metal: '🔩',
  farm: '🌾', pasture: '🐑', lumbermill: '🪵', ore_mine: '⛰️', mill: '🥣', weavery: '🧵', carpentry: '🪚', forge: '🔥',
};
const GUARD_META = {
  none: { name: 'Без охраны', risk_reduction: 0, cost_dirhams: 0 },
  basic: { name: 'Базовая', risk_reduction: 15, cost_dirhams: 1 },
  experienced: { name: 'Опытная', risk_reduction: 25, cost_dirhams: 2 },
  elite: { name: 'Элитная', risk_reduction: 100, cost_dirhams: 4 },
};

const fmt = (v, d = 2) => Number(v || 0).toLocaleString('ru-RU', { maximumFractionDigits: d });
const timeFmt = (sec) => {
  sec = Math.max(0, Math.floor(sec || 0));
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
};
const resourceName = (key) => ({
  grain: 'Зерно', wool: 'Шерсть', wood: 'Древесина', ore: 'Руда', flour: 'Мука', cloth: 'Ткань', planks: 'Доски', metal: 'Металл'
}[key] || key);

function safeHtml(id, html) {
  const el = $(id);
  if (el) el.innerHTML = html;
}
function safeText(id, text) {
  const el = $(id);
  if (el) el.textContent = text;
}
function showError(error) {
  console.error(error);
  window.alert(error?.message || String(error));
}
async function api(path, method = 'GET', body = null) {
  const options = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) options.body = JSON.stringify(body);
  const res = await fetch(`${API}${path}`, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Ошибка ${res.status}`);
  return data;
}

function getHiddenCompletedIds() {
  try {
    const raw = localStorage.getItem(AUTO_CLEAR_KEY);
    const arr = raw ? JSON.parse(raw) : [];
    return new Set(Array.isArray(arr) ? arr.map(Number) : []);
  } catch {
    return new Set();
  }
}
function setHiddenCompletedIds(set) {
  localStorage.setItem(AUTO_CLEAR_KEY, JSON.stringify(Array.from(set)));
}
function getBuildingLevel(appState, key) {
  return Number((appState?.buildings || []).find((b) => b.key === key)?.level || 0);
}

function saveTelegramSession(id, name, initData = '') {
  if (id) localStorage.setItem(TG_ID_CACHE_KEY, String(id));
  if (name) localStorage.setItem(TG_NAME_CACHE_KEY, String(name));
  if (initData) sessionStorage.setItem(TG_INIT_CACHE_KEY, initData);
}

function loadTelegramSession() {
  return {
    telegramId: localStorage.getItem(TG_ID_CACHE_KEY) || '',
    username: localStorage.getItem(TG_NAME_CACHE_KEY) || 'Игрок',
    initData: sessionStorage.getItem(TG_INIT_CACHE_KEY) || '',
  };
}

function bindLifecycleEvents() {
  document.addEventListener('visibilitychange', async () => {
    if (!document.hidden && telegramId) {
      try {
        state = await api(`/api/state/${telegramId}`);
        render({ keepScroll: false });
      } catch (error) {
        console.error('resume refresh error', error);
      }
    }
  });
  window.addEventListener('pageshow', async () => {
    if (!telegramId) return;
    try {
      state = await api(`/api/state/${telegramId}`);
      render();
    } catch (error) {
      console.error('pageshow refresh error', error);
    }
  });
}

async function bootstrap() {
  try {
    safeText('boot_status', 'Проверка сервера…');
    await api('/api/health');

    const tg = window.Telegram?.WebApp || null;
    if (tg) {
      try { tg.ready(); tg.expand(); } catch {}
    }

    const cached = loadTelegramSession();
    const initData = typeof tg?.initData === 'string' && tg.initData ? tg.initData : cached.initData;

    if (tg) {
      safeText('boot_status', 'Вход через Telegram…');
      if (initData) {
        state = await api('/api/auth/telegram', 'POST', { init_data: initData });
        const user = tg.initDataUnsafe?.user || null;
        telegramId = user?.id ? String(user.id) : String(state?.player?.telegram_id || cached.telegramId || '');
        username = user?.username || user?.first_name || cached.username || 'Игрок';
        saveTelegramSession(telegramId, username, initData);
      } else if (cached.telegramId) {
        telegramId = cached.telegramId;
        username = cached.username || 'Игрок';
        state = await api(`/api/state/${telegramId}`);
      } else {
        throw new Error('Не удалось восстановить Telegram-сессию. Открой игру заново из бота.');
      }
    } else {
      safeText('boot_status', 'Локальный вход…');
      telegramId = localStorage.getItem('steppe_local_id') || `local-${Math.random().toString(36).slice(2, 10)}`;
      username = localStorage.getItem('steppe_local_name') || 'Игрок';
      localStorage.setItem('steppe_local_id', telegramId);
      localStorage.setItem('steppe_local_name', username);
      state = await api('/api/auth', 'POST', { telegram_id: telegramId, username });
    }

    $('boot')?.classList.add('hidden');
    $('app')?.classList.remove('hidden');
    bindStaticEvents();
    bindLifecycleEvents();
    render();
    startRefreshLoop();
  } catch (error) {
    safeText('boot_status', 'Подключение не удалось.');
    safeText('boot_error', error?.message || String(error));
    $('boot_retry')?.classList.remove('hidden');
    $('boot_retry')?.addEventListener('click', bootstrap, { once: true });
  }
}

function startRefreshLoop() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(async () => {
    if (!telegramId) return;
    try {
      state = await api(`/api/state/${telegramId}`);
      render();
    } catch (error) {
      console.error('refresh error', error);
      if (String(error?.message || '').includes('Игрок не найден')) {
        try {
          const cached = loadTelegramSession();
          if (cached.initData) {
            state = await api('/api/auth/telegram', 'POST', { init_data: cached.initData });
            telegramId = String(state?.player?.telegram_id || telegramId);
            saveTelegramSession(telegramId, username || cached.username, cached.initData);
            render();
          }
        } catch (rehydrateError) {
          console.error('rehydrate error', rehydrateError);
        }
      }
    }
  }, 5000);
}

function bindStaticEvents() {
  document.querySelectorAll('.nav-btn').forEach((btn) => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab, { scrollToTop: true }));
  });
  document.querySelectorAll('.segment').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.filter === buildingFilter);
    btn.addEventListener('click', () => {
      buildingFilter = btn.dataset.filter;
      localStorage.setItem(BUILDING_FILTER_KEY, buildingFilter);
      document.querySelectorAll('.segment').forEach((el) => el.classList.toggle('active', el.dataset.filter === buildingFilter));
      renderBuildings();
    });
  });
  $('upgrade_storage_btn')?.addEventListener('click', () => doAction('/api/storage/upgrade', { telegram_id: telegramId }));
  $('send_caravan_btn')?.addEventListener('click', sendCaravan);
  $('mine_click_btn')?.addEventListener('click', mineClick);
}

function applyActiveTab(tab) {
  document.querySelectorAll('.page').forEach((el) => el.classList.toggle('active', el.id === `tab-${tab}`));
  document.querySelectorAll('.nav-btn').forEach((el) => el.classList.toggle('active', el.dataset.tab === tab));
}

function switchTab(tab, options = {}) {
  activeTab = tab || 'buildings';
  applyActiveTab(activeTab);
  if (options.scrollToTop) {
    requestAnimationFrame(() => {
      window.scrollTo({ top: 0, behavior: 'auto' });
    });
  }
}

function render() {
  if (!state?.player) return;

  renderTop();
  renderQuickActions();
  renderBuildings();
  renderWarehouse();
  renderCaravans();
  renderMine();
  renderWorkers();
  renderAchievements();
  renderLeaderboard();
  applyActiveTab(activeTab);
}

function renderTop() {
  const p = state.player;
  safeHtml('top_stats', `
    <div class="mini-card"><div class="mini-label">Золото</div><div class="mini-value">${fmt(p.gold)}</div><div class="mini-sub">Баланс</div></div>
    <div class="mini-card"><div class="mini-label">Дирхамы</div><div class="mini-value">${fmt(p.dirhams, 0)}</div><div class="mini-sub">Редкая валюта</div></div>
    <div class="mini-card"><div class="mini-label">Склад</div><div class="mini-value">${fmt(p.storage_used)} / ${fmt(p.storage_capacity)}</div><div class="mini-sub">Заполненность</div></div>
    <div class="mini-card"><div class="mini-label">Звание</div><div class="mini-value">${p.title_name}</div><div class="mini-sub">${fmt(p.rank_score)} рейтинга</div></div>
  `);
}

function renderQuickActions() {
  const p = state.player;
  const chestPreview = p.chest_preview || {};
  const activePet = p.active_pet;
  const petLine = activePet
    ? `${activePet.emoji || '🐾'} Питомец: ${activePet.name} (+${fmt(activePet.bonus_pct || 0)}%)`
    : `🐾 Шанс питомца: ${fmt(chestPreview.pet_drop_chance_pct || 0, 1)}%`;

  safeHtml('quick_actions', `
    <button class="btn" id="open_chest_btn" title="${p.chest_description || ''}">${p.chest_ready ? '🎁 Открыть сундук' : `🎁 ${timeFmt(p.chest_seconds)}`}</button>
    <button class="btn" id="buy_dirham_btn" title="${p.dirham_description || ''}">💠 Дирхам — ${fmt(p.dirham_price)}</button>
  `);

  safeHtml('quick_actions_info', `
    <div class="info-card">
      <div class="info-title">🎁 Сундук</div>
      <div class="info-desc">${p.chest_description || ''}</div>
      <div class="info-sub">Дроп: ${fmt(chestPreview.gold_min || 0, 0)}–${fmt(chestPreview.gold_max || 0, 0)} золота · дирхам ${fmt(chestPreview.dirham_chance_pct || 0, 1)}% · ${petLine}</div>
    </div>
    <div class="info-card">
      <div class="info-title">💠 Дирхамы</div>
      <div class="info-desc">${p.dirham_description || ''}</div>
      <div class="info-sub">${p.dirham_price_explainer || ''}</div>
    </div>
  `);

  $('open_chest_btn')?.addEventListener('click', () => doAction('/api/chest/open', { telegram_id: telegramId }));
  $('buy_dirham_btn')?.addEventListener('click', () => doAction('/api/dirham/buy', { telegram_id: telegramId }));
}

function buildingEmoji(key) {
  return ICONS[key] || '🏭';
}

function buildAutomationInfo(b) {
  if (b.category === 'production') {
    return {
      status: b.auto_active ? `Автопродажа · ${timeFmt(b.auto_seconds)}` : 'Автопродажа выключена',
      action: b.auto_active ? 'Отключить авто' : `Включить автопродажу · ${b.auto_cost_dirhams}💠`,
    };
  }
  const mode = b.auto_mode || 'off';
  if (!b.auto_active || mode === 'off') {
    return { status: 'Авто выключено', action: `Автопереработка · ${b.auto_cost_dirhams}💠` };
  }
  if (mode === 'process') {
    return { status: `Автопереработка · ${timeFmt(b.auto_seconds)}`, action: 'Добавить автопродажу' };
  }
  return { status: `Автопереработка + автопродажа · ${timeFmt(b.auto_seconds)}`, action: 'Отключить авто' };
}

function renderBuildings() {
  const all = Array.isArray(state.buildings) ? state.buildings : [];
  const visible = all.filter((b) => buildingFilter === 'producing' ? b.category === 'production' : b.category === 'processing');
  safeHtml('buildings_list', visible.map(buildingCard).join('') || '<div class="muted">Здания не найдены.</div>');
  if (recentBuiltBuildingKey) {
    setTimeout(() => {
      recentBuiltBuildingKey = null;
      renderBuildings();
    }, 650);
  }
}

function buildingCard(b) {
  const isBuilt = Number(b.level || 0) > 0;
  const isProduction = b.category === 'production';
  const isNew = recentBuiltBuildingKey === b.key;
  const mainText = isBuilt ? `Улучшить · ${fmt(b.price)}` : `Построить · ${fmt(b.price)}`;
  const auto = buildAutomationInfo(b);
  const stockText = isProduction ? fmt(b.resource_amount) : `${fmt(b.input_amount)} / ${fmt(b.output_amount)}`;
  const saleKey = isProduction ? b.resource_key : b.output_key;
  const saleAmount = isProduction ? Number(b.resource_amount || 0) : Number(b.output_amount || 0);
  return `
    <div class="building-card ${!isBuilt ? 'not-built' : ''} ${isNew ? 'build-pop' : ''}">
      <div class="card-head">
        <div>
          <div class="card-title"><span class="emoji">${buildingEmoji(b.key)}</span>${b.name}</div>
          <div class="card-desc">${b.description}</div>
        </div>
        <div class="card-level">ур. ${b.level}</div>
      </div>
      ${isBuilt ? `
        <div class="stat-grid">
          <div class="stat-box"><div class="stat-label">Сейчас</div><div class="stat-value">${fmt(b.current_per_min)} / мин</div></div>
          <div class="stat-box"><div class="stat-label">След. ур.</div><div class="stat-value">${fmt(b.next_per_min)} / мин</div></div>
          <div class="stat-box"><div class="stat-label">${isProduction ? 'На складе' : 'Сырьё / товар'}</div><div class="stat-value">${stockText}</div></div>
          <div class="stat-box"><div class="stat-label">Авто</div><div class="stat-value">${b.auto_active ? 'ON' : 'OFF'}</div></div>
        </div>
        <div class="mode-badge"><span>${auto.status}</span><span class="right">${isProduction ? 'x4' : (b.auto_mode === 'process_sell' ? 'x3 + x4' : 'x3')}</span></div>
        <div class="btn-stack">
          <button class="btn primary" onclick="buyBuilding('${b.key}')">${mainText}</button>
          <button class="btn" onclick="toggleAutomation('${b.key}')">${auto.action}</button>
          <div class="btn-row">
            <button class="btn" onclick="sellResource('${saleKey}', 1)" ${saleAmount < 1 ? 'disabled' : ''}>Продать 1</button>
            <button class="btn" onclick="sellResource('${saleKey}', ${saleAmount})" ${saleAmount <= 0 ? 'disabled' : ''}>Продать всё</button>
          </div>
        </div>
      ` : `
        <div class="mode-badge"><span>${isProduction ? `После постройки начнёт добывать ${resourceName(b.resource_key)}` : `После постройки: ${resourceName(b.input_key)} → ${resourceName(b.output_key)}`}</span></div>
        <div class="btn-stack"><button class="btn primary" onclick="buyBuilding('${b.key}')">${mainText}</button></div>
      `}
    </div>
  `;
}

function renderWarehouse() {
  const p = state.player;
  const pct = p.storage_capacity > 0 ? Math.max(0, Math.min(100, (p.storage_used / p.storage_capacity) * 100)) : 0;
  $('storage_fill').style.width = `${pct}%`;
  safeText('warehouse_hint', `${fmt(p.storage_used)} из ${fmt(p.storage_capacity)} занято`);
  safeText('upgrade_storage_btn', `Улучшить · ${fmt(p.storage_upgrade_cost)}`);

  const resources = (state.resources || []).slice().sort((a, b) => Number(b.amount || 0) - Number(a.amount || 0));
  safeHtml('warehouse_list', resources.map((r) => `
    <div class="resource-card">
      <div class="card-head">
        <div class="card-title"><span class="emoji">${ICONS[r.key] || '📦'}</span>${r.name}</div>
        <div class="card-level">${fmt(r.amount)}</div>
      </div>
      <div class="mode-badge"><span>Цена рынка</span><span class="right">${fmt(r.market_price)} золота</span></div>
      <div class="btn-row">
        <button class="btn" onclick="sellResource('${r.key}', 1)" ${r.amount < 1 ? 'disabled' : ''}>Продать 1</button>
        <button class="btn" onclick="sellResource('${r.key}', ${Number(r.amount || 0)})" ${r.amount <= 0 ? 'disabled' : ''}>Продать всё</button>
      </div>
    </div>
  `).join(''));
}

function updateCaravanPreview() {
  const routes = state?.caravan_routes || [];
  const route = routes.find((r) => r.key === $('route_select')?.value);
  const guard = GUARD_META[$('guard_select')?.value || 'none'] || GUARD_META.none;
  const resourceKey = $('resource_select')?.value || '';
  const amount = Number($('caravan_amount')?.value || 0);
  if (!route) {
    safeHtml('caravan_preview', '<div class="muted">Выбери маршрут, товар и охрану.</div>');
    return;
  }
  const finalRisk = Math.max(0, Number(route.risk_percent || 0) - Number(guard.risk_reduction || 0));
  safeHtml('caravan_preview', `
    <div class="caravan-meta">
      <div class="meta-row"><span class="left">Груз</span><b>${resourceKey ? `${resourceName(resourceKey)} · ${fmt(amount)}` : '—'}</b></div>
      <div class="meta-row"><span class="left">Время</span><b>${timeFmt(route.duration_seconds)}</b></div>
      <div class="meta-row"><span class="left">Риск</span><b>${fmt(finalRisk)}%</b></div>
      <div class="meta-row"><span class="left">Бонус</span><b>+${fmt((route.profit_bonus || 0) * 100)}%</b></div>
    </div>
  `);
}

function renderCaravans() {
  const routes = state.caravan_routes || [];
  const allCaravans = state.active_caravans || [];
  const hiddenCompleted = getHiddenCompletedIds();
  const active = allCaravans.filter((c) => !c.resolved);
  const completed = allCaravans.filter((c) => c.resolved && !hiddenCompleted.has(Number(c.id)));
  const prevRoute = $('route_select')?.value || '';
  const prevGuard = $('guard_select')?.value || 'none';
  const prevResource = $('resource_select')?.value || '';

  safeHtml('route_select', routes.map((r) => `<option value="${r.key}">${r.name}</option>`).join(''));
  if (routes.some((r) => r.key === prevRoute)) $('route_select').value = prevRoute;

  safeHtml('guard_select', Object.entries(GUARD_META).map(([k, g]) => `<option value="${k}">${g.name}${g.cost_dirhams ? ` · ${g.cost_dirhams}💠` : ''}</option>`).join(''));
  if (Object.keys(GUARD_META).includes(prevGuard)) $('guard_select').value = prevGuard;

  const available = (state.resources || []).filter((r) => Number(r.amount) > 0);
  safeHtml('resource_select', available.map((r) => `<option value="${r.key}">${resourceName(r.key)} (${fmt(r.amount)})</option>`).join(''));
  if (available.some((r) => r.key === prevResource)) $('resource_select').value = prevResource;

  updateCaravanPreview();
  ['route_select', 'guard_select', 'resource_select', 'caravan_amount'].forEach((id) => {
    const event = id === 'caravan_amount' ? 'input' : 'change';
    $(id)?.addEventListener(event, updateCaravanPreview);
  });

  const selectedResource = available.find((r) => r.key === ($('resource_select')?.value || available[0]?.key));
  const maxAmount = Number(selectedResource?.amount || 0);
  const amountInput = $('caravan_amount');
  if (amountInput) {
    amountInput.max = maxAmount > 0 ? String(Math.floor(maxAmount)) : '0';
    const currentAmount = Number(amountInput.value || 0);
    if (!currentAmount || currentAmount > maxAmount) amountInput.value = maxAmount > 0 ? String(Math.max(1, Math.floor(maxAmount))) : '';
  }
  document.querySelectorAll('[data-caravan-share]').forEach((btn) => {
    btn.onclick = () => {
      if (!amountInput) return;
      const share = Number(btn.dataset.caravanShare || 1);
      const next = Math.max(1, Math.floor(maxAmount * share));
      amountInput.value = String(share >= 1 ? Math.floor(maxAmount) : next);
      updateCaravanPreview();
    };
  });

  safeHtml('caravan_active', active.length ? active.map((c) => caravanCard(c, false)).join('') : '<div class="muted">Активных караванов нет.</div>');
  safeHtml('caravan_completed', completed.length ? completed.map((c) => caravanCard(c, true)).join('') : '<div class="muted">Завершённых караванов нет.</div>');
  $('clear_completed_caravans_btn').disabled = completed.length === 0;
  $('clear_completed_caravans_btn').onclick = () => {
    const next = getHiddenCompletedIds();
    completed.forEach((c) => next.add(Number(c.id)));
    setHiddenCompletedIds(next);
    renderCaravans();
  };
}

function caravanCard(c, completed) {
  const cargo = Object.entries(c.cargo || {}).map(([k, v]) => `${resourceName(k)}: ${fmt(v)}`).join(', ') || '—';
  return `
    <div class="caravan-card">
      <div class="card-head">
        <div class="card-title"><span class="emoji">🐫</span>${c.route_name}</div>
        <div class="card-level">${completed ? (c.success ? 'успех' : 'провал') : 'в пути'}</div>
      </div>
      <div class="caravan-meta">
        <div class="meta-row"><span class="left">Груз</span><b>${cargo}</b></div>
        <div class="meta-row"><span class="left">Охрана</span><b>${c.guard_name}</b></div>
        <div class="meta-row"><span class="left">Риск</span><b>${fmt(c.risk_percent)}%</b></div>
        <div class="meta-row"><span class="left">${completed ? 'Результат' : 'Осталось'}</span><b>${completed ? `${fmt(c.result_gold)} золота` : timeFmt(c.remaining_seconds)}</b></div>
      </div>
      ${c.event_text ? `<div class="hint-block" style="margin-top:8px">${c.event_text}</div>` : ''}
      ${!completed && c.remaining_seconds <= 0 ? `<button class="btn primary full" onclick="claimCaravan(${c.id})">Забрать</button>` : ''}
    </div>
  `;
}

function renderMine() {
  const p = state.player;
  safeHtml('mine_summary', `
    <div class="stat-box"><div class="stat-label">Средний тап</div><div class="stat-value">${fmt(p.mine_income)}</div></div>
    <div class="stat-box"><div class="stat-label">Крит шанс</div><div class="stat-value">${fmt(p.mine_crit_chance)}%</div></div>
  `);
  safeHtml('mine_upgrades', `
    <div class="upgrade-card">
      <div class="card-head"><div class="card-title"><span class="emoji">⛰️</span>Шахта</div><div class="card-level">ур. ${p.mine_level}</div></div>
      <div class="mode-badge"><span>Сила крита</span><span class="right">x${fmt(p.mine_crit_multiplier)}</span></div>
      <button class="btn primary full" onclick="mineUpgrade('mine')">Улучшить · ${fmt(p.mine_upgrade_cost)}</button>
    </div>
    <div class="upgrade-card">
      <div class="card-head"><div class="card-title"><span class="emoji">⛏️</span>Кирка</div><div class="card-level">ур. ${p.pickaxe_level}</div></div>
      <div class="mode-badge"><span>Базовый тап</span><span class="right">${fmt(p.mine_base_tap)}</span></div>
      <button class="btn primary full" onclick="mineUpgrade('pickaxe')">Улучшить · ${fmt(p.pickaxe_upgrade_cost)}</button>
    </div>
  `);
}


function renderWorkers() {
  const workers = Array.isArray(state.workers) ? state.workers : [];
  const upgrades = Array.isArray(state.worker_upgrades) ? state.worker_upgrades : [];
  const p = state.player || {};

  safeHtml('workers_summary', `
    <div class="mini-card"><div class="mini-label">Всего рабочих</div><div class="mini-value">${fmt(p.worker_total_count, 0)}</div><div class="mini-sub">Активный персонал</div></div>
    <div class="mini-card"><div class="mini-label">Бонус</div><div class="mini-value">+${fmt(p.worker_bonus_pct, 1)}%</div><div class="mini-sub">К общей эффективности</div></div>
    <div class="mini-card"><div class="mini-label">Зарплата</div><div class="mini-value">${fmt(p.worker_salary_per_minute)}</div><div class="mini-sub">Золота в минуту</div></div>
    <div class="mini-card"><div class="mini-label">Дирхамы</div><div class="mini-value">${fmt(p.dirhams, 0)}</div><div class="mini-sub">Для улучшений</div></div>
  `);

  safeHtml('workers_list', workers.length ? workers.map((w) => workerCard(w, upgrades)).join('') : '<div class="muted">Рабочих пока нет.</div>');
}

function workerCard(worker, upgrades) {
  const relatedUpgrades = upgrades.filter((item) => item.from_key === worker.key);
  return `
    <div class="resource-card worker-card ${worker.count <= 0 ? 'is-empty' : ''}">
      <div class="card-head">
        <div>
          <div class="card-title"><span class="emoji">👷</span>${worker.name}</div>
          <div class="card-desc">${worker.description}</div>
        </div>
        <div class="card-level">${fmt(worker.count, 0)} шт.</div>
      </div>
      <div class="stat-grid">
        <div class="stat-box"><div class="stat-label">Найм</div><div class="stat-value">${fmt(worker.hire_cost)}</div></div>
        <div class="stat-box"><div class="stat-label">Зарплата</div><div class="stat-value">${fmt(worker.salary)} / мин</div></div>
        <div class="stat-box"><div class="stat-label">Бонус</div><div class="stat-value">+${fmt(worker.efficiency_bonus_pct, 1)}%</div></div>
        <div class="stat-box"><div class="stat-label">Статус</div><div class="stat-value">${worker.count > 0 ? 'Работает' : 'Не нанят'}</div></div>
      </div>
      <div class="worker-actions">
        <div class="btn-row">
          <button class="btn primary" onclick="hireWorker('${worker.key}')">Нанять</button>
          <button class="btn" onclick="fireWorker('${worker.key}')" ${worker.count < 1 ? 'disabled' : ''}>Уволить</button>
        </div>
        ${relatedUpgrades.length ? `<div class="worker-upgrades">${relatedUpgrades.map(workerUpgradeCard).join('')}</div>` : '<div class="muted">Для этого типа больше нет улучшений.</div>'}
      </div>
    </div>
  `;
}

function workerUpgradeCard(item) {
  return `
    <div class="upgrade-pill">
      <div class="upgrade-pill-main">
        <div class="upgrade-pill-title">${item.from_name} → ${item.to_name}</div>
        <div class="upgrade-pill-sub">Улучшение за ${fmt(item.cost_dirhams, 0)}💠</div>
      </div>
      <button class="btn tiny" onclick="upgradeWorker('${item.key}')" ${!item.available ? 'disabled' : ''}>Прокачать</button>
    </div>
  `;
}

function renderAchievements() {
  const all = Array.isArray(state.achievements) ? state.achievements : [];
  const active = Array.isArray(state.active_achievements) ? state.active_achievements : all.filter((a) => !a.unlocked);
  const completed = Array.isArray(state.completed_achievements) ? state.completed_achievements : all.filter((a) => a.unlocked);
  const totalBonus = all.reduce((sum, a) => sum + (a.unlocked ? Number(a.bonus_pct || 0) : 0), 0);

  safeHtml('achievements_summary', `
    <div class="mini-card"><div class="mini-label">Открыто</div><div class="mini-value">${completed.length} / ${all.length}</div><div class="mini-sub">Всего достижений</div></div>
    <div class="mini-card"><div class="mini-label">Бонус</div><div class="mini-value">+${fmt(totalBonus)}%</div><div class="mini-sub">Суммарный бонус</div></div>
  `);

  safeHtml('achievements_active', active.length ? active.map(achievementCard).join('') : '<div class="muted">Все достижения уже открыты.</div>');
  safeHtml('achievements_completed', completed.length ? completed.map(achievementCard).join('') : '<div class="muted">Пока нет открытых достижений.</div>');
}

function achievementCard(a) {
  const threshold = Number(a.threshold || 0);
  const current = Number(a.current || 0);
  const pct = threshold > 0 ? Math.max(0, Math.min(100, (current / threshold) * 100)) : (a.unlocked ? 100 : 0);
  return `
    <div class="resource-card achievement-card ${a.unlocked ? 'is-done' : ''}">
      <div class="card-head">
        <div>
          <div class="card-title"><span class="emoji">${a.unlocked ? '🏆' : '🎯'}</span>${a.name}</div>
          <div class="card-desc">${a.description}</div>
        </div>
        <div class="card-level">+${fmt(a.bonus_pct)}%</div>
      </div>
      <div class="progress-wrap">
        <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
        <div class="progress-meta"><span>${a.unlocked ? 'Выполнено' : `${fmt(Math.min(current, threshold))} / ${fmt(threshold)}`}</span><span>${Math.round(pct)}%</span></div>
      </div>
    </div>
  `;
}

function renderLeaderboard() {
  const rows = Array.isArray(state.leaderboard) ? state.leaderboard : [];
  const me = rows.find((row) => row.username === state?.player?.username);
  safeHtml('leaderboard_summary', `
    <div class="mini-card"><div class="mini-label">Твой рейтинг</div><div class="mini-value">${fmt(state.player.rank_score)}</div><div class="mini-sub">Очки звания</div></div>
    <div class="mini-card"><div class="mini-label">Позиция</div><div class="mini-value">${me ? `#${me.rank}` : '—'}</div><div class="mini-sub">В топ-20</div></div>
  `);
  safeHtml('leaderboard_list', rows.length ? rows.map(leaderboardRow).join('') : '<div class="muted">Топ игроков пока пуст.</div>');
}

function leaderboardRow(row) {
  const isMe = row.username === state?.player?.username;
  return `
    <div class="resource-card leaderboard-row ${isMe ? 'is-me' : ''}">
      <div class="leaderboard-rank">#${row.rank}</div>
      <div class="leaderboard-main">
        <div class="leaderboard-name">${row.username || 'Игрок'}</div>
        <div class="leaderboard-sub">${row.title_name || '—'}</div>
      </div>
      <div class="leaderboard-score">${fmt(row.gold_earned)}</div>
    </div>
  `;
}


async function doAction(path, body) {
  try {
    state = await api(path, 'POST', body);
    render();
    const chest = state?.chest_open;
    if (chest) {
      const parts = [`+${fmt(chest.gold || 0, 0)} золота`];
      if (Number(chest.dirhams || 0) > 0) parts.push(`+${fmt(chest.dirhams, 0)} дирхам`);
      if (chest.pet) parts.push(`${chest.pet.emoji || '🐾'} Питомец: ${chest.pet.name}`);
      window.alert(`Сундук открыт: ${parts.join(' · ')}`);
    }
  } catch (error) {
    showError(error);
  }
}
async function buyBuilding(key) {
  try {
    const prev = getBuildingLevel(state, key);
    const nextState = await api('/api/building/buy', 'POST', { telegram_id: telegramId, building_key: key });
    const next = getBuildingLevel(nextState, key);
    if (prev === 0 && next > 0) recentBuiltBuildingKey = key;
    state = nextState;
    render();
  } catch (error) {
    showError(error);
  }
}
async function toggleAutomation(key) { await doAction('/api/building/automation', { telegram_id: telegramId, building_key: key }); }
async function hireWorker(key) { await doAction('/api/worker/hire', { telegram_id: telegramId, worker_key: key }); }
async function fireWorker(key) { await doAction('/api/worker/fire', { telegram_id: telegramId, worker_key: key }); }
async function upgradeWorker(key) { await doAction('/api/worker/upgrade', { telegram_id: telegramId, upgrade_key: key }); }
async function sellResource(key, amount) { if (Number(amount) <= 0) return; await doAction('/api/sell', { telegram_id: telegramId, resource_key: key, amount: Number(amount) }); }
async function mineUpgrade(type) { await doAction('/api/mine/upgrade', { telegram_id: telegramId, upgrade_type: type }); }
async function claimCaravan(id) { await doAction('/api/caravan/claim', { telegram_id: telegramId, caravan_id: id }); }
async function sendCaravan() {
  const routeKey = $('route_select')?.value || '';
  const guardLevel = $('guard_select')?.value || 'none';
  const resourceKey = $('resource_select')?.value || '';
  const amount = Number($('caravan_amount')?.value || 0);
  if (!routeKey || !resourceKey || amount <= 0) {
    showError(new Error('Выбери маршрут, товар и количество'));
    return;
  }
  await doAction('/api/caravan/send', { telegram_id: telegramId, route_key: routeKey, guard_level: guardLevel, resource_key: resourceKey, amount });
  $('caravan_amount').value = '';
}
function mineClick(event) {
  const btn = $('mine_click_btn');
  if (!btn) return;

  btn.classList.remove('hit');
  void btn.offsetWidth;
  btn.classList.add('hit');

  mineQueuedClicks += 1;
  mineVisualSeed += 1;

  const instantIncome = Number(state?.player?.mine_income || 1);
  const rect = btn.getBoundingClientRect();
  const hasPointer = event && typeof event.clientX === 'number' && typeof event.clientY === 'number';
  const xPercent = hasPointer
    ? Math.max(18, Math.min(82, ((event.clientX - rect.left) / rect.width) * 100))
    : 50 + ((mineVisualSeed % 5) - 2) * 8;
  const bottomOffset = hasPointer
    ? Math.max(28, Math.min(rect.height - 22, rect.bottom - event.clientY))
    : 56 + (mineVisualSeed % 4) * 10;

  spawnMineFloat(`+${fmt(instantIncome)}`, { xPercent, bottomOffset });
  runMineQueue();
}

async function runMineQueue() {
  if (mineWorkerRunning || mineQueuedClicks <= 0) return;

  mineWorkerRunning = true;

  try {
    while (mineQueuedClicks > 0) {
      mineQueuedClicks -= 1;

      const nextState = await api('/api/mine/click', 'POST', { telegram_id: telegramId });
      state = nextState;

      const click = nextState?.mine_click;
      if (click?.critical) {
        spawnMineFloat(`КРИТ ${fmt(click.income)}`, { critical: true });
      }

      renderTop();
      renderMine();
    }
  } catch (error) {
    showError(error);
  } finally {
    mineWorkerRunning = false;
    render();
    if (mineQueuedClicks > 0) {
      runMineQueue();
    }
  }
}

function spawnMineFloat(text, options = {}) {
  const layer = $('mine_float_layer');
  if (!layer) return;
  const el = document.createElement('div');
  el.className = `mine-float${options.critical ? ' is-crit' : ''}`;
  el.textContent = text;
  el.style.setProperty('--x', `${options.xPercent ?? 50}%`);
  el.style.setProperty('--y', `${options.bottomOffset ?? 46}px`);
  layer.appendChild(el);
  setTimeout(() => el.remove(), options.critical ? 920 : 720);
}

window.buyBuilding = buyBuilding;
window.toggleAutomation = toggleAutomation;
window.hireWorker = hireWorker;
window.fireWorker = fireWorker;
window.upgradeWorker = upgradeWorker;
window.sellResource = sellResource;
window.mineUpgrade = mineUpgrade;
window.claimCaravan = claimCaravan;

bootstrap();
