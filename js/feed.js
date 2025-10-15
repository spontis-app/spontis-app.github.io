const NOW_WINDOW_MS = 4 * 60 * 60 * 1000; // 4 hours
const TONIGHT_WINDOW_MS = 14 * 60 * 60 * 1000; // rest of evening
const ALLOWED_PAST_MS = 45 * 60 * 1000; // keep items that just started

function eventKey(event) {
    const title = (event?.title || "").trim().toLowerCase();
    const starts = (event?.starts_at || "").trim().toLowerCase();
    const url = (event?.url || "").trim().toLowerCase();
    return `${title}|${starts}|${url}`;
}

export function limitBySource(events, fraction = 0.25) {
    if (!Array.isArray(events) || !events.length) {
        return { selected: [], overflow: [] };
    }
    const limit = Math.max(1, Math.ceil(events.length * fraction));
    const counts = new Map();
    const selected = [];
    const overflow = [];

    events.forEach(event => {
        const source = (event?.source || "unknown").toLowerCase();
        const current = counts.get(source) || 0;
        if (current < limit) {
            selected.push(event);
            counts.set(source, current + 1);
        } else {
            overflow.push(event);
        }
    });
    return { selected, overflow };
}

export function selectUpcomingEvents(events, { now = new Date(), limit = 8 } = {}) {
    if (!Array.isArray(events)) return [];
    const base = now.valueOf();
    const upcoming = [];
    const tonight = [];

    events.forEach(event => {
        const value = event?.starts_at;
        if (!value) return;
        const timestamp = Date.parse(value);
        if (!Number.isFinite(timestamp)) return;

        if (timestamp + ALLOWED_PAST_MS < base) return;
        const diff = timestamp - base;
        if (diff <= NOW_WINDOW_MS) {
            upcoming.push({ event, timestamp });
        } else if (diff <= TONIGHT_WINDOW_MS) {
            tonight.push({ event, timestamp });
        }
    });

    const ordered = upcoming
        .sort((a, b) => a.timestamp - b.timestamp)
        .concat(tonight.sort((a, b) => a.timestamp - b.timestamp))
        .map(entry => entry.event);

    const limited = [];
    const seen = new Set();
    for (const event of ordered) {
        const key = eventKey(event);
        if (seen.has(key)) continue;
        seen.add(key);
        limited.push(event);
        if (limited.length >= limit) break;
    }
    return limited;
}

export function formatRelativeStart(timestamp, now = Date.now()) {
    if (!Number.isFinite(timestamp)) return "";
    const diff = timestamp - now;
    if (Math.abs(diff) < 5 * 60 * 1000) return "Starter nå";
    if (diff < 0) return "Startet nylig";
    const minutes = Math.round(diff / 60000);
    if (minutes < 60) return `Om ${minutes} min`;
    const hours = Math.round(diff / 3600000);
    return `Om ${hours} t`;
}

export function createBalancedFeed(events, { now = new Date(), fraction = 0.25, upcomingLimit = 8 } = {}) {
    const safeEvents = Array.isArray(events) ? events : [];
    const priority = selectUpcomingEvents(safeEvents, { now, limit: upcomingLimit });
    const priorityKeys = new Set(priority.map(eventKey));

    const remainder = safeEvents.filter(event => !priorityKeys.has(eventKey(event)));
    const { selected, overflow } = limitBySource(remainder, fraction);
    const selectedKeys = new Set(selected.map(eventKey));

    const feed = [...priority, ...selected];
    overflow.forEach(event => {
        const key = eventKey(event);
        if (!priorityKeys.has(key) && !selectedKeys.has(key)) {
            feed.push(event);
        }
    });

    return { feed, upcoming: priority };
}

export { NOW_WINDOW_MS, TONIGHT_WINDOW_MS, ALLOWED_PAST_MS, eventKey };
