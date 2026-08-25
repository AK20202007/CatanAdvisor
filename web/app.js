const $ = (id) => document.getElementById(id);
const HEX_WIDTH = 126;
const HEX_HEIGHT = 110;
const HEX_X = 104;
const HEX_Y = 84;
const DIRECTIONS = [[1, 0], [1, -1], [0, -1], [-1, 0], [-1, 1], [0, 1]];
const RESOURCE_LABELS = { brick: 'brick', lumber: 'lumber', wool: 'wool', grain: 'grain', ore: 'ore', desert: 'desert' };
const appState = { game: null, recommendations: null, selectedTile: null, focusPlayer: null };

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

async function request(url, options = {}) {
  const headers = { ...(options.headers || {}), 'X-Catan-Token': $('token').value.trim() };
  const response = await fetch(url, { ...options, headers });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || 'Request failed');
  return payload;
}

function setStatus(label, kind = 'idle') {
  $('connection-status').textContent = label;
  $('connection-status').className = `status-dot status-${kind}`;
}

function setActivity(message, error = false) {
  $('activity').textContent = message;
  $('activity').classList.toggle('activity-error', error);
}

function formatCoordinate(tile) { return `${tile.q},${tile.r}`; }

function projectTile(tile, bounds) {
  return { x: (tile.q - bounds.minQ) * HEX_X + (tile.r - bounds.minR) * 52, y: (tile.r - bounds.minR) * HEX_Y };
}

function getBoardBounds(tiles) {
  const minQ = Math.min(...tiles.map((tile) => tile.q));
  const minR = Math.min(...tiles.map((tile) => tile.r));
  const positions = tiles.map((tile) => projectTile(tile, { minQ, minR }));
  return { minQ, minR, width: Math.max(...positions.map((point) => point.x)) + HEX_WIDTH + 36, height: Math.max(...positions.map((point) => point.y)) + HEX_HEIGHT + 36 };
}

function canonicalVertex(coords) {
  return coords.slice().sort(([q1, r1], [q2, r2]) => q1 - q2 || r1 - r2).map(([q, r]) => `${q},${r}`).join('|');
}

function vertexList(tile) {
  return DIRECTIONS.map((direction, index) => {
    const next = DIRECTIONS[(index + 1) % DIRECTIONS.length];
    return canonicalVertex([[tile.q, tile.r], [tile.q + direction[0], tile.r + direction[1]], [tile.q + next[0], tile.r + next[1]]]);
  });
}

function vertexPoint(vertex, bounds) {
  const coords = vertex.split('|').map((part) => part.split(',').map(Number));
  const points = coords.map(([q, r]) => projectTile({ q, r }, bounds));
  return { x: points.reduce((sum, point) => sum + point.x, 0) / points.length + HEX_WIDTH / 2, y: points.reduce((sum, point) => sum + point.y, 0) / points.length + HEX_HEIGHT / 2 };
}

function pieceMarkers() {
  return (appState.game?.players || []).flatMap((player) => [
    ...player.settlements.map((piece) => ({ ...piece, type: 'settlement', player: player.id })),
    ...player.cities.map((piece) => ({ ...piece, type: 'city', player: player.id })),
  ]);
}

