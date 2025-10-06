const $ = s => document.querySelector(s);
const eventsEl = $('#events');
const filterBar = document.querySelector('.filters');
const spotlightEl = $('#spotlight');

const TAG_STYLE = {
    date: 'badge--date', girls: 'badge--girls', quiz: 'badge--quiz',
    cinema: 'badge--cinema', rave: 'badge--rave'
};

let currentList = [];
let highlightTimer;

function paint(list) {
    if (!list.length) {
        eventsEl.innerHTML = `<p style="opacity:.7">No events yet. Try another filter or check back later.</p>`;
        return;
    }
    eventsEl.innerHTML = list.map((e, idx) => {
        const tags = (e.tags || []).map(t => `<span class="badge ${TAG_STYLE[t] || ''}">${t}</span>`).join('');
        return `<article class="card" data-index="${idx}">
      <span class="meta">${tags}</span>
      <h3>${e.title}</h3>
      <p>${e.when} • ${e.where}</p>
      <a href="${e.url}" target="_blank" rel="noopener">Open</a>
    </article>`;
    }).join('');
}

function setActive(tag) {
    document.querySelectorAll('.filters .chip').forEach(b =>
        b.classList.toggle('chip--active', b.dataset.filter === tag)
    );
}

function clearSpotlight() {
    if (!spotlightEl) return;
    spotlightEl.hidden = true;
    spotlightEl.classList.remove('spotlight--visible');
    spotlightEl.textContent = '';
    if (highlightTimer) {
        clearTimeout(highlightTimer);
        highlightTimer = null;
    }
    eventsEl.querySelectorAll('.card--highlight').forEach(el => el.classList.remove('card--highlight'));
}

function applyFilter(tag) {
    const all = window.__ALL || [];
    const data = tag === 'all' ? all : all.filter(e => (e.tags || []).includes(tag));
    paint(data);
    setActive(tag);
    currentList = data;
    clearSpotlight();
}

function showSpotlight(event) {
    if (!spotlightEl) return;
    const whenWhere = [event.when, event.where].filter(Boolean).join(' • ');
    const link = event.url ? `<a class="spotlight__link" href="${event.url}" target="_blank" rel="noopener">Open event</a>` : '';
    const metaHtml = whenWhere ? `<div class="spotlight__meta">${whenWhere}</div>` : '';
    const html = `<strong>Inspire me</strong>
    <div class="spotlight__title">${event.title}</div>
    ${metaHtml}
    ${link}`;
    spotlightEl.innerHTML = html.trim();
    spotlightEl.hidden = false;
    spotlightEl.classList.add('spotlight--visible');
}

function highlightCard(index) {
    const card = eventsEl.querySelector(`.card[data-index="${index}"]`);
    if (!card) return;
    eventsEl.querySelectorAll('.card--highlight').forEach(el => el.classList.remove('card--highlight'));
    card.classList.add('card--highlight');
    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    if (highlightTimer) clearTimeout(highlightTimer);
    highlightTimer = setTimeout(() => {
        card.classList.remove('card--highlight');
        highlightTimer = null;
    }, 1500);
}

async function loadEvents() {
    const sources = [
        './data/events.json',
        './data/events.sample.json'
    ];
    const cacheBust = `v=${Date.now()}`;

    for (const url of sources) {
        const separator = url.includes('?') ? '&' : '?';
        try {
            const response = await fetch(`${url}${separator}${cacheBust}`);
            if (!response.ok) throw new Error(response.statusText);
            const data = await response.json();
            if (Array.isArray(data) && data.length) return data;
        } catch (err) {
            console.warn(`Failed to load ${url}`, err);
        }
    }

    console.warn('Falling back to embedded sample data');
    return [
        { title: "Quiz at Det Akademiske Kvarter", when: "Thu 20:00", where: "Kvarteret", tags: ["quiz"], url: "https://kvarteret.no/" },
        { title: "Midnight Rave", when: "Fri 23:59", where: "USF Verftet", tags: ["rave"], url: "https://ra.co/" },
        { title: "Paint n’ Sip", when: "Sat 18:00", where: "Kulturhuset", tags: ["girls", "date"], url: "https://ticketco.events/" },
        { title: "Cinema: Sci-Fi Classics", when: "Tonight 21:15", where: "Bergen Kino", tags: ["cinema", "date"], url: "https://bergenkino.no/" }
    ];
}

async function boot() {
    window.__ALL = await loadEvents();
    applyFilter('all');
}
boot();

filterBar.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-filter]');
    if (!btn) return;
    applyFilter(btn.dataset.filter);
});

$('#surprise')?.addEventListener('click', () => {
    const list = currentList.length ? currentList : (window.__ALL || []);
    if (!list.length) return;
    const idx = Math.floor(Math.random() * list.length);
    const event = list[idx];
    showSpotlight(event);
    highlightCard(idx);
});

$('#year').textContent = new Date().getFullYear();
