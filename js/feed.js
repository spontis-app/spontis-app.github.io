const NOW_WINDOW_MS = 4 * 60 * 60 * 1000; // 4 hours
const TONIGHT_WINDOW_MS = 14 * 60 * 60 * 1000; // rest of evening
const ALLOWED_PAST_MS = 45 * 60 * 1000; // keep items that just started

function eventKey(event) {
    const title = (event?.title || "").trim().toLowerCase();
    const starts = (event?.starts_at || "").trim().toLowerCase();
    const url = (event?.url || "").trim().toLowerCase();
    return `${title}|${starts}|${url}`;
}

export function limitBySource(events, options = {}) {
    if (!Array.isArray(events) || !events.length) {
        return { selected: [], overflow: [] };
    }

    const config = typeof options === 'number' ? { fraction: options } : (options || {});

    const fraction = (typeof config.fraction === 'number' && config.fraction >= 0)
        ? config.fraction
        : 0.25;
    const minRequested = (typeof config.min === 'number' && config.min > 0)
        ? Math.floor(config.min)
        : 1;
    const min = Math.max(1, minRequested);

    let max = config.max;
    if (typeof max === 'number' && max > 0 && Number.isFinite(max)) {
        max = Math.max(min, Math.floor(max));
    } else {
        max = Infinity;
    }

    const keyFn = typeof config.keyFn === 'function'
        ? config.keyFn
        : (event) => (event?.source || "unknown").toLowerCase();

    const limit = Math.min(
        max,
        Math.max(min, Math.ceil(events.length * fraction))
    );
    const counts = new Map();
    const selected = [];
    const overflow = [];

    events.forEach(event => {
        const source = keyFn(event);
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

export function createBalancedFeed(
    events,
    {
        now = new Date(),
        fraction = 0.25,
        upcomingLimit = 8,
        upcomingFraction,
        upcomingMinPerSource = 2,
        upcomingMaxPerSource = 3
    } = {}
) {
    const safeEvents = Array.isArray(events) ? events : [];
    const rawUpcoming = selectUpcomingEvents(safeEvents, { now, limit: upcomingLimit });

    const effectiveUpcomingFraction = (typeof upcomingFraction === 'number' && upcomingFraction >= 0)
        ? upcomingFraction
        : Math.max(fraction, 0.34);
    const upcomingCount = rawUpcoming.length || 1;
    const effectiveUpcomingMin = Math.max(
        1,
        Math.min(upcomingCount, Math.floor(upcomingMinPerSource ?? 1))
    );
    const effectiveUpcomingMax = (typeof upcomingMaxPerSource === 'number' && upcomingMaxPerSource > 0)
        ? Math.max(effectiveUpcomingMin, Math.floor(upcomingMaxPerSource))
        : Infinity;

    const { selected: priority } = limitBySource(rawUpcoming, {
        fraction: effectiveUpcomingFraction,
        min: effectiveUpcomingMin,
        max: effectiveUpcomingMax
    });
    const priorityKeys = new Set(priority.map(eventKey));

    const remainder = safeEvents.filter(event => !priorityKeys.has(eventKey(event)));
    const { selected, overflow } = limitBySource(remainder, { fraction });

    const feed = [...priority, ...selected];
    const feedKeys = new Set(feed.map(eventKey));

    overflow.forEach(event => {
        const key = eventKey(event);
        if (!feedKeys.has(key)) {
            feed.push(event);
            feedKeys.add(key);
        }
    });

    return { feed, upcoming: priority };
}

export { NOW_WINDOW_MS, TONIGHT_WINDOW_MS, ALLOWED_PAST_MS, eventKey };
