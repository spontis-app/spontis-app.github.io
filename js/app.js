import {
    getActiveDatasetKey,
    setActiveDatasetKey,
    getCurrentFilter,
    setCurrentFilter,
    getCurrentList,
    setCurrentList,
    getCurrentVibe,
    setCurrentVibe,
    resetState,
    getCurrentSmartFilter,
    setCurrentSmartFilter
} from './modules/state.js';
import {
    setDatasets,
    getDataset,
    collectTags,
    hasVibe
} from './modules/datasets.js';
import {
    createBalancedFeed,
    formatRelativeStart,
    selectUpcomingEvents
} from './feed.js';
import { defaultDatasetKey } from './date-filters.js';

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
const detailLayer = $('#detail-layer');
const detailDialog = $('#detail-dialog');
const detailCloseBtn = $('#detail-close');
const detailTagsEl = $('#detail-tags');
const detailTitleEl = $('#detail-title');
const detailHeadlineEl = $('#detail-headline');
const detailDescriptionEl = $('#detail-description');
const detailOrganiserEl = $('#detail-organiser');
const detailSourcesEl = $('#detail-sources');
const detailOpenLink = $('#detail-open');
const detailBackdrop = detailLayer ? detailLayer.querySelector('.detail-layer__backdrop') : null;
const topicDrawer = $('#topic-drawer');
const topicBackdrop = topicDrawer ? topicDrawer.querySelector('.topic-drawer__backdrop') : null;
const topicPanel = topicDrawer ? topicDrawer.querySelector('.topic-drawer__panel') : null;
const topicCloseBtn = $('#topic-drawer-close');
const topicApplyBtn = $('#topic-apply');
const topicClearBtn = $('#topic-clear');
const topicBody = $('#topic-drawer-body');
const topicTriggers = Array.from(document.querySelectorAll('[data-topics-trigger]'));
const datasetButtons = Array.from(document.querySelectorAll('.dataset-chip'));
const updatedChip = $('#updated-chip');
const sourceCountChip = $('#source-count-chip');
const eventCountChip = $('#event-count-chip');
const metaAlert = $('#meta-alert');
const metaAlertSummary = $('#meta-alert-summary');
const metaAlertList = $('#meta-alert-list');
const smartFiltersContainer = document.querySelector('.smart-filters');
const nowDeckEl = $('#now-deck');
const nowDeckBody = $('#now-deck-body');
let lastMeta = {};
let topicButtons = new Map();
let smartFilterButtons = new Map();
let pendingTag = null;
let lastTopicTrigger = null;


function openTopicDrawer(trigger) {
    if (!topicDrawer) return;
    if (trigger) {
        lastTopicTrigger = trigger;
    }
    pendingTag = getCurrentFilter();
    updatePendingSelection();
    topicDrawer.hidden = false;
    topicTriggers.forEach(btn => btn.setAttribute('aria-expanded', 'true'));
    document.body.style.overflow = 'hidden';
    if (topicPanel) {
        if (!topicPanel.hasAttribute('tabindex')) {
            topicPanel.setAttribute('tabindex', '-1');
        }
        topicPanel.focus({ preventScroll: true });
    }
}

function closeTopicDrawer() {
    if (!topicDrawer || topicDrawer.hidden) return;
    topicDrawer.hidden = true;
    topicTriggers.forEach(btn => btn.setAttribute('aria-expanded', 'false'));
    document.body.style.overflow = '';
    pendingTag = null;
    updatePendingSelection();
    updateTopicButtons(getCurrentFilter());
    const focusTarget = lastTopicTrigger || topicTriggers[0];
    focusTarget?.focus({ preventScroll: true });
    lastTopicTrigger = null;
}

function applyPendingTopic() {
    if (pendingTag) {
        applyFilter(pendingTag);
    } else {
        applyFilter(getActiveDatasetKey() || 'all');
    }
    pendingTag = getCurrentFilter();
    updatePendingSelection();
    closeTopicDrawer();
}

function clearPendingTopic() {
    pendingTag = null;
    updatePendingSelection();
    applyFilter(getActiveDatasetKey() || 'all');
    closeTopicDrawer();
}

function handleDatasetButtonClick(event) {
    const button = event.currentTarget;
    const key = button?.dataset?.dataset;
    const activeKey = getActiveDatasetKey();
    if (!key || !DATASET_FILTERS.has(key) || key === activeKey) return;
    pendingTag = null;
    applyFilter(key);
    if (!topicDrawer?.hidden) {
        closeTopicDrawer();
    }
}

function updateDatasetButtons() {
    datasetButtons.forEach(button => {
        const isActive = button.dataset.dataset === getActiveDatasetKey();
        button.setAttribute('aria-pressed', isActive ? 'true' : 'false');
        button.classList.toggle('dataset-chip--active', Boolean(isActive));
    });
}

function formatUpdatedLabel(isoString) {
    if (!isoString) return null;
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) return null;
    const formatter = new Intl.DateTimeFormat('nb-NO', {
        weekday: 'short',
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
    });
    return formatter.format(date);
}

