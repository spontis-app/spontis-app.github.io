const $ = selector => document.querySelector(selector);

const eventsEl = $('#events');
const filterShell = document.querySelector('.filters');
const stickyFilterBar = $('#filter-chips');
const legacyFilterBar = document.querySelector('#filters.filters--legacy') || document.querySelector('.filters.filters--legacy');
const filterBar = stickyFilterBar || legacyFilterBar || filterShell;
const filterContainers = [filterBar].filter(Boolean);
const spotlightEl = $('#spotlight');
const heatmapEl = $('#heatmap');
const heatmapGrid = $('#heatmap-bars');
const clusterDeckEl = $('#cluster-deck');
const densityEl = $('#density-map');
const sourceRollupEl = $('#source-rollup');

const DATASET_OPTIONS = [
    { key: 'all', label: 'All events' },
    { key: 'today', label: 'Today' },
    { key: 'tonight', label: 'Tonight' }
];
const DATASET_FILTERS = new Set(DATASET_OPTIONS.map(option => option.key));

const BASE_TAG_ORDER = ['date', 'dj', 'live', 'jazz', 'culture', 'cinema', 'festival', 'lecture', 'bar', 'girls', 'quiz', 'rave'];

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const TAG_STYLE = {
    date: 'badge--date',
    girls: 'badge--girls',
    quiz: 'badge--quiz',
    cinema: 'badge--cinema',
    rave: 'badge--rave',
    live: 'badge--live',
    dj: 'badge--dj',
    jazz: 'badge--jazz',
    bar: 'badge--bar',
    culture: 'badge--culture',
    opening: 'badge--opening',
    lecture: 'badge--lecture',
    festival: 'badge--festival',
    source: 'badge--source'
};

const TAG_LABELS = {
    all: 'All',
    bar: 'Bar night 🍸',
    culture: 'Culture 🎭',
    date: 'Date night ❤️',
    dj: 'DJ set 🎧',
    festival: 'Festival 🌟',
    girls: "Girls' night 🍷",
    jazz: 'Jazz 🎷',
    lecture: 'Talks 🎤',
    live: 'Live 🎸',
    opening: 'Opening ✨',
    quiz: 'Quiz 🍻',
    cinema: 'Cinema 🎥',
    rave: 'Rave 🔊'
};

const SMART_TAG_RULES = [
    { tag: 'live', pattern: /\bkonsert\b|\blive\b|concert|gig|setlist|band/iu },
    { tag: 'dj', pattern: /\bdj\b|selector|club\s?night|techno|house|rave|club/iu },
    { tag: 'jazz', pattern: /jazz|swing|impro(vis|v)|sax/iu },
    { tag: 'girls', pattern: /girls'?\s?night|ladies'?|venninn/iu },
    { tag: 'date', pattern: /date\s?night|romance|romantisk|couples?/iu },
    { tag: 'cinema', pattern: /cinema|kino|screening|film/iu },
    { tag: 'bar', pattern: /vinylbar|bar\b|cocktail|taproom|pub/iu },
    { tag: 'culture', pattern: /kultur|museum|gallery|teater|theatre|performance/iu },
    { tag: 'opening', pattern: /opening|vernissage|launch|grand opening|åpning/iu },
    { tag: 'lecture', pattern: /lecture|talk|samtale|conversation|panel|debate|foredrag|seminar|artist talk|workshop/iu },
    { tag: 'festival', pattern: /festival|weekender|marathon|takeover|all-?nighter/iu }
];

const TAG_ALLOW_LIST = new Set([
    ...Object.keys(TAG_STYLE),
    ...BASE_TAG_ORDER,
    ...SMART_TAG_RULES.map(rule => rule.tag)
]);

