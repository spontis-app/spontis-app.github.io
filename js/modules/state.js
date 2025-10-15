const state = {
    activeDatasetKey: 'all',
    currentFilter: null,
    currentList: [],
    currentVibe: null,
    currentSmartFilter: null,
};

export function getActiveDatasetKey() {
    return state.activeDatasetKey;
}

export function setActiveDatasetKey(value) {
    state.activeDatasetKey = value || 'all';
}

export function getCurrentFilter() {
    return state.currentFilter;
}

export function setCurrentFilter(value) {
    state.currentFilter = value || null;
}

export function getCurrentList() {
    return state.currentList;
}

export function setCurrentList(list) {
    if (Array.isArray(list)) {
        state.currentList = list;
    } else {
        state.currentList = [];
    }
}

export function getCurrentVibe() {
    return state.currentVibe;
}

export function setCurrentVibe(value) {
    state.currentVibe = value || null;
}

export function resetState() {
    state.activeDatasetKey = 'all';
    state.currentFilter = null;
    state.currentList = [];
    state.currentVibe = null;
    state.currentSmartFilter = null;
}

export function snapshotState() {
    return { ...state };
}

export function getCurrentSmartFilter() {
    return state.currentSmartFilter;
}

export function setCurrentSmartFilter(value) {
    state.currentSmartFilter = value || null;
}