function updateHeroMeta(meta, events) {
    const list = Array.isArray(events) ? events : [];
    if (eventCountChip) {
        const count = list.length;
        eventCountChip.textContent = count > 0 ? `Eventer i feeden: ${count}` : 'Eventer i feeden: –';
    }

    const uniqueSources = new Set();
    list.forEach(event => {
        const source = event?.source;
        if (source) uniqueSources.add(source);
    });

    if (sourceCountChip) {
        const datasetKey = getActiveDatasetKey();
        const stats = Array.isArray(meta?.source_stats) ? meta.source_stats : [];
        const metaCount = typeof meta?.source_count === 'number' ? meta.source_count : stats.length || null;
        const activeCount = stats.length
            ? stats.filter(entry => (entry?.events ?? 0) > 0).length
            : uniqueSources.size;
        const failing = stats.filter(entry => {
            const status = typeof entry?.status === 'string' ? entry.status.toLowerCase() : '';
            return status === 'error' || status === 'fallback' || status === 'offline';
        });

        const fallbackCount = datasetKey === 'all'
            ? (metaCount ?? uniqueSources.size)
            : uniqueSources.size;
        const displayCount = activeCount || fallbackCount;

        let label = displayCount > 0 ? `Kilder: ${displayCount}` : 'Kilder: –';
        if (metaCount && metaCount > displayCount) {
            label = `Kilder: ${displayCount}/${metaCount}`;
        }
        if (failing.length) {
            label += ' ⚠';
        }

        sourceCountChip.textContent = label;

        const tooltipLines = stats.length
            ? stats.map(entry => {
                const status = String(entry?.status || 'ok').toLowerCase();
                const events = entry?.events ?? 0;
                if (status === 'error') return `${entry?.name || 'Ukjent'} — feil (${events})`;
                if (status === 'fallback') return `${entry?.name || 'Fallback'} — sample-data`;
                if (status === 'offline') return `${entry?.name || 'Offline'} — offline`;
                if (events === 0) return `${entry?.name || 'Ukjent'} — ingen events`;
                return `${entry?.name || 'Ukjent'} — ok (${events})`;
            })
            : [...uniqueSources].map(name => `${name} — aktiv`);
        sourceCountChip.title = tooltipLines.join('\n');
        sourceCountChip.classList.toggle('hero__meta-chip--alert', failing.length > 0);
    }

    if (updatedChip) {
        const formatted = formatUpdatedLabel(meta?.last_updated);
        updatedChip.textContent = formatted ? `Oppdatert: ${formatted}` : 'Oppdatert nylig';
    }
}

function updateTopicsTriggerLabel(selectedTag = getCurrentFilter()) {
    topicTriggers.forEach(trigger => {
        const labelEl = trigger.querySelector('.drawer-trigger__label');
        if (labelEl) {
            labelEl.textContent = selectedTag ? labelForTag(selectedTag) : 'Topics';
        }
        trigger.setAttribute('data-selected-tag', selectedTag || '');
    });
}

function updateTopicButtons(selectedTag) {
    topicButtons.forEach((button, tag) => {
        const isActive = Boolean(selectedTag && tag === selectedTag);
        button.classList.toggle('topic-chip--active', isActive);
        button.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });
    updateTopicsTriggerLabel(selectedTag || null);
}

function updateVibeCards() {
    if (!clusterDeckEl) return;
    const activeVibe = getCurrentVibe();
    const cards = clusterDeckEl.querySelectorAll('.cluster-card');
    cards.forEach(card => {
        const vibeId = card.dataset.vibe;
        const isActive = Boolean(activeVibe && vibeId === activeVibe);
        card.classList.toggle('cluster-card--active', isActive);
        card.setAttribute('aria-pressed', isActive ? 'true' : 'false');
        if (!card.hasAttribute('tabindex')) {
            card.tabIndex = 0;
        }
    });
}

function showEvents(list, { updateMeta = false } = {}) {
    const base = Array.isArray(list) ? list : [];
    const { feed, upcoming } = createBalancedFeed(base, { now: new Date() });
    setCurrentList(feed);
    paint(feed);
   renderNowDeck(base, upcoming);
   if (updateMeta) {
       updateHeroMeta(lastMeta, base);
        renderMetaAlert(lastMeta);
   }
}

function renderNowDeck(events, upcomingOverride) {
    if (!nowDeckEl || !nowDeckBody) return;
    const upcoming = Array.isArray(upcomingOverride) ? upcomingOverride : selectUpcomingEvents(events, { now: new Date() });
    nowDeckBody.innerHTML = '';
    if (!upcoming.length) {
        nowDeckEl.hidden = true;
        return;
    }

    const fragment = document.createDocumentFragment();
    upcoming.forEach(event => {
        const timestamp = parseStartsAtValue(event.starts_at);
        const relative = formatRelativeStart(timestamp, Date.now());
        const schedule = computeScheduleLabel(event);

        const card = document.createElement('article');
        card.className = 'now-card';
        card.setAttribute('role', 'listitem');

        const timeEl = document.createElement('p');
        timeEl.className = 'now-card__time';
        timeEl.textContent = relative || schedule || 'I kveld';
        card.appendChild(timeEl);

        const titleEl = document.createElement('h3');
        titleEl.className = 'now-card__title';
        titleEl.textContent = event.title || 'Untitled event';
        card.appendChild(titleEl);

        const venue = deriveLocation(event);
        if (venue) {
            const venueEl = document.createElement('p');
            venueEl.className = 'now-card__venue';
            venueEl.textContent = venue;
            card.appendChild(venueEl);
        }

        const footer = document.createElement('div');
        footer.className = 'now-card__actions';

        const detailBtn = document.createElement('button');
        detailBtn.type = 'button';
        detailBtn.className = 'btn-secondary btn-secondary--compact';
        detailBtn.textContent = 'Detaljer';
        detailBtn.addEventListener('click', () => openDetail(event));
        footer.appendChild(detailBtn);

        const link = document.createElement('a');
        link.className = 'btn-primary btn-primary--compact';
        link.href = resolveEventUrl(event) || '#';
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = 'Billetter';
        link.setAttribute('aria-label', `Åpne ${event.title || 'event'} hos arrangør`);
        if (!event.url && !event.ticket_url) {
            link.classList.add('is-disabled');
        }
        footer.appendChild(link);

        card.appendChild(footer);
        fragment.appendChild(card);
    });

    nowDeckBody.appendChild(fragment);
    nowDeckEl.hidden = false;
}

