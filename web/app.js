const $ = (id) => document.getElementById(id);

async function request(url, options = {}) {
  const headers = {...(options.headers || {}), 'X-Catan-Token': $('token').value};
  const response = await fetch(url, {...options, headers});
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || 'Request failed');
  return payload;
}

function renderRecommendations(data) {
  $('build').textContent = JSON.stringify(data.recommendedBuild, null, 2);
  $('trades').textContent = JSON.stringify(data.recommendedTrades, null, 2);
  $('robber').textContent = JSON.stringify(data.robber, null, 2);
}

async function refresh() {
  const [recommendations, state] = await Promise.all([
    request('/api/recommendations'),
    request('/api/state'),
  ]);
  renderRecommendations(recommendations);
  $('state').textContent = JSON.stringify(state, null, 2);
}

$('roll-button').addEventListener('click', async () => {
  try {
    const data = await request('/api/roll', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({roll: Number($('roll').value)}),
    });
    renderRecommendations(data.recommendations);
    await refresh();
  } catch (error) { alert(error.message); }
});

$('refresh-button').addEventListener('click', () => refresh().catch((error) => alert(error.message)));