const VIBE_PROFILES = [
    {
        id: 'techno',
        label: 'Techno',
        keywords: ['techno', 'club', 'rave', 'acid', 'house', 'electro', 'warehouse', 'dancefloor'],
        tagHints: ['rave', 'dj'],
        sourceHints: ['resident advisor', 'ra.', 'østre', 'ekko']
    },
    {
        id: 'jazz',
        label: 'Jazz',
        keywords: ['jazz', 'sax', 'saxophone', 'improv', 'soul', 'swing', 'blues', 'bebop'],
        tagHints: ['jazz'],
        sourceHints: ['nattjazz']
    },
    {
        id: 'performance',
        label: 'Performance',
        keywords: ['konsert', 'concert', 'performance', 'show', 'theatre', 'theater', 'dance', 'ballet', 'cinema', 'screening'],
        tagHints: ['cinema', 'date', 'girls', 'live', 'culture'],
        sourceHints: ['kultur', 'teater', 'theatre', 'bergen kino']
    },
    {
        id: 'talks',
        label: 'Talks',
        keywords: ['talk', 'lecture', 'conversation', 'debate', 'panel', 'quiz', 'workshop', 'seminar'],
        tagHints: ['lecture', 'quiz'],
        sourceHints: ['litteraturhuset', 'library']
    },
    {
        id: 'experimental',
        label: 'Experimental',
        keywords: ['experimental', 'modular', 'ambient', 'noise', 'avant', 'installation', 'future', 'drone'],
        tagHints: ['experimental'],
        sourceHints: ['østre', 'ekko', 'bit teatergarasjen']
    }
];

const VIBE_LOOKUP = Object.fromEntries(VIBE_PROFILES.map(profile => [profile.id, profile]));

const WEEK = [
    { index: 1, short: 'Mon', full: 'Monday' },
    { index: 2, short: 'Tue', full: 'Tuesday' },
    { index: 3, short: 'Wed', full: 'Wednesday' },
    { index: 4, short: 'Thu', full: 'Thursday' },
    { index: 5, short: 'Fri', full: 'Friday' },
    { index: 6, short: 'Sat', full: 'Saturday' },
    { index: 0, short: 'Sun', full: 'Sunday' }
];

const datasets = { all: [], today: [], tonight: [] };
let currentList = [];
let currentFilter = null;
let highlightTimer;
let activeDatasetKey = 'all';

function normalizeTagValue(tag) {
    if (!tag && tag !== 0) return null;
    const slug = String(tag)
        .toLowerCase()
        .replace(/[^a-z0-9\s-]+/g, ' ')
        .trim()
        .replace(/\s+/g, '-');
    if (!slug || !TAG_ALLOW_LIST.has(slug)) return null;
    return slug;
}

function sanitizeTagList(tags) {
    if (!tags || !tags.length) return [];
    const clean = [];
    for (const tag of tags) {
        const normalized = normalizeTagValue(tag);
        if (normalized && !clean.includes(normalized)) {
            clean.push(normalized);
        }
    }
    return sortTags(clean);
}

function sortTags(tags) {
    const order = BASE_TAG_ORDER;
    const weight = tag => {
        const idx = order.indexOf(tag);
        if (idx !== -1) return idx;
        const first = typeof tag === 'string' && tag.length ? tag.charCodeAt(0) : 0;
        return order.length + first / 100;
    };
    return [...tags].sort((a, b) => {
        const diff = weight(a) - weight(b);
        return diff === 0 ? a.localeCompare(b) : diff;
    });
}

function normalizeText(text = '') {
    return text.toLowerCase().replace(/[^a-z0-9æøåäöüß ]+/gi, ' ').replace(/\s+/g, ' ').trim();
}

