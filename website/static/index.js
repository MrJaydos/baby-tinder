let currentName = null;
let filters = { gender: 'all', origin: 'all', style: 'all' };
let isSwiping = false;

const GENDER_LABEL = { M: 'Boy', F: 'Girl', N: 'Neutral' };
const GENDER_EMOJI = { M: '♂', F: '♀', N: '⚥' };

async function loadNextName() {
  if (isSwiping) return;
  const params = new URLSearchParams(filters);
  const res = await fetch('/api/next-name?' + params.toString());
  const data = await res.json();

  if (data.done) {
    showDone();
    return;
  }

  currentName = data;
  renderCard(data);
}

function renderCard(data) {
  const card = document.getElementById('name-card');
  if (!card) return;

  card.className = 'name-card';

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

  card.classList.add('card-enter');
  setTimeout(() => card.classList.remove('card-enter'), 400);
}

async function swipe(liked) {
  if (!currentName || isSwiping) return;
  isSwiping = true;

  const card = document.getElementById('name-card');
  card.classList.add(liked ? 'card-exit-right' : 'card-exit-left');

  const res = await fetch('/api/swipe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name_id: currentName.id, liked }),
  });
  const data = await res.json();

  setTimeout(() => {
    isSwiping = false;
    if (data.matched) {
      showMatchModal(data.matched_name);
    } else {
      loadNextName();
    }
  }, 350);
}

function showMatchModal(name) {
  document.getElementById('match-modal-name').textContent = name;
  const modal = document.getElementById('match-modal');
  modal.style.display = 'flex';
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
      <p>Change your filters to see more, or check your <a href="/matches">matches</a>.</p>
    </div>`;
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('card-container')) {
    loadNextName();
  }

  document.getElementById('like-btn')?.addEventListener('click', () => swipe(true));
  document.getElementById('dislike-btn')?.addEventListener('click', () => swipe(false));

  document.getElementById('gender-filter')?.addEventListener('change', function () {
    filters.gender = this.value;
    currentName = null;
    loadNextName();
  });

  document.getElementById('origin-filter')?.addEventListener('change', function () {
    filters.origin = this.value;
    currentName = null;
    loadNextName();
  });

  document.getElementById('style-filter')?.addEventListener('change', function () {
    filters.style = this.value;
    currentName = null;
    loadNextName();
  });

  document.getElementById('match-modal-close')?.addEventListener('click', closeMatchModal);
  document.getElementById('match-modal-keep-swiping')?.addEventListener('click', closeMatchModal);

  // Keyboard shortcuts: arrow keys or vim-style h/l
  document.addEventListener('keydown', (e) => {
    if (!document.getElementById('card-container')) return;
    if (e.key === 'ArrowRight' || e.key === 'l') swipe(true);
    if (e.key === 'ArrowLeft' || e.key === 'h') swipe(false);
  });
});
