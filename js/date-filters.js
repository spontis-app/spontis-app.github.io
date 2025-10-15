export function defaultDatasetKey(now = new Date()) {
    const hour = now.getHours();
    if (hour >= 16 || hour < 4) {
        return 'tonight';
    }
    return 'all';
}

export function isEvening(now = new Date()) {
    const hour = now.getHours();
    return hour >= 16 || hour < 4;
}
