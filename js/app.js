const $ = s => document.querySelector(s);
const eventsEl = $('#events');
const filterBtns = [...document.querySelectorAll('.filters button[data-filter]')];

const TAG_STYLE = { date: 'badge--date', girls: 'badge--girls', quiz: 'badge--quiz', cinema: 'badge--cinema', rave: 'badge--rave' };

function paint(list) {
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

async function boot() {
    const r = await fetch('/data/events.sample.json');
    const data = await r.json();
    window.__ALL = data;
    paint(data);
}
boot();

filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        filterBtns.forEach(b => b.classList.remove('chip--active'));
        btn.classList.add('chip--active');
        const k = btn.dataset.filter;
        paint(k === 'all' ? window.__ALL : window.__ALL.filter(e => (e.tags || []).includes(k)));
    });
});

$('#surprise').addEventListener('click', () => {
    const A = window.__ALL || []; if (!A.length) return;
    const e = A[Math.floor(Math.random() * A.length)];
    alert(`Try this: ${e.title} — ${e.when} @ ${e.where}`);
});
$('#year').textContent = new Date().getFullYear();

if (!list.length) { eventsEl.innerHTML = `<p style="opacity:.7">No events yet. Try another filter.</p>`; return; }

async function boot() {
    try {
        const r = await fetch('./data/events.sample.json?v=4');
        if (!r.ok) throw new Error();
        window.__ALL = await r.json();
    } catch {
        window.__ALL = [
            { title: "Quiz at Det Akademiske Kvarter", when: "Thu 20:00", where: "Kvarteret", tags: ["quiz"], url: "https://kvarteret.no/" },
            { title: "Midnight Rave", when: "Fri 23:59", where: "USF Verftet", tags: ["rave"], url: "https://ra.co/" },
            { title: "Paint n’ Sip", when: "Sat 18:00", where: "Kulturhuset", tags: ["girls", "date"], url: "https://ticketco.events/" },
            { title: "Cinema: Sci-Fi Classics", when: "Tonight 21:15", where: "Bergen Kino", tags: ["cinema", "date"], url: "https://bergenkino.no/" }
        ];
    }
    paint(window.__ALL);
}
