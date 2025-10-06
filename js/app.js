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
    eventsEl.innerHTML = '';

    if (!list.length) {
        const emptyState = document.createElement('p');
        emptyState.style.opacity = '.7';
        emptyState.textContent = 'No events yet. Try another filter or check back later.';
        eventsEl.appendChild(emptyState);
        return;
    }

    const fragment = document.createDocumentFragment();

    list.forEach((event, idx) => {
        const article = document.createElement('article');
        article.className = 'card';
        article.dataset.index = String(idx);

        const meta = document.createElement('span');
        meta.className = 'meta';
        (event.tags || []).forEach(tag => {
            const badge = document.createElement('span');
            const classes = ['badge'];
            if (TAG_STYLE[tag]) classes.push(TAG_STYLE[tag]);
            badge.className = classes.join(' ');
            badge.textContent = tag;
            meta.appendChild(badge);
        });
        article.appendChild(meta);

        const title = document.createElement('h3');
        title.textContent = event.title || 'Untitled event';
        article.appendChild(title);

        const details = [event.when, event.where].filter(Boolean).join(' • ');
        if (details) {
            const detailEl = document.createElement('p');
            detailEl.textContent = details;
            article.appendChild(detailEl);
        }

        if (event.url) {
            const link = document.createElement('a');
            link.href = event.url;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.textContent = 'Open';
            article.appendChild(link);
        }

        fragment.appendChild(article);
    });

    eventsEl.appendChild(fragment);
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

    spotlightEl.replaceChildren();

    const intro = document.createElement('strong');
    intro.textContent = 'Inspire me';
    spotlightEl.appendChild(intro);

    const title = document.createElement('div');
    title.className = 'spotlight__title';
    title.textContent = event.title || 'Untitled event';
    spotlightEl.appendChild(title);

    const whenWhere = [event.when, event.where].filter(Boolean).join(' • ');
    if (whenWhere) {
        const meta = document.createElement('div');
        meta.className = 'spotlight__meta';
        meta.textContent = whenWhere;
        spotlightEl.appendChild(meta);
    }

    if (event.url) {
        const link = document.createElement('a');
        link.className = 'spotlight__link';
        link.href = event.url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = 'Open event';
        spotlightEl.appendChild(link);
    }

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
