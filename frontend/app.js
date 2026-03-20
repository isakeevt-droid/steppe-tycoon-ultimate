const API = window.location.origin;
const AUTO_CLEAR_KEY = 'steppe_hidden_completed_caravans';

let state = null;
let telegramId = '';
let username = '';
let selectedTab = localStorage.getItem('steppe_tab') || 'overview';
let productionFilter = ['producing','processing'].includes(localStorage.getItem('steppe_production_filter')) ? localStorage.getItem('steppe_production_filter') : 'producing';
let refreshTimer = null;

const $ = (id) => document.getElementById(id);
const ICONS = {
  gold: '🪙', dirhams: '💠', storage: '📦', grain: '🌾', wool: '🐑', wood: '🪵', ore: '⛏️', flour: '🥣', cloth: '🧵', planks: '🪚', metal: '🔩',
  farm: '🌾', pasture: '🐑', lumbermill: '🪵', ore_mine: '⛰️', mill: '🥣', weavery: '🧵', carpentry: '🪚', forge: '🔥', mine: '⛰️', pickaxe: '⛏️', crit: '💥'
};
const GUARD_META = {
  none: { name: 'Без охраны', risk_reduction: 0, cost_dirhams: 0 },
  basic: { name: 'Базовая', risk_reduction: 15, cost_dirhams: 1 },
  experienced: { name: 'Опытная', risk_reduction: 25, cost_dirhams: 2 },
  elite: { name: 'Элитная', risk_reduction: 100, cost_dirhams: 4 },
};

function safeText(id, value) {
  const el = $(id);
  if (el) el.textContent = value;
}

function safeHtml(id, value) {
  const el = $(id);
  if (el) el.innerHTML = value;
}

