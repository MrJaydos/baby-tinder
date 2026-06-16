const GENDER_LABEL = { M: 'Boy', F: 'Girl', N: 'Neutral' };
const GENDER_EMOJI = { M: '♂', F: '♀', N: '⚥' };
const ANIM_MS = 250;

let currentName = null;
let prefetched  = null; // next name fetched in background; null = not ready
let isSwiping   = false;

async function _fetchName() {
  const res = await fetch('/api/next-name');
  return res.json();
}

function _prefetchNext() {
  // Fire-and-forget — result stored whenever it arrives
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

  // Start fetching the card after this one while the user is reading.
  // The current card isn't swiped yet so the pool still contains it —
  // we check for that collision in swipe() and discard if needed.
  _prefetchNext();
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

  // Remove old state, trigger entrance
  card.classList.remove('card-exit-right', 'card-exit-left', 'card-enter');
  // Force reflow so removing + re-adding card-enter restarts the animation
  void card.offsetWidth;
  card.classList.add('card-enter');
}

async function swipe(liked) {
  if (!currentName || isSwiping) return;
  isSwiping = true;

  const nameId = currentName.id;
  const card = document.getElementById('name-card');
  card.classList.remove('card-enter');
  card.classList.add(liked ? 'card-exit-right' : 'card-exit-left');

  // Run exit animation and swipe POST in parallel — saves a full round-trip
  const [swipeRes] = await Promise.all([
    fetch('/api/swipe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name_id: nameId, liked }),
    }),
    new Promise(r => setTimeout(r, ANIM_MS)),
  ]);

  const swipeData = await swipeRes.json();
  isSwiping = false;

  // Discard prefetch if it somehow returned the card we just swiped
  if (prefetched && !prefetched.done && prefetched.id === nameId) {
    prefetched = null;
  }

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
  container.innerHTML = `
    <div class="done-message">
      <div class="done-icon">&#127881;</div>
      <h3>You've seen all the names!</h3>
      <p style="color:var(--muted);font-weight:600;">
        Update your <a href="/account">preferences</a> to see more,
        or check your <a href="/matches">matches</a>.
      </p>
    </div>`;
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('card-container')) {
    loadNextName();
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
