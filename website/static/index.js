const GENDER_LABEL = { M: 'Boy', F: 'Girl', N: 'Neutral' };
const GENDER_EMOJI = { M: '♂', F: '♀', N: '⚥' };
const ANIM_MS = 250;

let currentName = null;
let prefetched  = null; // next name fetched in background; null = not ready yet
let isSwiping   = false;

async function _fetchName() {
  const res = await fetch('/api/next-name', { cache: 'no-store' });
  return res.json();
}

// Fire-and-forget — safe to call only AFTER the current swipe is committed,
// so the server's unswiped pool is up-to-date before we sample from it.
function _prefetchNext() {
  _fetchName().then(data => { prefetched = data; }).catch(() => {});
}

async function loadNextName() {
  let data;

  if (prefetched !== null) {
    data = prefetched;
    prefetched = null;
  } else {
    data = await _fetchName();
  }

  if (data.done) { showDone(); return; }

  currentName = data;
  renderCard(data);
}

function renderCard(data) {
  const card = document.getElementById('name-card');
  if (!card) return;

  document.getElementById('card-name').textContent = data.name;

  const genderBadge = document.getElementById('card-gender');
  genderBadge.textContent = (GENDER_EMOJI[data.gender] || '') + ' ' + (GENDER_LABEL[data.gender] || data.gender);
  genderBadge.className = 'gender-badge gender-' + (data.gender || 'N').toLowerCase();

  const originEl = document.getElementById('card-origin');
  originEl.textContent = data.origin || '';
  originEl.style.display = data.origin ? '' : 'none';

  const styleEl = document.getElementById('card-style');
  styleEl.textContent = data.style || '';
  styleEl.style.display = data.style ? '' : 'none';

  document.getElementById('card-meaning').textContent = data.meaning || 'No meaning available.';

  card.classList.remove('card-exit-right', 'card-exit-left', 'card-enter');
  void card.offsetWidth; // force reflow so animation restarts cleanly
  card.classList.add('card-enter');
}

async function swipe(liked) {
  if (!currentName || isSwiping) return;
  isSwiping = true;

  const nameId = currentName.id;
  const card = document.getElementById('name-card');
  card.classList.remove('card-enter');
  card.classList.add(liked ? 'card-exit-right' : 'card-exit-left');

  // Run exit animation and swipe POST in parallel to save a round-trip
  let swipeRes;
  try {
    [swipeRes] = await Promise.all([
      fetch('/api/swipe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name_id: nameId, liked }),
      }),
      new Promise(r => setTimeout(r, ANIM_MS)),
    ]);
  } catch (e) {
    isSwiping = false;
    loadNextName();
    return;
  }

  const swipeData = await swipeRes.json();
  isSwiping = false;

  // Swipe is now committed — safe to prefetch from the updated pool.
  // Discard any stale prefetch that arrived before this swipe was recorded
  // (rare, but possible if user swiped very fast).
  if (prefetched && !prefetched.done && prefetched.id === nameId) {
    prefetched = null;
  }
  _prefetchNext();

  if (swipeData.matched) {
    showMatchModal(swipeData.matched_name);
  } else {
    loadNextName();
  }
}

function showMatchModal(name) {
  document.getElementById('match-modal-name').textContent = name;
  document.getElementById('match-modal').style.display = 'flex';
  document.body.style.overflow = 'hidden';
}

function closeMatchModal() {
  document.getElementById('match-modal').style.display = 'none';
  document.body.style.overflow = '';
  loadNextName();
}

function showDone() {
  const container = document.getElementById('card-container');
  if (!container) return;

  // Read active filters from data attributes set by the template
  const gender = container.dataset.gender || 'all';
  const origin = container.dataset.origin || '';
  const style  = container.dataset.style  || '';

  const parts = [];
  if (gender === 'M') parts.push('Boy names');
  else if (gender === 'F') parts.push('Girl names');
  else if (gender === 'N') parts.push('Neutral names');
  if (origin) parts.push(origin + ' origin');
  if (style)  parts.push(style  + ' style');

  const filterLine = parts.length
    ? `You've seen every <strong>${parts.join(', ')}</strong> name.`
    : "You've seen every name in your current preferences.";

  container.innerHTML = `
    <div class="done-message">
      <div class="done-icon">&#10024;</div>
      <h3>All done!</h3>
      <p style="color:var(--muted);font-weight:600;line-height:1.6;">
        ${filterLine}<br>
        <a href="/account">Change your preferences</a> to explore more,
        or check your <a href="/matches">matches</a>.
      </p>
    </div>`;
}

document.addEventListener('DOMContentLoaded', async () => {
  if (document.getElementById('card-container')) {
    // Await the first card so we can immediately kick off a prefetch
    // while the user reads the card — all subsequent swipes will be instant.
    await loadNextName();
    _prefetchNext();
  }

  document.getElementById('like-btn')?.addEventListener('click', () => swipe(true));
  document.getElementById('dislike-btn')?.addEventListener('click', () => swipe(false));

  document.getElementById('match-modal-close')?.addEventListener('click', closeMatchModal);
  document.getElementById('match-modal-keep-swiping')?.addEventListener('click', closeMatchModal);

  document.addEventListener('keydown', (e) => {
    if (!document.getElementById('card-container')) return;
    if (e.key === 'ArrowRight' || e.key === 'l') swipe(true);
    if (e.key === 'ArrowLeft'  || e.key === 'h') swipe(false);
  });
});