function renderBoard() {
  const canvas = $('board-canvas');
  const tiles = appState.game?.board?.tiles || [];
  canvas.replaceChildren();
  if (!tiles.length) { $('board-heading').textContent = 'No tiles in this state'; return; }
  const bounds = getBoardBounds(tiles);
  canvas.style.width = `${Math.max(bounds.width, 620)}px`;
  canvas.style.height = `${Math.max(bounds.height, 420)}px`;
  $('board-heading').textContent = `${tiles.length} tiles · click to edit`;

  const vertices = new Set(tiles.flatMap(vertexList));
  vertices.forEach((vertex) => {
    const point = vertexPoint(vertex, bounds);
    const dot = element('button', 'vertex-dot');
    dot.type = 'button'; dot.title = `Place ${$('board-mode').value} at ${vertex}`;
    dot.style.left = `${point.x - 7}px`; dot.style.top = `${point.y - 7}px`;
    dot.addEventListener('click', () => handleVertexClick(vertex));
    canvas.append(dot);
  });

  tiles.forEach((tile) => {
    const point = projectTile(tile, bounds);
    const hex = element('button', `hex resource-${tile.resource}`);
    hex.type = 'button'; hex.style.left = `${point.x}px`; hex.style.top = `${point.y}px`;
    if (appState.selectedTile?.q === tile.q && appState.selectedTile?.r === tile.r) hex.classList.add('selected');
    const resource = element('span', 'hex-resource', RESOURCE_LABELS[tile.resource] || tile.resource);
    hex.append(resource);
    if (tile.number) hex.append(element('span', 'number-token', tile.number));
    if (appState.game.board.robber.q === tile.q && appState.game.board.robber.r === tile.r) hex.append(element('span', 'robber-marker', 'robber'));
    hex.addEventListener('click', () => handleTileClick(tile));
    canvas.append(hex);
  });

  pieceMarkers().forEach((piece) => {
    const point = vertexPoint(piece.vertex, bounds);
    const marker = element('span', `piece-marker piece-${piece.type}`, piece.type === 'city' ? '◆' : '●');
    marker.dataset.player = piece.player;
    marker.title = `${piece.player} ${piece.type}`;
    marker.style.left = `${point.x - 12}px`; marker.style.top = `${point.y - 12}px`;
    canvas.append(marker);
  });
}

function renderPlayers() {
  const players = appState.game?.players || [];
  const select = $('active-player');
  const current = appState.focusPlayer || appState.game?.activePlayer;
  select.replaceChildren(...players.map((player) => {
    const option = new Option(`${player.id} · ${player.victoryPoints} VP`, player.id);
    option.selected = player.id === current;
    return option;
  }));
  const active = players.find((player) => player.id === current) || players[0];
  const summary = $('player-summary'); summary.replaceChildren();
  if (!active) return;
  const name = element('strong', null, active.id);
  const vp = element('span', null, `${active.victoryPoints} VP`);
  const resources = element('small', null, Object.entries(active.resources).map(([nameKey, count]) => `${nameKey} ${count}`).join(' · '));
  summary.append(name, vp, resources);
}

function renderBuild(build) {
  const container = $('build'); container.replaceChildren(); container.classList.remove('empty-state');
  if (!build) { container.classList.add('empty-state'); container.textContent = 'No legal build found.'; return; }
  const title = element('div', 'recommendation-title', build.type.replace('_', ' '));
  title.append(element('span', null, `${Number(build.score).toFixed(1)} pts`));
  container.append(title, element('p', null, build.reasoning), element('code', null, build.location || 'anywhere'));
}

function renderTrades(trades) {
  const container = $('trades'); container.replaceChildren(); container.classList.remove('empty-state');
  if (!trades.length) { container.classList.add('empty-state'); container.textContent = 'No trade needed right now.'; return; }
  trades.slice(0, 3).forEach((trade) => {
    const row = element('div', 'trade-line');
    row.append(element('strong', null, Object.entries(trade.give).map(([name, count]) => `${count} ${name}`).join(', ')));
    row.append(element('span', null, `→ ${Object.entries(trade.receive).map(([name, count]) => `${count} ${name}`).join(', ')}`));
    row.append(element('small', null, `with ${trade.offerTo}`));
    container.append(row);
  });
}

function renderRobber(robber) {
  const container = $('robber'); container.replaceChildren(); container.classList.remove('empty-state');
  if (!robber) { container.classList.add('empty-state'); container.textContent = 'No robber target found.'; return; }
  const title = element('div', 'recommendation-title', `Move to ${robber.tile}`);
  title.append(element('span', null, `${robber.score} pts`));
  container.append(title, element('p', null, robber.reasoning), element('small', null, `Blocks: ${robber.blockedPlayers.join(', ')}`));
}

function renderRecommendations(data) { appState.recommendations = data; renderBuild(data.recommendedBuild); renderTrades(data.recommendedTrades || []); renderRobber(data.robber); }

