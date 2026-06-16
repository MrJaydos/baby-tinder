const GENDER_LABEL = { M: 'Boy', F: 'Girl', N: 'Neutral' };
const GENDER_EMOJI = { M: '♂', F: '♀', N: '⚥' };
const ANIM_MS = 250;
const SWIPE_THRESHOLD = 80; // px

let currentName = null;
let prefetched  = null;
let isSwiping   = false;

let dragStartX = 0;
let dragStartY = 0;
let isDragging = false;

async function _fetchName() {
  const res = await fetch('/api/next-name', { cache: 'no-store' });
  return res.json();
}

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

  const imgEl = document.getElementById('card-img');
  const placeholder = document.getElementById('card-img-placeholder');
  if (imgEl && placeholder) {
    imgEl.style.opacity = '0';
    placeholder.style.opacity = '1';
    imgEl.onload = () => { placeholder.style.opacity = '0'; imgEl.style.opacity = '1'; };
    imgEl.onerror = () => {};
    imgEl.src = `/api/name-image/${data.id}`;
  }

  const hintLike = document.getElementById('hint-like');
  const hintNope = document.getElementById('hint-nope');
  if (hintLike) hintLike.style.opacity = '0';
  if (hintNope) hintNope.style.opacity = '0';

  // Clear all inline drag styles then play enter animation from clean state
  card.style.cssText = '';
  card.classList.remove('card-exit-right', 'card-exit-left', 'card-enter', 'is-dragging');
  void card.offsetWidth;
  card.classList.add('card-enter');
}

async function swipe(liked, dragAnimated = false) {
  if (!currentName || isSwiping) return;
  isSwiping = true;

  const nameId = currentName.id;
  const card = document.getElementById('name-card');

  if (!dragAnimated) {
    // Button / keyboard path — use CSS keyframe animation
    card.style.cssText = '';
    card.classList.remove('card-enter');
    card.classList.add(liked ? 'card-exit-right' : 'card-exit-left');
  }
  // dragAnimated path: card is already flying via inline transition set in onDragEnd

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

  if (prefetched && !prefetched.done && prefetched.id === nameId) prefetched = null;
  _prefetchNext();

  if (swipeData.matched) showMatchModal(swipeData.matched_name);
  else loadNextName();
}

// ── Drag swipe via Pointer Events ──────────────────────────────────────────
// Pointer Events unify touch + mouse into one API.
// setPointerCapture keeps tracking the pointer even when it leaves the card.

function onDragStart(e) {
  if (isSwiping || !currentName || e.button !== 0) return;

  const card = document.getElementById('name-card');
  card.setPointerCapture(e.pointerId); // all future pointer events route here

  dragStartX = e.clientX;
  dragStartY = e.clientY;
  isDragging = true;

  // Stop any in-progress CSS animation and lock card at full opacity
  card.classList.remove('card-enter', 'card-exit-right', 'card-exit-left');
  card.style.animation  = 'none';
  card.style.transition = 'none';
  card.style.opacity    = '1';
  card.style.transform  = 'translateX(0) rotate(0deg)';
  card.classList.add('is-dragging');
}

function onDragMove(e) {
  if (!isDragging) return;

  const dx = e.clientX - dragStartX;
  const dy = e.clientY - dragStartY;

  const card     = document.getElementById('name-card');
  const hintLike = document.getElementById('hint-like');
  const hintNope = document.getElementById('hint-nope');

  card.style.transform = `translateX(${dx}px) translateY(${dy * 0.15}px) rotate(${dx * 0.12}deg)`;
  card.style.opacity   = String(Math.max(0.35, 1 - Math.abs(dx) / 220));

  if (hintLike && hintNope) {
    if (dx > 0) {
      hintLike.style.opacity = String(Math.min(1, dx / 70));
      hintNope.style.opacity = '0';
    } else {
      hintNope.style.opacity = String(Math.min(1, -dx / 70));
      hintLike.style.opacity = '0';
    }
  }
}

function onDragEnd(e) {
  if (!isDragging) return;
  isDragging = false;

  const dx = e.clientX - dragStartX;
  const card     = document.getElementById('name-card');
  const hintLike = document.getElementById('hint-like');
  const hintNope = document.getElementById('hint-nope');

  card.classList.remove('is-dragging');

  if (!isSwiping && currentName && Math.abs(dx) >= SWIPE_THRESHOLD) {
    const liked = dx > 0;
    card.style.transition = `transform ${ANIM_MS}ms ease-out, opacity ${ANIM_MS}ms ease-out`;
    card.style.transform  = `translateX(${liked ? '130vw' : '-130vw'}) rotate(${liked ? 35 : -35}deg)`;
    card.style.opacity    = '0';
    if (hintLike) hintLike.style.opacity = '0';
    if (hintNope) hintNope.style.opacity = '0';
    swipe(liked, true);
  } else {
    // Snap back with a spring bounce
    card.style.transition = 'transform 0.3s cubic-bezier(0.25,1.5,0.5,1), opacity 0.2s ease';
    card.style.transform  = 'translateX(0) rotate(0deg)';
    card.style.opacity    = '1';
    if (hintLike) hintLike.style.opacity = '0';
    if (hintNope) hintNope.style.opacity = '0';
    setTimeout(() => { if (!isDragging) card.style.transition = 'none'; }, 320);
  }
}

// ── Modals ─────────────────────────────────────────────────────────────────

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
  const container = document.getElementById('card-container');
  if (container) {
    await loadNextName();
    _prefetchNext();
  }

  document.getElementById('like-btn')?.addEventListener('click', () => swipe(true));
  document.getElementById('dislike-btn')?.addEventListener('click', () => swipe(false));

  document.getElementById('match-modal-close')?.addEventListener('click', closeMatchModal);
  document.getElementById('match-modal-keep-swiping')?.addEventListener('click', closeMatchModal);

  // Pointer events: unified touch + mouse; setPointerCapture routes moves to the card
  const card = document.getElementById('name-card');
  if (card) {
    card.addEventListener('pointerdown',   onDragStart);
    card.addEventListener('pointermove',   onDragMove);
    card.addEventListener('pointerup',     onDragEnd);
    card.addEventListener('pointercancel', onDragEnd);
  }

  document.addEventListener('keydown', (e) => {
    if (!document.getElementById('card-container')) return;
    if (e.key === 'ArrowRight' || e.key === 'l') swipe(true);
    if (e.key === 'ArrowLeft'  || e.key === 'h') swipe(false);
  });
});
