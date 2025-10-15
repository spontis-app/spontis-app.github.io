const store = {
    all: [],
    today: [],
    tonight: []
};

export function setDatasets(payload) {
    if (!payload || typeof payload !== 'object') return;
    if (Array.isArray(payload.all)) {
        store.all = payload.all;
    }
    if (Array.isArray(payload.today)) {
        store.today = payload.today;
    }
    if (Array.isArray(payload.tonight)) {
        store.tonight = payload.tonight;
    }
}

export function setDataset(key, events) {
    if (!key) return;
    store[key] = Array.isArray(events) ? events : [];
}

export function getDataset(key) {
    if (key === 'today') return store.today;
    if (key === 'tonight') return store.tonight;
    return store.all;
}

export function getDatasets() {
    return {
        all: store.all,
        today: store.today,
        tonight: store.tonight
    };
}

export function collectTags() {
    const tags = new Set();
    store.all.forEach(event => {
        (event.tags || []).forEach(tag => tags.add(tag));
    });
    return tags;
}

export function hasVibe(vibeId) {
    if (!vibeId) return false;
    return store.all.some(event => (event.vibe || 'performance') === vibeId);
}