function updatePendingSelection() {
    topicButtons.forEach((button, tag) => {
        const isSelected = Boolean(pendingTag && tag === pendingTag);
        button.classList.toggle('topic-chip--selected', isSelected);
    });
    if (topicClearBtn) {
        const hasSelection = Boolean(pendingTag);
        topicClearBtn.disabled = !hasSelection;
        topicClearBtn.setAttribute('aria-disabled', hasSelection ? 'false' : 'true');
    }
}

function toggleTopicSelection(tag) {
    pendingTag = pendingTag === tag ? null : tag;
    updatePendingSelection();
}

const detailElements = {
    layer: detailLayer,
    dialog: detailDialog,
    close: detailCloseBtn,
    tags: detailTagsEl,
    title: detailTitleEl,
    headline: detailHeadlineEl,
    description: detailDescriptionEl,
    organiser: detailOrganiserEl,
    sources: detailSourcesEl,
    link: detailOpenLink,
};

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

const TAG_ICON = {
    culture: './assets/icons/tag-culture.svg',
    live: './assets/icons/tag-live.svg',
    jazz: './assets/icons/tag-jazz.svg',
    cinema: './assets/icons/tag-cinema.svg',
    dj: './assets/icons/tag-dj.svg',
    quiz: './assets/icons/tag-quiz.svg',
};

const TAG_LABELS = {
    all: 'All',
    bar: 'Bar night',
    culture: 'Culture',
    date: 'Date night',
    dj: 'DJ set',
    festival: 'Festival',
    girls: "Girls' night",
    jazz: 'Jazz',
    lecture: 'Talks',
    live: 'Live music',
    opening: 'Opening',
    quiz: 'Quiz night',
    cinema: 'Cinema',
    rave: 'Rave'
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

const SMART_FILTERS = [
    {
        id: 'free',
        label: 'Gratis',
        predicate: event => {
            if (event?.free === true) return true;
            const price = typeof event?.price === 'string' ? event.price.trim().toLowerCase() : '';
            if (price === 'gratis' || price === 'free') return true;
            const tags = event?.tags || [];
            return tags.includes('free');
        }
    },
    {
        id: 'family',
        label: 'Familie',
        predicate: event => {
            const tags = event?.tags || [];
            return tags.some(tag => ['family', 'kids', 'barn', 'ungdom'].includes(tag));
        }
    },
    {
        id: 'music',
        label: 'Live & DJ',
        predicate: event => {
            const tags = event?.tags || [];
            return tags.some(tag => ['live', 'dj', 'jazz', 'festival'].includes(tag));
        }
    },
    {
        id: 'late',
        label: 'Sen kveld',
        predicate: event => {
            const value = parseStartsAtValue(event?.starts_at);
            if (Number.isNaN(value)) return false;
            const date = new Date(value);
            const hours = date.getHours();
            return hours >= 21 || hours < 4;
        }
    }
];

const SMART_FILTER_MAP = new Map(SMART_FILTERS.map(filter => [filter.id, filter]));

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
        label: 'Stage & Screen',
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

const DATE_FORMAT_WITH_TIME = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/Oslo',
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
});

const DATE_FORMAT_DAY_ONLY = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/Oslo',
    weekday: 'short',
    day: 'numeric',
    month: 'short'
});

function updateUrlFilters() {
    const activeDatasetKey = getActiveDatasetKey();
    const currentFilter = getCurrentFilter();
    const currentVibe = getCurrentVibe();
    const currentSmart = getCurrentSmartFilter();
    const params = new URLSearchParams(window.location.search);
    if (activeDatasetKey && activeDatasetKey !== 'all') {
        params.set('dataset', activeDatasetKey);
    } else {
        params.delete('dataset');
    }

    if (currentFilter) {
        params.set('tag', currentFilter);
    } else {
        params.delete('tag');
    }

    if (currentVibe) {
        params.set('vibe', currentVibe);
    } else {
        params.delete('vibe');
    }

    if (currentSmart) {
        params.set('smart', currentSmart);
    } else {
        params.delete('smart');
    }

    const query = params.toString();
    const newUrl = `${window.location.pathname}${query ? `?${query}` : ''}${window.location.hash}`;
    window.history.replaceState({}, '', newUrl);
}

function hasClockComponent(value) {
    return typeof value === 'string' && !/T0{2}:0{2}(?::0{2})?(?:\.0+)?(?:Z|[+-]0{2}:?0{2})?$/.test(value);
}

function computeScheduleLabel(event) {
    if (event.when && String(event.when).trim()) {
        return String(event.when).trim();
    }
    if (!event.starts_at) {
        return '';
    }
    const date = new Date(event.starts_at);
    if (Number.isNaN(date.getTime())) {
        return '';
    }
    const formatter = hasClockComponent(event.starts_at) ? DATE_FORMAT_WITH_TIME : DATE_FORMAT_DAY_ONLY;
    return formatter.format(date).replace(',', '');
}