function renderState(state) {
  appState.game = state; renderPlayers(); renderBoard(); $('state').textContent = JSON.stringify(state, null, 2);
  if (appState.selectedTile) selectTile(appState.selectedTile, false);
}

function selectTile(tile, redraw = true) {
  appState.selectedTile = { q: tile.q, r: tile.r };
  $('inspector-title').textContent = `Tile ${formatCoordinate(tile)}`;
  $('selection-badge').textContent = tile.resource;
  $('resource-editor').value = tile.resource; $('number-editor').value = tile.number ?? '';
  $('tile-editor').hidden = false; $('building-editor').hidden = true; $('inspector-empty').hidden = true;
  if (redraw) renderBoard();
}

function handleTileClick(tile) { if ($('board-mode').value === 'tile') { selectTile(tile); setActivity(`Editing tile ${formatCoordinate(tile)}.`); } }

async function handleVertexClick(vertex) {
  const mode = $('board-mode').value; if (mode === 'tile') return;
  try {
    setActivity(`Placing ${mode} at ${vertex}…`);
    await request('/api/build', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ playerId: $('active-player').value, type: mode, location: vertex }) });
    await refresh(); setActivity(`${mode} recorded for ${$('active-player').value}.`);
  } catch (error) { setActivity(error.message, true); }
}

async function refresh() {
  setStatus('Syncing…', 'busy');
  const state = await request('/api/state'); renderState(state);
  const playerId = appState.focusPlayer || $('active-player').value;
  const query = playerId ? `?player_id=${encodeURIComponent(playerId)}` : '';
  const recommendations = await request(`/api/recommendations${query}`);
  renderRecommendations(recommendations); setStatus('Connected', 'online'); setActivity('Board synced.');
}

async function saveTile() {
  if (!appState.selectedTile) return;
  await request('/api/board/tile', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...appState.selectedTile, resource: $('resource-editor').value, number: $('number-editor').value }) });
  await refresh(); setActivity(`Tile ${formatCoordinate(appState.selectedTile)} updated.`);
}

async function moveRobber() {
  if (!appState.selectedTile) return;
  await request('/api/robber', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(appState.selectedTile) });
  await refresh(); setActivity(`Robber moved to ${formatCoordinate(appState.selectedTile)}.`);
}

async function applyRoll() {
  await request('/api/roll', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ roll: Number($('roll').value) }) });
  await refresh(); setActivity(`Roll ${$('roll').value} applied.`);
}

function setMode() {
  const mode = $('board-mode').value; const buildingMode = mode !== 'tile';
  $('tile-editor').hidden = true; $('building-editor').hidden = !buildingMode; $('inspector-empty').hidden = buildingMode;
  $('building-type-label').textContent = mode; $('mode-hint').textContent = buildingMode ? `Click an open point to place a ${mode} for ${$('active-player').value}.` : 'Click any hex to edit its resource or number.';
  document.body.classList.toggle('building-mode', buildingMode); renderBoard();
}

$('connect-button').addEventListener('click', () => refresh().catch((error) => { setStatus('Offline', 'error'); setActivity(error.message, true); }));
$('refresh-button').addEventListener('click', () => refresh().catch((error) => setActivity(error.message, true)));
$('save-tile-button').addEventListener('click', () => saveTile().catch((error) => setActivity(error.message, true)));
$('robber-button').addEventListener('click', () => moveRobber().catch((error) => setActivity(error.message, true)));
$('roll-button').addEventListener('click', () => applyRoll().catch((error) => setActivity(error.message, true)));
$('board-mode').addEventListener('change', setMode);
$('active-player').addEventListener('change', () => { appState.focusPlayer = $('active-player').value; setMode(); refresh().catch((error) => setActivity(error.message, true)); });
$('cancel-building-button').addEventListener('click', () => { $('board-mode').value = 'tile'; setMode(); });
$('resource-editor').addEventListener('change', () => { if ($('resource-editor').value === 'desert') $('number-editor').value = ''; });
setMode();
