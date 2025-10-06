const $ = s => document.querySelector(s);
const eventsEl = $('#events');
const filterBar = document.querySelector('.filters');
const spotlightEl = $('#spotlight');
const heatmapEl = $('#heatmap');
const heatmapGrid = $('#heatmap-bars');

const DATASET_FILTERS = new Set(['all', 'today', 'tonight']);
const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const TAG_STYLE = {
    date: 'badge--date', girls: 'badge--girls', quiz: 'badge--quiz',
    cinema: 'badge--cinema', rave: 'badge--rave'
};

let currentList = [];
let highlightTimer;
let activeDatasetKey = 'all';

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

function setActive(value, scope) {
    const selector = scope ? `.filters [data-scope="${scope}"]` : '.filters [data-filter]';
    document.querySelectorAll(selector).forEach((btn) => {
        const isActive = value !== null && btn.dataset.filter === value;
        btn.classList.toggle('chip--active', isActive);
    });
}

function getDataset(key) {
    if (key === 'today') return window.__TODAY || [];
    if (key === 'tonight') return window.__TONIGHT || [];
    return window.__ALL || [];
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
    if (DATASET_FILTERS.has(tag)) {
        activeDatasetKey = tag;
        const data = getDataset(tag);
        paint(data);
        setActive(activeDatasetKey, 'dataset');
        setActive(null, 'tag');
        currentList = data;
        clearSpotlight();
        return;
    }

    const source = getDataset(activeDatasetKey);
    const data = source.filter(e => (e.tags || []).includes(tag));
    paint(data);
    setActive(activeDatasetKey, 'dataset');
    setActive(tag, 'tag');
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
    for (const url of sources) {
        try {
            const data = await fetchJson(url);
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

async function fetchJson(url) {
    const cacheBust = `v=${Date.now()}`;
    const separator = url.includes('?') ? '&' : '?';
    const response = await fetch(`${url}${separator}${cacheBust}`);
    if (!response.ok) throw new Error(response.statusText);
    return response.json();
}

async function loadSupplemental(url) {
    try {
        const data = await fetchJson(url);
        return data;
    } catch (err) {
        console.warn(`Failed to load ${url}`, err);
        return null;
    }
}

function renderHeatmap(map) {
    if (!heatmapEl || !heatmapGrid) return;
    if (!map) {
        heatmapEl.hidden = true;
        heatmapGrid.innerHTML = '';
        return;
    }

    const values = WEEKDAYS.map(day => {
        const value = Number(map[day] ?? 0);
        return Number.isFinite(value) ? value : 0;
    });
    const max = Math.max(...values, 1);

    heatmapGrid.replaceChildren();

    WEEKDAYS.forEach((day, index) => {
        const value = values[index];
        const item = document.createElement('div');
        item.className = 'heatmap__item';
        item.setAttribute('role', 'listitem');

        const bar = document.createElement('div');
        bar.className = 'heatmap__bar';
        bar.dataset.empty = value === 0 ? 'true' : 'false';
        const height = value === 0 ? 6 : 6 + Math.round((value / max) * 46);
        bar.style.height = `${height}px`;
        bar.title = `${day}: ${value} event${value === 1 ? '' : 's'}`;
        item.appendChild(bar);

        const count = document.createElement('span');
        count.className = 'heatmap__count';
        count.textContent = String(value);
        item.appendChild(count);

        const label = document.createElement('span');
        label.className = 'heatmap__day';
        label.textContent = day;
        item.appendChild(label);

        heatmapGrid.appendChild(item);
    });

    heatmapEl.hidden = false;
}

async function boot() {
    const [all, today, tonight, heatmap] = await Promise.all([
        loadEvents(),
        loadSupplemental('./data/today.json'),
        loadSupplemental('./data/tonight.json'),
        loadSupplemental('./data/heatmap.json')
    ]);

    window.__ALL = all;
    window.__TODAY = Array.isArray(today) ? today : [];
    window.__TONIGHT = Array.isArray(tonight) ? tonight : [];

    if (heatmap && typeof heatmap === 'object' && !Array.isArray(heatmap)) {
        renderHeatmap(heatmap);
    } else {
        renderHeatmap(null);
    }

    activeDatasetKey = 'all';
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