function deriveLocation(event) {
    return event.where || event.venue || event.city || '';
}

function buildEventHeadline(event) {
    const parts = [];
    const schedule = computeScheduleLabel(event);
    if (schedule) parts.push(schedule);
    const location = deriveLocation(event);
    if (location) parts.push(location);
    return parts.join(' • ');
}

function renderDetailSources(event) {
    detailSourcesEl.innerHTML = '';
    const links = event.sourceLinks || [];
    if (!links.length) {
        detailSourcesEl.hidden = true;
        return;
    }
    const fragment = document.createDocumentFragment();
    links.forEach(entry => {
        if (!entry?.url) return;
        const li = document.createElement('li');
        const anchor = document.createElement('a');
        anchor.href = entry.url;
        anchor.target = '_blank';
        anchor.rel = 'noopener noreferrer';
        anchor.textContent = entry.source || entry.url.replace(/^https?:\/\//i, '');
        li.appendChild(anchor);
        fragment.appendChild(li);
    });
    detailSourcesEl.appendChild(fragment);
    detailSourcesEl.hidden = false;
}

let lastFocusedElement = null;

function openDetail(event) {
    if (!detailLayer || !detailDialog) return;
    lastFocusedElement = document.activeElement;

    detailTagsEl.textContent = (event.tags || []).map(labelForTag).join(' • ');
    detailTitleEl.textContent = event.title || 'Untitled event';
    const headline = event.displayHeadline || buildEventHeadline(event);
    detailHeadlineEl.textContent = headline;
    detailHeadlineEl.hidden = !headline;

    const description = event.description || event.summary || '';
    detailDescriptionEl.textContent = description;
    detailDescriptionEl.hidden = !description;

    const organiser = event.sources?.length ? event.sources.join(' · ') : event.source;
    detailOrganiserEl.textContent = organiser ? `Organiser: ${organiser}` : '';
    detailOrganiserEl.hidden = !organiser;

    renderDetailSources(event);
    const resolvedUrl = resolveEventUrl(event);
    if (resolvedUrl) {
        detailOpenLink.href = resolvedUrl;
        detailOpenLink.classList.remove('is-disabled');
    } else {
        detailOpenLink.href = '#';
        detailOpenLink.classList.add('is-disabled');
    }

    detailLayer.hidden = false;
    detailLayer.classList.add('detail-layer--open');
    document.body.style.overflow = 'hidden';
    detailDialog.focus();
}

function closeDetail() {
    if (!detailLayer || detailLayer.hidden) return;
    detailLayer.hidden = true;
    detailLayer.classList.remove('detail-layer--open');
    document.body.style.overflow = '';
    if (lastFocusedElement?.focus) {
        lastFocusedElement.focus();
    }
}

function parseStartsAtValue(value) {
    if (!value) return Number.NaN;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? Number.NaN : date.getTime();
}

function sortEventsChronologically(list) {
    return [...list].sort((a, b) => {
        const aTime = parseStartsAtValue(a.starts_at);
        const bTime = parseStartsAtValue(b.starts_at);
        const aHasTime = !Number.isNaN(aTime);
        const bHasTime = !Number.isNaN(bTime);
        if (aHasTime && bHasTime) return aTime - bTime;
        if (aHasTime) return -1;
        if (bHasTime) return 1;
        const aWhen = (a.when || '').toLowerCase();
        const bWhen = (b.when || '').toLowerCase();
        if (aWhen && bWhen && aWhen !== bWhen) return aWhen.localeCompare(bWhen);
        return (a.title || '').localeCompare(b.title || '');
    });
}

const WEEK = [
    { index: 1, short: 'Mon', full: 'Monday' },
    { index: 2, short: 'Tue', full: 'Tuesday' },
    { index: 3, short: 'Wed', full: 'Wednesday' },
    { index: 4, short: 'Thu', full: 'Thursday' },
    { index: 5, short: 'Fri', full: 'Friday' },
    { index: 6, short: 'Sat', full: 'Saturday' },
    { index: 0, short: 'Sun', full: 'Sunday' }
];

const FALLBACK_HOST_RESOLVERS = {
    'bergenkjott.org': createBergenKjottLink,
    'bergenkjott.no': createBergenKjottLink
};

const FALLBACK_SOURCE_RESOLVERS = {
    'Bergen Kjøtt': createBergenKjottLink
};

let highlightTimer;

const UPCOMING_WINDOW_DAYS = 14;

function safeParseUrl(value) {
    if (!value) return null;
    try {
        return new URL(value);
    } catch (error) {
        return null; // ignore malformed URLs
    }
}

function slugifyTitle(text = '') {
    return text
        .toString()
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/&/g, ' og ')
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/-{2,}/g, '-')
        .replace(/^-+|-+$/g, '');
}

function uniqueByTitle(events) {
    const seen = new Map();
    events.forEach(event => {
        const key = (event.title || '').trim().toLowerCase();
        if (!key) return;
        if (!seen.has(key)) {
            seen.set(key, event);
        } else {
            const existing = seen.get(key);
            const currentTime = parseStartsAtValue(event.starts_at);
            const existingTime = parseStartsAtValue(existing?.starts_at);
            if (!Number.isNaN(currentTime) && (Number.isNaN(existingTime) || currentTime < existingTime)) {
                seen.set(key, event);
            }
        }
    });
    return Array.from(seen.values());
}

function createBergenKjottLink(event) {
    const slug = slugifyTitle(event?.title || '');
    if (slug) {
        return `https://www.bergenkjott.org/events/${slug}`;
    }
    return 'https://www.bergenkjott.org/program';
}

