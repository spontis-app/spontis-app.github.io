const $ = s => document.querySelector(s);
const eventsEl = $('#events');
const filterBar = document.querySelector('.filters');

const TAG_STYLE = {
    date: 'badge--date', girls: 'badge--girls', quiz: 'badge--quiz',
    cinema: 'badge--cinema', rave: 'badge--rave'
};

function paint(list) {
    if (!list.length) {
        eventsEl.innerHTML = `<p style="opacity:.7">No events yet. Try another filter or check back later.</p>`;
        return;
    }
    eventsEl.innerHTML = list.map(e => {
        const tags = (e.tags || []).map(t => `<span class="badge ${TAG_STYLE[t] || ''}">${t}</span>`).join('');
        return `<article class="card">
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

function applyFilter(tag) {
    const all = window.__ALL || [];
    const data = tag === 'all' ? all : all.filter(e => (e.tags || []).includes(tag));
    paint(data);
    setActive(tag);
}

async function boot() {
    try {
        // BRUK SAMPLE-FILEN MIDLERTIDIG
        const r = await fetch('./data/events.sample.json?v=6');
        if (!r.ok) throw new Error(r.statusText);
        window.__ALL = await r.json();
    } catch (err) {
        console.warn('Falling back to embedded sample data:', err);
        window.__ALL = [
            { title: "Quiz at Det Akademiske Kvarter", when: "Thu 20:00", where: "Kvarteret", tags: ["quiz"], url: "https://kvarteret.no/" },
            { title: "Midnight Rave", when: "Fri 23:59", where: "USF Verftet", tags: ["rave"], url: "https://ra.co/" },
            { title: "Paint n’ Sip", when: "Sat 18:00", where: "Kulturhuset", tags: ["girls", "date"], url: "https://ticketco.events/" },
            { title: "Cinema: Sci-Fi Classics", when: "Tonight 21:15", where: "Bergen Kino", tags: ["cinema", "date"], url: "https://bergenkino.no/" }
        ];
    }
    applyFilter('all');
}
boot();

filterBar.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-filter]');
    if (!btn) return;
    applyFilter(btn.dataset.filter);
});

$('#surprise')?.addEventListener('click', () => {
    const A = window.__ALL || []; if (!A.length) return;
    const e = A[Math.floor(Math.random() * A.length)];
    alert(`Try this: ${e.title} — ${e.when} @ ${e.where}`);
});

$('#year').textContent = new Date().getFullYear();