async function api(path, method = 'GET', body = null) {
  const options = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) options.body = JSON.stringify(body);
  const res = await fetch(`${API}${path}`, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Ошибка ${res.status}`);
  return data;
}

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
const icon = (key) => `<span class="ico">${ICONS[key] || '◻️'}</span>`;

function showError(error) {
  const message = error?.message || String(error);
  console.error(error);
  window.alert(message);
}

function bindTabs() {
  document.querySelectorAll('.tab').forEach((btn) => {
    btn.onclick = () => activateTab(btn.dataset.tab);
  });
}

function activateTab(tab) {
  selectedTab = tab;
  localStorage.setItem('steppe_tab', tab);
  document.querySelectorAll('.tab').forEach((el) => el.classList.toggle('active', el.dataset.tab === tab));
  document.querySelectorAll('.tab-page').forEach((el) => el.classList.toggle('active', el.id === `tab-${tab}`));
}

function bindProductionFilters() {
  document.querySelectorAll('.subtab').forEach((btn) => {
    btn.onclick = () => {
      productionFilter = btn.dataset.filter;
      localStorage.setItem('steppe_production_filter', productionFilter);
      document.querySelectorAll('.subtab').forEach((el) => el.classList.toggle('active', el.dataset.filter === productionFilter));
      renderProduction();
    };
  });
}

function getHiddenCompletedIds() {
  try {
    const raw = localStorage.getItem(AUTO_CLEAR_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return new Set(Array.isArray(parsed) ? parsed.map(Number) : []);
  } catch {
    return new Set();
  }
}

function setHiddenCompletedIds(set) {
  localStorage.setItem(AUTO_CLEAR_KEY, JSON.stringify(Array.from(set)));
}

async function bootstrap() {
  try {
    safeText('boot_status', 'Проверка сервера…');
    await api('/api/health');

    const tg = window.Telegram?.WebApp || null;
    if (tg) {
      try {
        tg.ready();
        tg.expand();
      } catch {}
    }

    const initData = typeof tg?.initData === 'string' ? tg.initData : '';
    if (initData) {
      safeText('boot_status', 'Вход через Telegram…');
      try {
        state = await api('/api/auth/telegram', 'POST', { init_data: initData });
        const user = tg.initDataUnsafe?.user || null;
        telegramId = user?.id ? String(user.id) : '';
        username = user?.username || user?.first_name || 'Игрок';
        localStorage.setItem('steppe_tg_id', telegramId);
        localStorage.setItem('steppe_username', username);
      } catch (error) {
        console.warn('Telegram auth fallback:', error);
      }
    }

    if (!state) {
      safeText('boot_status', 'Локальный вход…');
      telegramId = localStorage.getItem('steppe_local_id') || `local-${Math.random().toString(36).slice(2, 10)}`;
      username = localStorage.getItem('steppe_local_name') || 'Игрок';
      localStorage.setItem('steppe_local_id', telegramId);
      localStorage.setItem('steppe_local_name', username);
      localStorage.setItem('steppe_username', username);
      state = await api('/api/auth', 'POST', { telegram_id: telegramId, username });
    }

    $('boot')?.classList.add('hidden');
    $('app')?.classList.remove('hidden');
    render();
    startRefreshLoop();
  } catch (error) {
    console.error('BOOT ERROR:', error);
    safeText('boot_status', 'Подключение не удалось.');
    safeText('boot_error', error?.message || String(error));
    $('boot_retry')?.classList.remove('hidden');
  }
}

function startRefreshLoop() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(refreshState, 5000);
}

async function refreshState() {
  if (!telegramId) return;
  try {
    state = await api(`/api/state/${telegramId}`);
    render();
  } catch (error) {
    console.error('REFRESH ERROR:', error);
  }
}

function render() {
  if (!state?.player) return;
  renderTop();
  renderNotifications();
  renderOverview();
  renderProduction();
  renderWarehouse();
  renderMine();
  renderCaravans();
  renderProgress();
  renderLeaderboard();
  bindActions();
  bindTabs();
  bindProductionFilters();
  activateTab(selectedTab);
}

function renderTop() {
  const p = state.player;
  safeHtml('top_stats', `
    <div class="stat"><div class="k">${icon('gold')} Золото</div><div class="v">${fmt(p.gold)}</div></div>
    <div class="stat"><div class="k">${icon('dirhams')} Дирхамы</div><div class="v">${fmt(p.dirhams, 0)}</div></div>
    <div class="stat"><div class="k">${icon('storage')} Склад</div><div class="v">${fmt(p.storage_used)} / ${fmt(p.storage_capacity)}</div></div>
    <div class="stat"><div class="k">💹 Бонус дохода</div><div class="v">${fmt(p.total_bonus_pct)}%</div></div>
    <div class="stat"><div class="k">👑 Звание</div><div class="v">${p.title_name}</div></div>
  `);
}

function renderNotifications() {
  const notes = state.notifications || [];
  safeHtml('notifications', notes.map((n) => `<div class="notice">⚠️ ${n}</div>`).join(''));
}

function renderOverview() {
  const p = state.player;
  const profileItems = [
    ['Имя', p.username],
    ['Рейтинг', fmt(p.rank_score)],
    ['Заработано', fmt(p.total_gold_earned)],
    ['Потрачено', fmt(p.total_gold_spent)],
    ['Произведено', fmt(p.total_resources_produced)],
    ['Переработано', fmt(p.total_resources_processed)]
  ];
  safeHtml('profile_grid', profileItems.map(([k, v]) => `
    <div class="kv"><div class="k">${k}</div><div class="v">${v}</div></div>
  `).join(''));

  const goal = state.active_achievements?.[0] || null;
  safeHtml('current_goal', goal ? `
    <div class="card">
      <h3>🎯 ${goal.name}</h3>
      <div class="muted">${goal.description}</div>
      <div class="row"><span>Прогресс</span><b>${fmt(goal.current)} / ${fmt(goal.threshold)}</b></div>
      <div class="row"><span>Бонус</span><b>+${fmt(goal.bonus_pct)}%</b></div>
    </div>
  ` : '<div class="hint">Все текущие цели выполнены.</div>');

  safeText('open_chest_btn', p.chest_ready ? '🎁 Открыть сундук' : `🎁 Сундук через ${timeFmt(p.chest_seconds)}`);
  safeText('buy_dirham_btn', `💠 Купить 1 дирхам — ${fmt(p.dirham_price)} золота`);
  safeText('overview_hint', `Средний доход шахты: ${fmt(p.mine_income)} за тап`);
}


function sellControls(resourceKey, amount, prefix = 'sell') {
  const inputId = `${prefix}_${resourceKey}`;
  return `
    <div class="btn-row">
      <input type="number" min="1" step="1" placeholder="Количество" id="${inputId}">
      <button class="btn primary" onclick="sellCustom('${resourceKey}', '${inputId}')">Продать</button>
    </div>
    <div class="hint">Доступно: ${fmt(amount)}</div>
  `;
}

function buildingCard(b) {
  const autoLabel = b.auto_kind === 'sell' ? 'авто-продажа' : 'авто-переработка';
  const autoButtonLabel = b.auto_active
    ? (b.auto_kind === 'sell' ? 'Остановить авто-продажу' : 'Остановить авто-переработку')
    : (b.auto_kind === 'sell'
        ? `Авто-продажа за ${b.auto_cost_dirhams} 💠`
        : `Авто-переработка за ${b.auto_cost_dirhams} 💠`);

  const saleResourceKey = b.category === 'production' ? b.resource_key : b.output_key;
  const saleResourceAmount = b.category === 'production' ? Number(b.resource_amount || 0) : Number(b.output_amount || 0);

  const main = b.category === 'production'
    ? `
      <div class="row"><span>Производит</span><b>${icon(b.resource_key)} ${resourceName(b.resource_key)}</b></div>
      <div class="row"><span>Сейчас</span><b>${fmt(b.current_per_min)} / мин</b></div>
      <div class="row"><span>На складе</span><b>${fmt(b.resource_amount)}</b></div>
    `
    : `
      <div class="row"><span>Переработка</span><b>${icon(b.input_key)} ${resourceName(b.input_key)} → ${icon(b.output_key)} ${resourceName(b.output_key)}</b></div>
      <div class="row"><span>Сейчас</span><b>${fmt(b.current_per_min)} / мин</b></div>
      <div class="row"><span>Сырьё / товар</span><b>${fmt(b.input_amount)} / ${fmt(b.output_amount)}</b></div>
      <div class="row"><span>К продаже</span><b>${icon(b.output_key)} ${resourceName(b.output_key)}</b></div>
    `;

  return `
    <div class="card">
      <h3>${icon(b.key)} ${b.name}</h3>
      <div class="muted">${b.description}</div>
      ${main}
      <div class="row"><span>Уровень</span><b>${b.level}</b></div>
      <div class="row"><span>После улучшения</span><b>${fmt(b.next_per_min)} / мин</b></div>
      <div class="row"><span>${autoLabel}</span><b>${b.auto_active ? `работает ${timeFmt(b.auto_seconds)}` : 'выкл.'}</b></div>
      <div class="btn-row">
        <button class="btn" onclick="buyBuilding('${b.key}')">Улучшить за ${fmt(b.price)}</button>
        <button class="btn ${b.auto_active ? 'primary' : ''}" onclick="toggleAutomation('${b.key}')">${autoButtonLabel}</button>
      </div>
      <div class="top-space">
        ${sellControls(saleResourceKey, saleResourceAmount, `prod_${b.key}`)}
      </div>
    </div>
  `;
}

function renderProduction() {
  const allBuildings = Array.isArray(state.buildings) ? state.buildings : [];
  const produced = allBuildings.filter((b) => b.category === 'production');
  const processed = allBuildings.filter((b) => b.category !== 'production');

  const visible = productionFilter === 'processing' ? processed : produced;

  safeHtml('production_counts', `
    <span>Производящие: <b>${produced.length}</b></span>
    <span>Перерабатывающие: <b>${processed.length}</b></span>
  `);
  safeHtml('production_list', visible.map(buildingCard).join('') || '<div class="hint">Здания не найдены.</div>');
}

function renderWarehouse() {
  const p = state.player;
  const ratio = p.storage_capacity > 0 ? (p.storage_used / p.storage_capacity) * 100 : 0;
  const percent = Math.max(0, Math.min(100, ratio));
  safeHtml('warehouse_summary', `
    <div class="storage-bar"><div class="storage-fill" style="width:${percent}%"></div></div>
    <div class="hint top-space">Заполнено ${fmt(p.storage_used)} из ${fmt(p.storage_capacity)}. Улучшение склада вынесено сюда.</div>
  `);
  safeText('upgrade_storage_btn', `📦 Улучшить склад — ${fmt(p.storage_upgrade_cost)} золота`);

  const raw = (state.resources || []).filter((r) => r.kind === 'raw');
  const goods = (state.resources || []).filter((r) => r.kind !== 'raw');
  const renderCard = (r, prefix) => `
    <div class="card">
      <h3>${icon(r.key)} ${r.name}</h3>
      <div class="muted">${r.kind === 'raw' ? 'Сырьё' : 'Товар'}</div>
      <div class="row"><span>На складе</span><b>${fmt(r.amount)}</b></div>
      <div class="row"><span>Цена рынка</span><b>${fmt(r.market_price)} золота</b></div>
      <div class="row"><span>Стоимость всего</span><b>${fmt(r.amount * r.market_price)}</b></div>
      ${sellControls(r.key, Number(r.amount || 0), prefix)}
    </div>
  `;

  safeHtml('warehouse_list', `
    <div class="section-title">🧺 Сырьё</div>
    ${raw.map((r) => renderCard(r, 'wh_raw')).join('')}
    <div class="section-title top-space">📦 Товары</div>
    ${goods.map((r) => renderCard(r, 'wh_goods')).join('')}
  `);
}

function renderMine() {
  const p = state.player;
  safeHtml('mine_info', `
    <div class="grid mine-grid">
      <div class="card">
        <h3>${icon('mine')} Шахта</h3>
        <div class="muted">Увеличивает силу крита и слегка повышает базовый доход.</div>
        <div class="row"><span>Уровень</span><b>${p.mine_level}</b></div>
        <div class="row"><span>Базовый тап</span><b>${fmt(p.mine_base_tap)}</b></div>
        <div class="row"><span>Сила крита</span><b>x${fmt(p.mine_crit_multiplier)}</b></div>
        <button class="btn" onclick="mineUpgrade('mine')">Улучшить шахту за ${fmt(p.mine_upgrade_cost)}</button>
      </div>
      <div class="card">
        <h3>${icon('pickaxe')} Кирка</h3>
        <div class="muted">Даёт только шанс критического удара.</div>
        <div class="row"><span>Уровень</span><b>${p.pickaxe_level}</b></div>
        <div class="row"><span>Шанс крита</span><b>${fmt(p.mine_crit_chance)}%</b></div>
        <div class="row"><span>Средний тап</span><b>${fmt(p.mine_income)}</b></div>
        <button class="btn" onclick="mineUpgrade('pickaxe')">Улучшить кирку за ${fmt(p.pickaxe_upgrade_cost)}</button>
      </div>
    </div>
  `);
}

function updateCaravanPreview() {
  const routes = state?.caravan_routes || [];
  const routeKey = $('route_select')?.value || '';
  const guardLevel = $('guard_select')?.value || 'none';
  const resourceKey = $('resource_select')?.value || '';
  const amount = Number($('caravan_amount')?.value || 0);

  const route = routes.find((r) => r.key === routeKey);
  if (!route) {
    safeText('caravan_preview', 'Выбери маршрут, охрану и груз.');
    return;
  }

  const guard = GUARD_META[guardLevel] || GUARD_META.none;
  const baseRisk = Number(route.risk_percent || 0);
  const reducedBy = Number(guard.risk_reduction || 0);
  const finalRisk = Math.max(0, baseRisk - reducedBy);
  const cargoText = resourceKey ? `${resourceName(resourceKey)}${amount > 0 ? ` (${fmt(amount)})` : ''}` : '—';

  safeHtml('caravan_preview', `
    <div class="row"><span>Груз</span><b>${cargoText}</b></div>
    <div class="row"><span>Охрана</span><b>${guard.name}${guard.cost_dirhams > 0 ? ` — ${guard.cost_dirhams} 💠` : ''}</b></div>
    <div class="row"><span>Время</span><b>${timeFmt(route.duration_seconds || 0)}</b></div>
    <div class="row"><span>Базовый риск</span><b>${fmt(baseRisk)}%</b></div>
    <div class="row"><span>Снижение от охраны</span><b>-${fmt(reducedBy)}%</b></div>
    <div class="row"><span>Итоговый риск</span><b>${fmt(finalRisk)}%</b></div>
    <div class="row"><span>Бонус маршрута</span><b>+${fmt((route.profit_bonus || 0) * 100)}%</b></div>
  `);
}

function renderCaravanCard(c, completed = false) {
  const status = c.success ? 'успех' : 'провал';
  return `
    <div class="card">
      <h3>🐫 ${c.route_name}</h3>
      <div class="row"><span>Груз</span><b>${Object.entries(c.cargo || {}).map(([k, v]) => `${resourceName(k)}: ${fmt(v)}`).join(', ')}</b></div>
      <div class="row"><span>Охрана</span><b>${c.guard_name || '—'}</b></div>
      <div class="row"><span>Риск</span><b>${fmt(c.risk_percent)}%</b></div>
      <div class="row"><span>Статус</span><b>${completed ? status : 'в пути'}</b></div>
      <div class="row">
        <span>${completed ? 'Результат' : 'Осталось'}</span>
        <b ${completed ? '' : `id="caravan_timer_${c.id}" data-seconds="${c.remaining_seconds}"`}>
          ${completed ? `${fmt(c.result_gold)} золота` : timeFmt(c.remaining_seconds)}
        </b>
      </div>
      ${completed && c.event_text ? `<div class="hint top-space">${c.event_text}</div>` : ''}
      ${!completed && c.remaining_seconds <= 0 ? `<button class="btn primary" onclick="claimCaravan(${c.id})">Забрать</button>` : ''}
    </div>
  `;
}

function renderCaravans() {
  const routes = state.caravan_routes || [];
  const caravans = state.active_caravans || [];
  const hiddenCompleted = getHiddenCompletedIds();
  const active = caravans.filter((c) => !c.resolved);
  const completed = caravans.filter((c) => c.resolved && !hiddenCompleted.has(Number(c.id)));

  const prevRoute = $('route_select')?.value || '';
  const prevGuard = $('guard_select')?.value || 'none';
  const prevResource = $('resource_select')?.value || '';

  safeHtml('route_select', routes.map((r) => `<option value="${r.key}">${r.name}</option>`).join(''));
  if (routes.some((r) => r.key === prevRoute)) $('route_select').value = prevRoute;

  safeHtml('guard_select', Object.entries(GUARD_META).map(([k, g]) => `<option value="${k}">${g.name}${g.cost_dirhams > 0 ? ` — ${g.cost_dirhams} 💠` : ''}</option>`).join(''));
  if (Object.keys(GUARD_META).includes(prevGuard)) $('guard_select').value = prevGuard;

  const availableResources = (state.resources || []).filter((r) => Number(r.amount) > 0);
  safeHtml('resource_select', availableResources.map((r) => `<option value="${r.key}">${resourceName(r.key)} (${fmt(r.amount)})</option>`).join(''));
  if (availableResources.some((r) => r.key === prevResource)) $('resource_select').value = prevResource;

  safeText('caravan_slots', `${state.player.active_caravans_count}/${state.player.max_active_caravans}`);
  safeHtml('caravan_active', active.length ? active.map((c) => renderCaravanCard(c, false)).join('') : '<div class="hint">Активных караванов нет.</div>');
  safeHtml('caravan_completed', completed.length ? completed.map((c) => renderCaravanCard(c, true)).join('') : '<div class="hint">Завершённых караванов нет.</div>');

  updateCaravanPreview();

  $('route_select').onchange = updateCaravanPreview;
  $('guard_select').onchange = updateCaravanPreview;
  $('resource_select').onchange = updateCaravanPreview;
  $('caravan_amount').oninput = updateCaravanPreview;

  const clearBtn = $('clear_completed_caravans_btn');
  if (clearBtn) {
    clearBtn.disabled = completed.length === 0;
    clearBtn.onclick = () => {
      const next = getHiddenCompletedIds();
      completed.forEach((c) => next.add(Number(c.id)));
      setHiddenCompletedIds(next);
      renderCaravans();
    };
  }
}

function renderProgress() {
  safeHtml('active_achievements', (state.active_achievements || []).map((a) => `
    <div class="card"><h3>${a.name}</h3><div class="muted">${a.description}</div><div class="row"><span>Прогресс</span><b>${fmt(a.current)} / ${fmt(a.threshold)}</b></div></div>
  `).join(''));

  safeHtml('completed_achievements', (state.completed_achievements || []).map((a) => `
    <div class="card"><h3>✅ ${a.name}</h3><div class="muted">+${fmt(a.bonus_pct)}% дохода</div></div>
  `).join('') || '<div class="hint">Пока ничего не открыто.</div>');
}

function renderLeaderboard() {
  safeHtml('leaderboard', (state.leaderboard || []).map((x) => `
    <div class="card"><div class="row"><b>#${x.rank} ${x.username}</b><span>${x.title_name}</span></div><div class="muted">${fmt(x.gold_earned)} золота</div></div>
  `).join(''));
}

function bindActions() {
  $('open_chest_btn').onclick = () => doAction('/api/chest/open', { telegram_id: telegramId });
  $('buy_dirham_btn').onclick = () => doAction('/api/dirham/buy', { telegram_id: telegramId });
  $('upgrade_storage_btn').onclick = () => doAction('/api/storage/upgrade', { telegram_id: telegramId });
  $('send_caravan_btn').onclick = sendCaravan;
  $('mine_click_btn').onclick = mineClick;
}

async function doAction(path, body) {
  try {
    state = await api(path, 'POST', body);
    render();
  } catch (err) {
    showError(err);
  }
}
async function buyBuilding(key) { await doAction('/api/building/buy', { telegram_id: telegramId, building_key: key }); }
async function toggleAutomation(key) { await doAction('/api/building/automation', { telegram_id: telegramId, building_key: key }); }
async function sell(key, amount) { if (amount <= 0) return; await doAction('/api/sell', { telegram_id: telegramId, resource_key: key, amount: Number(amount) }); }
async function sellCustom(key, inputId) {
  const input = document.getElementById(inputId);
  if (!input) return alert('Поле количества не найдено');
  const amount = Number(input.value || 0);
  if (!amount || amount <= 0) return alert('Укажи количество');
  await doAction('/api/sell', { telegram_id: telegramId, resource_key: key, amount: Number(amount) });
  input.value = '';
}
async function mineUpgrade(type) { await doAction('/api/mine/upgrade', { telegram_id: telegramId, upgrade_type: type }); }
async function mineClick() {
  try {
    state = await api('/api/mine/click', 'POST', { telegram_id: telegramId });
    render();
  } catch (err) {
    showError(err);
  }
}
async function sendCaravan() {
  const route_key = $('route_select').value;
  const guard_level = $('guard_select').value;
  const resource_key = $('resource_select').value;
  const amount = Number($('caravan_amount').value || 0);
  if (!amount) return alert('Укажи количество');
  await doAction('/api/caravan/send', { telegram_id: telegramId, route_key, guard_level, resource_key, amount });
  $('caravan_amount').value = '';
  updateCaravanPreview();
}
async function claimCaravan(id) { await doAction('/api/caravan/claim', { telegram_id: telegramId, caravan_id: id }); }

setInterval(() => {
  document.querySelectorAll('[id^="caravan_timer_"]').forEach((el) => {
    let sec = Number(el.dataset.seconds || 0);
    if (sec <= 0) return;
    sec -= 1;
    el.dataset.seconds = sec;
    el.textContent = timeFmt(sec);
  });
}, 1000);

bindTabs();
activateTab(selectedTab);
bootstrap();
$('boot_retry').onclick = bootstrap;