function resolveEventUrl(event) {
    if (!event) return null;
    const rawUrl = typeof event.url === 'string' ? event.url.trim() : '';
    const parsed = safeParseUrl(rawUrl);
    const searchTerms = [event.title, event.venue, event.source].filter(Boolean).join(' ');

    if (parsed && parsed.pathname && parsed.pathname !== '/' && parsed.pathname !== '') {
        return rawUrl;
    }

    const hostKey = parsed?.hostname?.replace(/^www\./i, '');
    if (hostKey && FALLBACK_HOST_RESOLVERS[hostKey]) {
        return FALLBACK_HOST_RESOLVERS[hostKey](event, parsed);
    }

    if (event.source && FALLBACK_SOURCE_RESOLVERS[event.source]) {
        return FALLBACK_SOURCE_RESOLVERS[event.source](event, parsed);
    }

    if (parsed && (!parsed.pathname || parsed.pathname === '/') && !parsed.search && !parsed.hash) {
        if (searchTerms) {
            return `https://www.google.com/search?q=${encodeURIComponent(searchTerms)}`;
        }
    }

    if (rawUrl) return rawUrl;

    if (searchTerms) {
        return `https://www.google.com/search?q=${encodeURIComponent(searchTerms)}`;
    }

    return null;
}

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

function filterUpcomingEvents(events, daysAhead = UPCOMING_WINDOW_DAYS) {
    const start = new Date();
    start.setHours(0, 0, 0, 0);
    const startMs = start.getTime();
    const endMs = startMs + (daysAhead + 1) * 24 * 60 * 60 * 1000;
    const todayIndex = start.getDay();

    return events.filter(event => {
        if (event?.starts_at) {
            const parsed = new Date(event.starts_at);
            if (!Number.isNaN(parsed.getTime())) {
                const time = parsed.getTime();
                if (time < startMs || time >= endMs) {
                    return false;
                }
                return true;
            }
        }

        if (typeof event?.dayIndex === 'number') {
            let delta = event.dayIndex - todayIndex;
            if (delta < 0) delta += 7;
            return delta <= daysAhead;
        }

        if (event?.when) {
            const normalized = event.when.toLowerCase();
            if (/\b(today|tonight)\b/.test(normalized)) return true;
            if (/\btomorrow\b/.test(normalized) && daysAhead >= 1) return true;
        }

        return true;
    });
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

    const upcoming = filterUpcomingEvents(deduped);

    const active = upcoming.filter(event => (event.source || '').trim().toLowerCase() !== 'sample');

    const enriched = active.map(event => {
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

        const scheduleLabel = computeScheduleLabel(event);
        if (scheduleLabel && !event.when) {
            event.when = scheduleLabel;
        }

        const location = deriveLocation(event);
        if (location && !event.where) {
            event.where = location;
        }

        event.displayHeadline = buildEventHeadline(event);

        if (!event.sources || !event.sources.length) {
            event.sources = event.source ? [event.source] : [];
        }

        return event;
    });

    return sortEventsChronologically(enriched);
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

        const meta = document.createElement('div');
        meta.className = 'meta';

        (event.tags || []).forEach(tag => {
            const badge = document.createElement('span');
            const classes = ['badge'];
            if (TAG_STYLE[tag]) classes.push(TAG_STYLE[tag]);
            badge.className = classes.join(' ');
            const iconPath = TAG_ICON[tag];
            if (iconPath) {
                const icon = document.createElement('img');
                icon.src = iconPath;
                icon.alt = '';
                icon.className = 'badge__icon';
                icon.setAttribute('aria-hidden', 'true');
                badge.appendChild(icon);
            }
            badge.appendChild(document.createTextNode(labelForTag(tag)));
            meta.appendChild(badge);
        });

        const organiserLabel = event.sources?.length ? event.sources[0] : event.source;
        if (organiserLabel) {
            const sourceBadge = document.createElement('span');
            sourceBadge.className = 'badge badge--source';
            sourceBadge.textContent = organiserLabel;
            meta.appendChild(sourceBadge);
        }

        if (meta.children.length) {
            article.appendChild(meta);
        }

        const title = document.createElement('h3');
        title.textContent = event.title || 'Untitled event';
        article.appendChild(title);

        const headline = event.displayHeadline || buildEventHeadline(event);
        if (headline) {
            const detailEl = document.createElement('p');
            detailEl.className = 'card__details';
            detailEl.textContent = headline;
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
            sourceEl.textContent = `Organiser: ${sourceNames}`;
            article.appendChild(sourceEl);
        }

        const actionRow = document.createElement('div');
        actionRow.className = 'card__actions';

        const detailButton = document.createElement('button');
        detailButton.type = 'button';
        detailButton.className = 'btn-secondary';
        detailButton.textContent = 'Details';
        detailButton.addEventListener('click', (ev) => {
            ev.preventDefault();
            ev.stopPropagation();
            openDetail(event);
        });
        actionRow.appendChild(detailButton);

        const resolvedUrl = resolveEventUrl(event);
        if (resolvedUrl) {
            const link = document.createElement('a');
            link.href = resolvedUrl;
            link.target = '_blank';
            link.rel = 'noopener noreferrer external';
            link.className = 'btn-primary';
            link.textContent = 'Open event';
            if (event.title) {
                link.setAttribute('aria-label', `Open event: ${event.title}`);
            }
            actionRow.appendChild(link);
        }

        article.appendChild(actionRow);

        fragment.appendChild(article);
    });

    eventsEl.appendChild(fragment);
}