function labelForTag(tag) {
    return TAG_LABELS[tag] || tag.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function inferRelativeDayIndex(text) {
    if (!text) return null;
    const normalized = text.toLowerCase();
    const today = new Date();

    if (/\b(today|tonight)\b/.test(normalized)) {
        return today.getDay();
    }

    if (/\btomorrow\b/.test(normalized)) {
        return (today.getDay() + 1) % 7;
    }

    return null;
}

function parseTimeFromText(text) {
    if (!text) return null;
    const match = text.match(/(\d{1,2})(?::(\d{2}))?/);
    if (!match) return null;
    let hours = Number.parseInt(match[1], 10);
    if (Number.isNaN(hours)) return null;
    let minutes = match[2] ? Number.parseInt(match[2], 10) : 0;
    if (Number.isNaN(minutes)) minutes = 0;
    hours = Math.max(0, Math.min(23, hours));
    minutes = Math.max(0, Math.min(59, minutes));
    return hours * 60 + minutes;
}

const RELATIVE_DAY_WEIGHT = 10000;
const RELATIVE_NO_TIME_WEIGHT = 9000;
const RELATIVE_NO_INFO_WEIGHT = 11000;

function getEventSortKey(event) {
    if (event.starts_at) {
        const parsed = new Date(event.starts_at);
        if (!Number.isNaN(parsed.getTime())) {
            return { type: 'absolute', value: parsed.getTime() };
        }
    }

    let dayIndex = typeof event.dayIndex === 'number' ? event.dayIndex : null;
    if (dayIndex == null) {
        const relative = inferRelativeDayIndex(event.when);
        if (typeof relative === 'number') {
            dayIndex = relative;
        }
    }

    const normalizedDay = dayIndex == null ? 8 : (dayIndex === 0 ? 7 : dayIndex);
    const minutes = parseTimeFromText(event.when);
    const minuteWeight = minutes != null
        ? minutes
        : (dayIndex == null ? RELATIVE_NO_INFO_WEIGHT : RELATIVE_NO_TIME_WEIGHT);

    return {
        type: 'relative',
        value: normalizedDay * RELATIVE_DAY_WEIGHT + minuteWeight
    };
}

function compareEvents(a, b) {
    const aKey = getEventSortKey(a);
    const bKey = getEventSortKey(b);

    if (aKey.type === 'absolute' && bKey.type === 'absolute') {
        const diff = aKey.value - bKey.value;
        if (diff !== 0) return diff;
    }

    if (aKey.type === 'absolute') return -1;
    if (bKey.type === 'absolute') return 1;

    const diff = aKey.value - bKey.value;
    if (diff !== 0) return diff;

    const titleA = (a.title || '').toLowerCase();
    const titleB = (b.title || '').toLowerCase();
    if (titleA !== titleB) return titleA.localeCompare(titleB);

    const urlA = (a.url || '').toLowerCase();
    const urlB = (b.url || '').toLowerCase();
    return urlA.localeCompare(urlB);
}

function sortByEventTime(events) {
    return events.slice().sort(compareEvents);
}

function getDayInfo(event) {
    if (typeof event.dayIndex === 'number') {
        const match = WEEK.find(day => day.index === event.dayIndex);
        return match || null;
    }

    if (event.starts_at) {
        const parsed = new Date(event.starts_at);
        if (!Number.isNaN(parsed)) {
            const match = WEEK.find(day => day.index === parsed.getDay());
            if (match) return match;
        }
    }

    if (event.when) {
        const dayMatch = event.when.match(/\b(mon|tue|wed|thu|fri|sat|sun)\b/i);
        if (dayMatch) {
            const dayKey = dayMatch[1].slice(0, 3).toLowerCase();
            const info = WEEK.find(day => day.short.toLowerCase() === dayKey);
            if (info) return info;
        }

        const relative = inferRelativeDayIndex(event.when);
        if (typeof relative === 'number') {
            const info = WEEK.find(day => day.index === relative);
            if (info) return info;
        }
    }

    return null;
}

function buildDedupeKey(raw) {
    const titleKey = normalizeText(raw.title || '');
    const venueKey = normalizeText(raw.venue || raw.where || '');
    let dateKey = '';

    if (raw.starts_at) {
        const parsed = new Date(raw.starts_at);
        if (!Number.isNaN(parsed.getTime())) {
            dateKey = parsed.toISOString().slice(0, 10);
        }
    }

    if (!dateKey && raw.when) {
        dateKey = String(raw.when).trim().toLowerCase();
    }

    if (!dateKey) {
        const urlHash = raw.urlHash || raw.url_hash || raw.url;
        if (!urlHash) {
            return null;
        }
        dateKey = String(urlHash).trim().toLowerCase();
    }

    const parts = [titleKey, dateKey, venueKey].filter(Boolean);
    return parts.length ? parts.join('|') : null;
}

function dedupeEvents(events) {
    const map = new Map();
    const deduped = [];
    let merged = 0;
    let skipped = 0;

    for (const raw of events) {
        const day = getDayInfo(raw);
        const key = buildDedupeKey(raw);
        const baseTags = sanitizeTagList(raw.tags || []);
        const initialSources = [
            ...(Array.isArray(raw.sources) ? raw.sources : []),
            ...(raw.source ? [raw.source] : [])
        ].filter(Boolean);
        const baseSources = Array.from(new Set(initialSources));
        const linkCandidates = Array.isArray(raw.sourceLinks)
            ? [...raw.sourceLinks]
            : Array.isArray(raw.source_links)
                ? [...raw.source_links]
                : [];
        if (raw.source && raw.url) {
            linkCandidates.push({ source: raw.source, url: raw.url });
        }
        const sourceLinks = [];
        for (const entry of linkCandidates) {
            if (!entry || !entry.url) continue;
            if (!sourceLinks.some(item => item.url === entry.url)) {
                sourceLinks.push({ source: entry.source || raw.source, url: entry.url });
            }
        }

        const next = {
            ...raw,
            tags: baseTags,
            sources: baseSources,
            sourceLinks,
            dayIndex: day?.index ?? null
        };

        if (!key) {
            skipped += 1;
            deduped.push(next);
            continue;
        }

        if (!map.has(key)) {
            map.set(key, next);
            deduped.push(next);
            continue;
        }

        const existing = map.get(key);
        merged += 1;

        existing.tags = sanitizeTagList([...(existing.tags || []), ...(next.tags || [])]);

        const mergedSources = new Set([...(existing.sources || []), ...(next.sources || [])].filter(Boolean));
        existing.sources = Array.from(mergedSources);

        if (!existing.sourceLinks) existing.sourceLinks = [];
        for (const entry of next.sourceLinks || []) {
            if (!existing.sourceLinks.some(item => item.url === entry.url)) {
                existing.sourceLinks.push(entry);
            }
        }

        if (!existing.url && next.url) existing.url = next.url;
        if (existing.url_status == null && next.url_status != null) existing.url_status = next.url_status;
        if (existing.url_status && Number(existing.url_status) !== 200 && next.url_status && Number(next.url_status) === 200 && next.url) {
            existing.url = next.url;
            existing.url_status = next.url_status;
        }
        if (!existing.when && next.when) existing.when = next.when;
        if (!existing.where && next.where) existing.where = next.where;
        if (!existing.description && next.description) existing.description = next.description;
        if (!existing.summary && next.summary) existing.summary = next.summary;
        if (existing.dayIndex == null && next.dayIndex != null) existing.dayIndex = next.dayIndex;
        if (!existing.ticket_url && next.ticket_url) existing.ticket_url = next.ticket_url;
    }

    if (merged || skipped) {
        console.info(`Dedupe results → merged: ${merged}, kept: ${deduped.length}, skipped: ${skipped}`);
    }

    return deduped;
}

function applySmartTags(event, combinedText) {
    const tags = new Set(event.tags || []);
    for (const rule of SMART_TAG_RULES) {
        if (rule.pattern.test(combinedText)) {
            tags.add(rule.tag);
        }
    }
    event.tags = sanitizeTagList([...tags]);
}

function detectVibe(event, combinedText) {
    const tags = event.tags || [];
    let bestId = 'performance';
    let bestScore = 0;

    for (const profile of VIBE_PROFILES) {
        let score = 0;
        for (const keyword of profile.keywords) {
            if (combinedText.includes(keyword)) {
                score += keyword.length > 6 ? 2 : 1;
            }
        }

        for (const hint of profile.tagHints || []) {
            if (tags.includes(hint)) score += 2;
        }

        const sourceText = normalizeText(event.source || '');
        for (const hint of profile.sourceHints || []) {
            if (sourceText.includes(hint)) score += 1.5;
        }

        if (score > bestScore) {
            bestId = profile.id;
            bestScore = score;
        }
    }

    if (!bestScore) {
        const fallback = tags.includes('festival') ? 'experimental' : bestId;
        return fallback;
    }

    return bestId;
}

function enrichEvents(events) {
    const deduped = dedupeEvents(events);

    return deduped.map(event => {
        const combinedText = [
            event.title,
            event.description,
            event.summary,
            event.venue,
            event.where,
            (event.tags || []).join(' ')
        ].filter(Boolean).join(' ').toLowerCase();

        applySmartTags(event, combinedText);

        event.vibe = detectVibe(event, combinedText);
        event.vibeLabel = VIBE_LOOKUP[event.vibe]?.label || 'Performance';

        const dayInfo = getDayInfo(event);
        event.dayIndex = dayInfo?.index ?? null;
        event.dayName = dayInfo?.full ?? null;
        event.dayShort = dayInfo?.short ?? null;

        if (!event.sources || !event.sources.length) {
            event.sources = event.source ? [event.source] : [];
        }

        return event;
    });
}

function paint(list) {
    if (!eventsEl) return;
    eventsEl.innerHTML = '';

    if (!list.length) {
        const emptyState = document.createElement('p');
        emptyState.className = 'empty-state';
        emptyState.textContent = 'No events yet. Try another filter or check back later.';
        eventsEl.appendChild(emptyState);
        return;
    }

    const fragment = document.createDocumentFragment();

    list.forEach((event, idx) => {
        const article = document.createElement('article');
        article.className = 'card';
        article.dataset.index = String(idx);
        article.setAttribute('role', 'listitem');

        if (event.tags?.length) {
            const meta = document.createElement('div');
            meta.className = 'meta';
            event.tags.forEach(tag => {
                const badge = document.createElement('span');
                const classes = ['badge'];
                if (TAG_STYLE[tag]) classes.push(TAG_STYLE[tag]);
                badge.className = classes.join(' ');
                badge.textContent = tag;
                meta.appendChild(badge);
            });
            article.appendChild(meta);
        }

        const title = document.createElement('h3');
        title.textContent = event.title || 'Untitled event';
        article.appendChild(title);

        const detailParts = [];
        if (event.dayName) detailParts.push(event.dayName);
        if (event.when) detailParts.push(event.when);
        if (event.where) detailParts.push(event.where);

        if (detailParts.length) {
            const detailEl = document.createElement('p');
            detailEl.className = 'card__details';
            detailEl.textContent = detailParts.join(' • ');
            article.appendChild(detailEl);
        }

        const summary = event.summary || event.description;
        if (summary) {
            const summaryEl = document.createElement('p');
            summaryEl.className = 'card__summary';
            summaryEl.textContent = summary.length > 160 ? `${summary.slice(0, 157)}…` : summary;
            article.appendChild(summaryEl);
        }

        const sourceNames = event.sources && event.sources.length
            ? event.sources.join(' · ')
            : event.source;
        if (sourceNames) {
            const sourceEl = document.createElement('p');
            sourceEl.className = 'card__sources';
            sourceEl.textContent = `Source: ${sourceNames}`;
            article.appendChild(sourceEl);
        }

        if (event.url) {
            const link = document.createElement('a');
            link.href = event.url;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.textContent = 'View event';
            article.appendChild(link);
        }

        fragment.appendChild(article);
    });

    eventsEl.appendChild(fragment);
}

function setActive(value, scope) {
    const selector = scope ? `.filters [data-scope="${scope}"]` : '.filters [data-filter]';
    document.querySelectorAll(selector).forEach(btn => {
        const isActive = value !== null && value !== undefined && btn.dataset.filter === value;
        btn.classList.toggle('chip--active', isActive);
        btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });
}

function getDataset(key) {
    if (key === 'today') return datasets.today || [];
    if (key === 'tonight') return datasets.tonight || [];
    return datasets.all || [];
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
    eventsEl?.querySelectorAll('.card--highlight').forEach(el => el.classList.remove('card--highlight'));
}

function applyFilter(tag) {
    if (DATASET_FILTERS.has(tag)) {
        activeDatasetKey = tag;
        const data = getDataset(tag);
        currentList = data;
        currentFilter = null;
        paint(data);
        setActive(activeDatasetKey, 'dataset');
        setActive(null, 'tag');
        clearSpotlight();
        return;
    }

    const source = getDataset(activeDatasetKey);
    const data = source.filter(e => (e.tags || []).includes(tag));
    currentList = data;
    currentFilter = tag;
    paint(data);
    setActive(activeDatasetKey, 'dataset');
    setActive(tag, 'tag');
    clearSpotlight();
}

function showSpotlight(event) {
    if (!spotlightEl) return;

    spotlightEl.replaceChildren();

    const intro = document.createElement('strong');
    intro.textContent = 'Spotlight';
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

    const sourceNames = event.sources && event.sources.length
        ? event.sources.join(' · ')
        : event.source;
    if (sourceNames) {
        const meta = document.createElement('div');
        meta.className = 'spotlight__sources';
        meta.textContent = `Source: ${sourceNames}`;
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
    if (!eventsEl) return;
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

function renderFilters(events) {
    if (!filterBar) return;

    const available = new Set();
    events.forEach(event => (event.tags || []).forEach(tag => available.add(tag)));

    const ordered = [...BASE_TAG_ORDER];
    const extras = Array.from(available).filter(tag => !BASE_TAG_ORDER.includes(tag));
    extras.sort();
    ordered.push(...extras);

    const unique = ordered.filter((tag, index) => ordered.indexOf(tag) === index);

    const datasetButtons = DATASET_OPTIONS.map(option => {
        const classes = ['chip', 'chip--dataset'];
        if (option.key === activeDatasetKey) classes.push('chip--active');
        return `<button type="button" class="${classes.join(' ')}" data-scope="dataset" data-filter="${option.key}" aria-pressed="${option.key === activeDatasetKey}">${option.label}</button>`;
    }).join('');

    const tagButtons = unique.map(tag => {
        const label = labelForTag(tag);
        const classes = ['chip'];
        if (tag === currentFilter) classes.push('chip--active');
        return `<button type="button" class="${classes.join(' ')}" data-scope="tag" data-filter="${tag}" aria-pressed="${tag === currentFilter}">${label}</button>`;
    }).join('');

    const surpriseButton = '<button type="button" id="surprise" class="chip chip--accent">Inspire me</button>';

    filterBar.innerHTML = `
        <div class="filters__row filters__row--datasets">${datasetButtons}</div>
        <div class="filters__row filters__row--tags">${tagButtons}${surpriseButton}</div>
    `;
    setActive(activeDatasetKey, 'dataset');
    if (currentFilter) {
        setActive(currentFilter, 'tag');
    }
}

function heatColor(ratio, alpha = .2) {
    const clamped = Math.max(0, Math.min(1, ratio));
    const hue = 260 - clamped * 180; // from violet to orange
    const saturation = 80;
    const lightness = 65 - clamped * 15;
    return `hsla(${Math.round(hue)}, ${saturation}%, ${Math.round(lightness)}%, ${alpha})`;
}

function renderDensityMap(events) {
    if (!densityEl) return;

    const counts = new Array(7).fill(0);
    let datedEvents = 0;
    events.forEach(event => {
        if (typeof event.dayIndex === 'number') {
            counts[event.dayIndex] += 1;
            datedEvents += 1;
        }
    });

    if (!datedEvents) {
        densityEl.hidden = false;
        densityEl.innerHTML = '<p class="empty-state">No schedule data yet for this week.</p>';
        updatePulseColor(counts);
        return;
    }

    const max = Math.max(1, ...counts);
    const cards = WEEK.map(day => {
        const count = counts[day.index];
        const ratio = count / max;
        const strength = ratio ? (0.3 + ratio * 0.7) : 0.1;
        const color = heatColor(ratio, .28);
        return `<div class="density__cell" style="--density-strength:${strength.toFixed(2)};--density-color:${color}">
            <div class="density__day">${day.full}</div>
            <div class="density__count">${count}</div>
            <div class="density__bar"><span></span></div>
        </div>`;
    }).join('');

    densityEl.hidden = false;
    densityEl.innerHTML = `<div class="density__grid">${cards}</div>`;
    updatePulseColor(counts);
}

function updatePulseColor(counts) {
    const today = new Date();
    const todayIndex = today.getDay();
    const max = Math.max(1, ...counts);
    const todayRatio = (counts[todayIndex] || 0) / max;
    const lightPulse = heatColor(todayRatio, .14);
    const darkPulse = heatColor(todayRatio, .32);
    document.documentElement.style.setProperty('--pulse-color', lightPulse);
    document.documentElement.style.setProperty('--pulse-color-dark', darkPulse);
}

function renderClusters(events) {
    if (!clusterDeckEl) return;

    const groups = new Map();
    events.forEach(event => {
        const key = event.vibe || 'performance';
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(event);
    });

    const cards = VIBE_PROFILES
        .filter(profile => groups.has(profile.id))
        .map(profile => {
            const list = sortByEventTime(groups.get(profile.id));
            const sample = list[0];
            const count = list.length;
            const suffix = count === 1 ? 'event' : 'events';
            const sampleWhen = [sample?.when, sample?.where].filter(Boolean).join(' • ');
            const sampleLine = sample ? `${sample.title}${sampleWhen ? ` — ${sampleWhen}` : ''}` : '';
            return `<article class="cluster-card" data-vibe="${profile.id}">
                <span class="cluster-card__title">${profile.label}</span>
                <span class="cluster-card__count">${count} ${suffix}</span>
                <span class="cluster-card__sample">${sampleLine}</span>
            </article>`;
        }).join('');

    clusterDeckEl.innerHTML = cards;
    clusterDeckEl.hidden = !cards.length;
}

async function fetchJson(url) {
    const cacheBust = `v=${Date.now()}`;
    const separator = url.includes('?') ? '&' : '?';
    const response = await fetch(`${url}${separator}${cacheBust}`);
    if (!response.ok) throw new Error(response.statusText);
    return response.json();
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
        {
            title: 'Quiz at Det Akademiske Kvarter',
            when: 'Thu 20:00',
            where: 'Kvarteret',
            tags: ['quiz'],
            url: 'https://kvarteret.no/'
        },
        {
            title: 'Midnight Rave',
            when: 'Fri 23:59',
            where: 'USF Verftet',
            tags: ['rave'],
            url: 'https://ra.co/'
        },
        {
            title: 'Paint n’ Sip',
            when: 'Sat 18:00',
            where: 'Kulturhuset',
            tags: ['girls', 'date'],
            url: 'https://ticketco.events/'
        },
        {
            title: 'Cinema: Sci-Fi Classics',
            when: 'Tonight 21:15',
            where: 'Bergen Kino',
            tags: ['cinema', 'date'],
            url: 'https://bergenkino.no/'
        }
    ];
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

function renderSourceRollup(events) {
    if (!sourceRollupEl) return;
    const sources = new Set();
    events.forEach(event => {
        (event.sources || [event.source]).forEach(source => {
            if (source) sources.add(source);
        });
    });
    const sorted = [...sources].sort((a, b) => a.localeCompare(b));
    sourceRollupEl.innerHTML = sorted.length
        ? sorted.map(source => `<li>${source}</li>`).join('')
        : '<li>Sources will appear once events are loaded.</li>';
}

function handleSurprise() {
    const list = currentList.length ? currentList : getDataset(activeDatasetKey);
    if (!list.length) return;
    const idx = Math.floor(Math.random() * list.length);
    const event = list[idx];
    showSpotlight(event);
    highlightCard(idx);
}

function handleFilterClick(e) {
    const button = e.target.closest('button');
    if (!button) return;
    if (button.dataset.filter) {
        applyFilter(button.dataset.filter);
        return;
    }
    if (button.id === 'surprise') {
        handleSurprise();
    }
}

async function boot() {
    const [allRaw, todayRaw, tonightRaw, heatmap] = await Promise.all([
        loadEvents(),
        loadSupplemental('./data/today.json'),
        loadSupplemental('./data/tonight.json'),
        loadSupplemental('./data/heatmap.json')
    ]);

    datasets.all = enrichEvents(Array.isArray(allRaw) ? allRaw : []);
    datasets.today = enrichEvents(Array.isArray(todayRaw) ? todayRaw : []);
    datasets.tonight = enrichEvents(Array.isArray(tonightRaw) ? tonightRaw : []);

    currentList = datasets.all;

    renderFilters(datasets.all);
    renderClusters(datasets.all);
    renderDensityMap(datasets.all);
    renderSourceRollup(datasets.all);

    if (heatmap && typeof heatmap === 'object' && !Array.isArray(heatmap)) {
        renderHeatmap(heatmap);
    } else {
        renderHeatmap(null);
    }

    applyFilter('all');
}

filterContainers.forEach(container => {
    container.addEventListener('click', handleFilterClick);
});

if (filterBar) {
    filterBar.classList.add('filters--ready');
}

$('#year')?.textContent = new Date().getFullYear();

document.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
        clearSpotlight();
    }
});

boot();