function setActive(value, scope) {
    if (scope === 'dataset') {
        updateDatasetButtons();
        return;
    }
    if (scope === 'tag') {
        updateTopicButtons(value);
        return;
    }
}

function renderSmartFilters(events) {
    if (!smartFiltersContainer) return;
    smartFilterButtons = new Map();
    smartFiltersContainer.replaceChildren();
    const fragment = document.createDocumentFragment();
    let availableCount = 0;

    SMART_FILTERS.forEach(filter => {
        const count = events.filter(filter.predicate).length;
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'smart-filter-chip';
        button.dataset.smart = filter.id;
        button.textContent = count > 0 ? `${filter.label} (${count})` : filter.label;
        button.setAttribute('aria-pressed', 'false');
        button.disabled = count === 0;
        button.setAttribute('aria-disabled', count === 0 ? 'true' : 'false');
        fragment.appendChild(button);
        smartFilterButtons.set(filter.id, button);
        if (count > 0) availableCount += 1;
    });

    smartFiltersContainer.appendChild(fragment);
    smartFiltersContainer.hidden = availableCount === 0;
    updateSmartFilterButtons(getCurrentSmartFilter());
}

function updateSmartFilterButtons(selectedId = getCurrentSmartFilter()) {
    smartFilterButtons.forEach((button, id) => {
        const isActive = Boolean(selectedId && id === selectedId);
        button.setAttribute('aria-pressed', isActive ? 'true' : 'false');
        button.classList.toggle('smart-filter-chip--active', isActive);
    });
}

function applySmartFilter(filterId) {
    const definition = SMART_FILTER_MAP.get(filterId);
    if (!definition) return;
    const activeDatasetKey = getActiveDatasetKey();
    const source = getDataset(activeDatasetKey);
    const data = source.filter(event => {
        try {
            return definition.predicate(event);
        } catch (error) {
            console.warn('Smart filter predicate failed', error);
            return false;
        }
    });
    setCurrentSmartFilter(filterId);
    setCurrentFilter(null);
    setCurrentVibe(null);
    pendingTag = null;
    showEvents(data, 2);
    setActive(activeDatasetKey, 'dataset');
    setActive(null, 'tag');
    updateSmartFilterButtons(filterId);
    updateVibeCards();
    updatePendingSelection();
    renderNowDeck(data);
    updateHeroMeta(lastMeta, data);
    clearSpotlight();
    updateUrlFilters();
    if (eventsEl) {
        eventsEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
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
        setActiveDatasetKey(tag);
        const data = getDataset(tag);
        setCurrentFilter(null);
        setCurrentVibe(null);
        setCurrentSmartFilter(null);
        pendingTag = null;
        renderSmartFilters(data);
        renderClusters(data);
        renderDensityMap(data);
        renderSourceRollup(data);
        showEvents(data, { updateMeta: true });
        setActive(tag, 'dataset');
        setActive(null, 'tag');
        updatePendingSelection();
        updateUrlFilters();
        clearSpotlight();
        return;
    }

    const activeDatasetKey = getActiveDatasetKey();
    const source = getDataset(activeDatasetKey);
    const data = source.filter(e => (e.tags || []).includes(tag));
    setCurrentFilter(tag);
    setCurrentVibe(null);
    setCurrentSmartFilter(null);
    pendingTag = null;
    showEvents(data, { updateMeta: true });
    setActive(activeDatasetKey, 'dataset');
    setActive(tag, 'tag');
    updateSmartFilterButtons(null);
    updateVibeCards();
    updatePendingSelection();
    clearSpotlight();
    updateUrlFilters();
}

function applyVibeFilter(vibeId) {
    if (!vibeId) return;
    const activeDatasetKey = getActiveDatasetKey();
    const source = getDataset(activeDatasetKey);
    const data = source.filter(event => (event.vibe || 'performance') === vibeId);
    setCurrentVibe(vibeId);
    setCurrentFilter(null);
    setCurrentSmartFilter(null);
    pendingTag = null;
    showEvents(data, { updateMeta: true });
    setActive(activeDatasetKey, 'dataset');
    setActive(null, 'tag');
    updateVibeCards();
    updatePendingSelection();
    updateSmartFilterButtons(null);
    clearSpotlight();
    updateUrlFilters();
    if (eventsEl) {
        eventsEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

function showSpotlight(event) {
    if (!spotlightEl) return;

    spotlightEl.replaceChildren();

    const intro = document.createElement('strong');
    intro.textContent = 'Curated pick';
    spotlightEl.appendChild(intro);

    const title = document.createElement('div');
    title.className = 'spotlight__title';
    title.textContent = event.title || 'Untitled event';
    spotlightEl.appendChild(title);

    const headline = event.displayHeadline || buildEventHeadline(event);
    if (headline) {
        const meta = document.createElement('div');
        meta.className = 'spotlight__meta';
        meta.textContent = headline;
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
    if (!topicBody) return;

    const activeFilter = getCurrentFilter();
    const available = new Set();
    events.forEach(event => (event.tags || []).forEach(tag => available.add(tag)));

    const ordered = [...BASE_TAG_ORDER];
    const extras = Array.from(available).filter(tag => !BASE_TAG_ORDER.includes(tag));
    extras.sort();
    ordered.push(...extras);

    const unique = ordered.filter((tag, index) => ordered.indexOf(tag) === index);

    topicButtons = new Map();
    topicBody.innerHTML = '';
    const fragment = document.createDocumentFragment();

    unique.forEach(tag => {
        const label = labelForTag(tag);
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'topic-chip';
        button.dataset.filter = tag;
        button.setAttribute('aria-pressed', tag === activeFilter ? 'true' : 'false');

        const iconPath = TAG_ICON[tag];
        if (iconPath) {
            const img = document.createElement('img');
            img.src = iconPath;
            img.alt = '';
            img.setAttribute('aria-hidden', 'true');
            button.appendChild(img);
        }

        button.appendChild(document.createTextNode(label));
        button.addEventListener('click', () => toggleTopicSelection(tag));
        fragment.appendChild(button);
        topicButtons.set(tag, button);
    });

    topicBody.appendChild(fragment);
    updateTopicButtons(activeFilter);
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
            const rawList = groups.get(profile.id);
            const unique = uniqueByTitle(rawList);
            const list = sortByEventTime(unique);
            const sample = list[0];
            const count = list.length;
            const suffix = count === 1 ? 'event' : 'events';
            const countLabel = count > 20 ? '20+ events' : `${count} ${suffix}`;
            const sampleWhen = [sample?.when, sample?.where].filter(Boolean).join(' • ');
            const sampleLine = sample ? `${sample.title}${sampleWhen ? ` — ${sampleWhen}` : ''}` : '';
            return `<article class="cluster-card" data-vibe="${profile.id}" role="button" tabindex="0" aria-pressed="false">
                <span class="cluster-card__title">${profile.label}</span>
                <span class="cluster-card__count">${countLabel}</span>
                <span class="cluster-card__sample">${sampleLine}</span>
            </article>`;
        }).join('');

    clusterDeckEl.innerHTML = cards;
    clusterDeckEl.hidden = !cards.length;
    updateVibeCards();
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
        'data/events.json',
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

function renderMetaAlert(meta) {
    if (!metaAlert || !metaAlertSummary || !metaAlertList) return;
    const stats = Array.isArray(meta?.source_stats) ? meta.source_stats : [];
    const relevantStatuses = new Set(['error', 'fallback', 'offline']);
    const issues = stats.filter(entry => {
        const status = typeof entry?.status === 'string' ? entry.status.toLowerCase() : '';
        return relevantStatuses.has(status);
    });

    if (issues.length === 0) {
        metaAlert.hidden = true;
        metaAlertSummary.textContent = '';
        metaAlertList.replaceChildren();
        return;
    }

    const hasFallback = issues.some(issue => (issue.status || '').toLowerCase() === 'fallback');
    const hasError = issues.some(issue => (issue.status || '').toLowerCase() === 'error');
    const offlineOnly = issues.every(issue => (issue.status || '').toLowerCase() === 'offline');

    let summary;
    if (offlineOnly) {
        summary = 'Scraperen ble kjørt uten nett – data vises fra sample-filen.';
    } else if (hasFallback) {
        summary = 'Vi viser sample-data mens vi venter på frisk feed.';
    } else if (hasError) {
        summary = 'Noen kilder er utilgjengelige. Vi følger med og oppdaterer så snart de svarer.';
    } else {
        summary = 'Noen kilder er midlertidig utilgjengelige.';
    }
    metaAlertSummary.textContent = summary;

    const fragment = document.createDocumentFragment();
    issues.slice(0, 8).forEach(issue => {
        const status = typeof issue?.status === 'string' ? issue.status.toLowerCase() : '';
        let label = issue?.name || 'Ukjent kilde';
        if (status === 'fallback') {
            label = 'Fallback-feed';
        } else if (status === 'offline' && (!issue?.name || issue.name.toLowerCase() === 'sample')) {
            label = 'Offline-modus';
        }

        let detail;
        if (status === 'error') {
            detail = issue?.error || 'klarte ikke hente data.';
        } else if (status === 'fallback') {
            detail = 'viser midlertidige sample-eventer.';
        } else if (status === 'offline') {
            detail = 'scraperen ble kjørt uten nettverk.';
        } else if (issue?.error) {
            detail = issue.error;
        } else {
            detail = 'er midlertidig utilgjengelig.';
        }

        const item = document.createElement('li');
        item.textContent = `${label}: ${detail}`;
        fragment.appendChild(item);
    });

    if (issues.length > 8) {
        const extraNotice = document.createElement('li');
        extraNotice.textContent = `…og ${issues.length - 8} flere kilder venter på svar.`;
        fragment.appendChild(extraNotice);
    }

    metaAlertList.replaceChildren(fragment);
    metaAlert.hidden = false;
}

function handleSurprise() {
    const currentList = getCurrentList();
    const activeDatasetKey = getActiveDatasetKey();
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

function handleSmartFilterClick(event) {
    const button = event.target.closest('button[data-smart]');
    if (!button || button.disabled) return;
    const id = button.dataset.smart;
    const activeId = getCurrentSmartFilter();
    if (activeId === id) {
        setCurrentSmartFilter(null);
        applyFilter(getActiveDatasetKey() || 'all');
        return;
    }
    applySmartFilter(id);
}

async function boot() {
    const [allRaw, todayRaw, tonightRaw, heatmap, meta] = await Promise.all([
        loadEvents(),
        loadSupplemental('./data/generated/today.json'),
        loadSupplemental('./data/generated/tonight.json'),
        loadSupplemental('./data/generated/heatmap.json'),
        loadSupplemental('./data/generated/meta.json')
    ]);

    const allEvents = enrichEvents(Array.isArray(allRaw) ? allRaw : []);
    const todayEvents = enrichEvents(Array.isArray(todayRaw) ? todayRaw : []);
    const tonightEvents = enrichEvents(Array.isArray(tonightRaw) ? tonightRaw : []);
    setDatasets({
        all: allEvents,
        today: todayEvents,
        tonight: tonightEvents
    });

    resetState();

    const params = new URLSearchParams(window.location.search);
    const datasetParam = params.get('dataset');
    if (datasetParam && DATASET_FILTERS.has(datasetParam)) {
        setActiveDatasetKey(datasetParam);
    } else {
        setActiveDatasetKey(defaultDatasetKey());
    }
    const tagParam = params.get('tag');
    if (tagParam) {
        setCurrentFilter(tagParam);
    }
    const vibeParam = params.get('vibe');
    if (vibeParam && VIBE_LOOKUP[vibeParam]) {
        setCurrentVibe(vibeParam);
    }
    const smartParam = params.get('smart');
    if (smartParam && SMART_FILTER_MAP.has(smartParam)) {
        setCurrentSmartFilter(smartParam);
    }

    renderFilters(allEvents);
    lastMeta = meta || {};
    renderMetaAlert(lastMeta);

    const baseDataset = getDataset(getActiveDatasetKey());
    renderSmartFilters(baseDataset);
    renderClusters(baseDataset);
    renderDensityMap(baseDataset);
    renderSourceRollup(baseDataset);

    if (heatmap && typeof heatmap === 'object' && !Array.isArray(heatmap)) {
        renderHeatmap(heatmap);
    } else {
        renderHeatmap(null);
    }

    const availableTags = collectTags();
    const currentFilter = getCurrentFilter();
    if (currentFilter && !availableTags.has(currentFilter)) {
        setCurrentFilter(null);
    }

    const currentVibe = getCurrentVibe();
    if (currentVibe && !hasVibe(currentVibe)) {
        setCurrentVibe(null);
    }

    const currentSmart = getCurrentSmartFilter();
    if (currentSmart) {
        const definition = SMART_FILTER_MAP.get(currentSmart);
        if (!definition || !allEvents.some(event => definition.predicate(event))) {
            setCurrentSmartFilter(null);
        }
    }

    const activeDatasetKey = getActiveDatasetKey();
    const activeFilter = getCurrentFilter();
    const activeVibe = getCurrentVibe();
    const activeSmart = getCurrentSmartFilter();

    if (activeFilter) {
        applyFilter(activeFilter);
    } else if (activeVibe) {
        applyVibeFilter(activeVibe);
    } else if (activeSmart) {
        applySmartFilter(activeSmart);
    } else if (activeDatasetKey && activeDatasetKey !== 'all') {
        applyFilter(activeDatasetKey);
    } else {
        applyFilter('all');
    }
}

filterContainers.forEach(container => {
    container.addEventListener('click', handleFilterClick);
});

if (filterBar) {
    filterBar.classList.add('filters--ready');
}

datasetButtons.forEach(button => {
    button.addEventListener('click', handleDatasetButtonClick);
});

smartFiltersContainer?.addEventListener('click', handleSmartFilterClick);

function handleClusterActivation(card) {
    if (!card) return;
    const vibeId = card.dataset.vibe;
    if (!vibeId) return;
    applyVibeFilter(vibeId);
}

clusterDeckEl?.addEventListener('click', event => {
    const card = event.target.closest('.cluster-card');
    if (!card) return;
    event.preventDefault();
    handleClusterActivation(card);
});

clusterDeckEl?.addEventListener('keydown', event => {
    if (event.key === 'Enter' || event.key === ' ') {
        const card = event.target.closest('.cluster-card');
        if (!card) return;
        event.preventDefault();
        handleClusterActivation(card);
    }
});

topicTriggers.forEach(trigger => {
    trigger.addEventListener('click', () => {
        if (topicDrawer?.hidden) {
            openTopicDrawer(trigger);
        } else {
            lastTopicTrigger = trigger;
            closeTopicDrawer();
        }
    });
});

topicApplyBtn?.addEventListener('click', applyPendingTopic);
topicClearBtn?.addEventListener('click', clearPendingTopic);
topicCloseBtn?.addEventListener('click', closeTopicDrawer);
topicBackdrop?.addEventListener('click', closeTopicDrawer);

const yearEl = $('#year');
if (yearEl) {
    yearEl.textContent = new Date().getFullYear();
}

const timezoneChip = document.getElementById('timezone-chip');
if (timezoneChip) {
    try {
        const formatter = new Intl.DateTimeFormat('en-GB', {
            timeZone: 'Europe/Oslo',
            timeZoneName: 'short'
        });
        const zonePart = formatter.formatToParts(new Date()).find(part => part.type === 'timeZoneName');
        const label = zonePart?.value || 'CEST';
        timezoneChip.textContent = `Tidssone: Bergen (${label})`;
    } catch (error) {
        timezoneChip.textContent = 'Tidssone: Bergen (CEST)';
    }
}

document.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
        if (!topicDrawer?.hidden) {
            event.preventDefault();
            closeTopicDrawer();
            return;
        }
        if (!detailLayer?.hidden) {
            event.preventDefault();
            closeDetail();
            return;
        }
        clearSpotlight();
    }
});

detailCloseBtn?.addEventListener('click', () => {
    closeDetail();
});

detailBackdrop?.addEventListener('click', () => {
    closeDetail();
});

boot();
