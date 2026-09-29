const LKS_ID = 8244;

const fmtDate = (iso, withTime = true) => {
  if (!iso) return "—";
  const d = new Date(iso);
  const opts = { day: "numeric", month: "long" };
  if (withTime) Object.assign(opts, { hour: "2-digit", minute: "2-digit" });
  return new Intl.DateTimeFormat("pl-PL", opts).format(d);
};

const fmtMatchDate = (iso) => {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("pl-PL", {
    weekday: "long",
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
};

const fmtFixtureDate = (iso) => {
  if (!iso) return { weekday: "—", date: "—", time: "—" };
  const d = new Date(iso);
  return {
    weekday: new Intl.DateTimeFormat("pl-PL", { weekday: "short" }).format(d),
    date: new Intl.DateTimeFormat("pl-PL", { day: "numeric", month: "short" }).format(d),
    time: new Intl.DateTimeFormat("pl-PL", { hour: "2-digit", minute: "2-digit" }).format(d),
  };
};

const escapeHtml = (value = "") => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

function renderMatch(targetId, match, isFinished) {
  const el = document.getElementById(targetId);
  if (!match) {
    el.innerHTML = '<p class="loading">Brak danych o meczu.</p>';
    return;
  }
  const score = isFinished ? (match.status?.scoreStr || "—") : '<span class="versus">VS</span>';
  el.innerHTML = `
    <div class="match-content">
      <div class="match-date">${fmtMatchDate(match.matchDate)}</div>
      <div class="match-line">
        <div class="team-name">${escapeHtml(match.homeTeamName)}</div>
        <div class="score">${score}</div>
        <div class="team-name away">${escapeHtml(match.awayTeamName)}</div>
      </div>
      <div class="match-meta">I Liga</div>
    </div>
  `;
}

function statCard(label, value, sub = "") {
  return `
    <article class="stat-card">
      <div class="stat-label">${label}</div>
      <div class="stat-value">${value}</div>
      <div class="stat-sub">${sub}</div>
    </article>
  `;
}

function renderSummary(data) {
  const s = data.summary;
  document.getElementById("summary-cards").innerHTML = [
    statCard("Miejsce", `${s.position}.`, "w tabeli"),
    statCard("Punkty", s.points, `${s.points_per_match} / mecz`),
    statCard("Bilans", `${s.wins}-${s.draws}-${s.losses}`, "W-R-P"),
    statCard("Bramki", `${s.goals_for}:${s.goals_against}`, `${s.goal_difference >= 0 ? "+" : ""}${s.goal_difference}`),
    statCard("Czyste konta", s.clean_sheets, `z ${s.played} spotkań`),
    statCard("Bez gola", s.failed_to_score, `z ${s.played} spotkań`)
  ].join("");
}

function renderForm(data) {
  document.getElementById("form-row").innerHTML = data.form.map(item => `
    <div class="form-item">
      <div class="form-badge ${item.result}">${item.result === "W" ? "W" : item.result === "D" ? "R" : "P"}</div>
      <div>
        <div class="form-opponent">${escapeHtml(item.opponent)}</div>
        <div class="form-score">${fmtDate(item.date, false)}</div>
      </div>
      <div class="form-score">${escapeHtml(item.score)}</div>
    </div>
  `).join("");
}

function renderDeepStats(data) {
  const h = data.splits.home;
  const a = data.splits.away;
  const best = data.records.best_win;
  const worst = data.records.worst_loss;
  const blocks = [
    ["U siebie", `${h.wins}W · ${h.draws}R · ${h.losses}P · ${h.gf}:${h.ga}`],
    ["Na wyjeździe", `${a.wins}W · ${a.draws}R · ${a.losses}P · ${a.gf}:${a.ga}`],
    ["Najwyższe zwycięstwo", best ? `${best.score} · ${best.homeTeamName} – ${best.awayTeamName}` : "—"],
    ["Najwyższa porażka", worst ? `${worst.score} · ${worst.homeTeamName} – ${worst.awayTeamName}` : "—"],
    ["Mecze ze zdobytym golem", `${data.summary.matches_scored_in} / ${data.summary.played}`],
    ["Gole / mecz", `${data.summary.goals_for_per_match.toFixed(2)} · stracone ${data.summary.goals_against_per_match.toFixed(2)}`]
  ];
  document.getElementById("deep-stats").innerHTML = blocks.map(([label, value]) => `
    <div class="deep-stat"><strong>${escapeHtml(value)}</strong><span>${label}</span></div>
  `).join("");
}

function renderAdvanced(data) {
  const h = data.splits.home;
  const a = data.splits.away;
  const streaks = data.records.streaks;
  const biggest = data.records.biggest_goals;

  const groups = [
    {
      title: "Czyste konta / bez gola",
      rows: [
        ["Czyste konta", `${h.clean_sheets} dom · ${a.clean_sheets} wyjazd · ${data.summary.clean_sheets} razem`],
        ["Bez zdobytej bramki", `${h.failed_to_score} dom · ${a.failed_to_score} wyjazd · ${data.summary.failed_to_score} razem`]
      ]
    },
    {
      title: "Bramki dom / wyjazd",
      rows: [
        ["Zdobyte", `${h.gf} (${h.gf_avg}/mecz) · ${a.gf} (${a.gf_avg}/mecz)`],
        ["Stracone", `${h.ga} (${h.ga_avg}/mecz) · ${a.ga} (${a.ga_avg}/mecz)`],
        ["Najwięcej zdobytych w meczu", `${biggest.for.home} dom · ${biggest.for.away} wyjazd`],
        ["Najwięcej straconych w meczu", `${biggest.against.home} dom · ${biggest.against.away} wyjazd`]
      ]
    },
    {
      title: "Najdłuższe serie",
      rows: [
        ["Zwycięstwa", streaks.wins],
        ["Remisy", streaks.draws],
        ["Porażki", streaks.losses],
        ["Bez porażki", streaks.unbeaten]
      ]
    }
  ];

  document.getElementById("advanced-stats").innerHTML = groups.map(group => `
    <section class="advanced-card">
      <h3>${escapeHtml(group.title)}</h3>
      <div class="advanced-rows">
        ${group.rows.map(([label, value]) => `
          <div class="advanced-row">
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(value)}</strong>
          </div>
        `).join("")}
      </div>
    </section>
  `).join("");
}

function renderNextOpponent(data) {
  const o = data.next_opponent;
  const box = document.getElementById("next-opponent");
  if (!o) {
    box.innerHTML = '<p class="loading">Brak danych o najbliższym rywalu.</p>';
    return;
  }

  document.getElementById("opponent-title").textContent = o.name;
  document.getElementById("opponent-venue").textContent =
    o.venue === "home" ? "mecz u siebie" : "mecz na wyjeździe";

  const gapText = o.points_gap_to_lks === 0
    ? "tyle samo co ŁKS"
    : o.points_gap_to_lks > 0
      ? `+${o.points_gap_to_lks} względem ŁKS`
      : `${o.points_gap_to_lks} względem ŁKS`;

  box.innerHTML = `
    <div class="opponent-hero">
      <div>
        <span class="opponent-rank">${o.position}.</span>
        <span class="opponent-rank-label">miejsce</span>
      </div>
      <div class="opponent-points">
        <strong>${o.points}</strong>
        <span>pkt · ${escapeHtml(gapText)}</span>
      </div>
    </div>

    <div class="opponent-grid">
      <div><span>Bilans</span><strong>${o.wins}-${o.draws}-${o.losses}</strong></div>
      <div><span>Bramki</span><strong>${o.goals_for}:${o.goals_against}</strong></div>
      <div><span>Różnica</span><strong>${o.goal_difference > 0 ? "+" : ""}${o.goal_difference}</strong></div>
      <div><span>Mecze</span><strong>${o.played}</strong></div>
    </div>

    <div class="opponent-compare">
      <div class="compare-head"><span>ŁKS</span><span>${escapeHtml(o.name)}</span></div>
      <div class="compare-row"><span>Punkty</span><b>${data.summary.points}</b><i>${o.points}</i></div>
      <div class="compare-row"><span>Bramki</span><b>${data.summary.goals_for}:${data.summary.goals_against}</b><i>${o.goals_for}:${o.goals_against}</i></div>
      <div class="compare-row"><span>Bilans</span><b>${data.summary.wins}-${data.summary.draws}-${data.summary.losses}</b><i>${o.wins}-${o.draws}-${o.losses}</i></div>
    </div>
  `;
}

function renderUpcoming(data) {
  document.getElementById("upcoming").innerHTML = data.upcoming_matches.map(m => {
    const isHome = String(m.homeTeamId) === String(LKS_ID);
    const opponent = isHome ? m.awayTeamName : m.homeTeamName;
    const when = fmtFixtureDate(m.matchDate);
    return `
      <div class="fixture">
        <div class="fixture-date">
          <strong>${escapeHtml(when.weekday)}</strong>
          <span>${escapeHtml(when.date)} · ${escapeHtml(when.time)}</span>
        </div>
        <div class="fixture-teams">${isHome ? "ŁKS" : escapeHtml(opponent)} <span class="muted">—</span> ${isHome ? escapeHtml(opponent) : "ŁKS"}</div>
        <div class="fixture-tag">${isHome ? "DOM" : "WYJAZD"}</div>
      </div>
    `;
  }).join("");
}

function renderStandings(data) {
  document.getElementById("table-meta").textContent = `${data.summary.played} kolejek ŁKS`;
  document.getElementById("standings-body").innerHTML = data.standings.map(row => `
    <tr class="${row.id === LKS_ID ? "lks" : ""}">
      <td class="pos"><span class="zone" style="background:${row.qualColor || "transparent"}"></span>${row.position}</td>
      <td class="team-cell">${escapeHtml(row.name)}</td>
      <td>${row.played}</td>
      <td>${escapeHtml(row.goals)}</td>
      <td>${row.goal_difference > 0 ? "+" : ""}${row.goal_difference}</td>
      <td class="pts">${row.points}</td>
    </tr>
  `).join("");
}

function renderLeagueLeaders(data) {
  const joinNames = items => items.map(x => x.name).join(" / ");
  const value = items => items[0]?.value ?? "—";
  const cards = [
    ["Najwięcej goli", joinNames(data.league_leaders.best_attack), value(data.league_leaders.best_attack)],
    ["Najmniej straconych", joinNames(data.league_leaders.best_defense), value(data.league_leaders.best_defense)],
    ["Najwięcej straconych", joinNames(data.league_leaders.most_goals_conceded), value(data.league_leaders.most_goals_conceded)]
  ];
  document.getElementById("league-leaders").innerHTML = cards.map(([label, name, val]) => `
    <div class="leader">
      <div><div class="leader-label">${label}</div><div class="leader-name">${escapeHtml(name)}</div></div>
      <div class="leader-value">${val}</div>
    </div>
  `).join("");
}

async function boot() {
  try {
    const response = await fetch("data/dashboard.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();

    renderMatch("previous-match", data.previous_match, true);
    renderMatch("next-match", data.next_match, false);
    renderSummary(data);
    renderForm(data);
    renderDeepStats(data);
    renderAdvanced(data);
    renderNextOpponent(data);
    renderUpcoming(data);
    renderStandings(data);
    renderLeagueLeaders(data);

    document.getElementById("updated-at").textContent =
      "Dashboard: " + new Intl.DateTimeFormat("pl-PL", {
        day:"numeric", month:"short", hour:"2-digit", minute:"2-digit"
      }).format(new Date(data.generated_at_utc));
  } catch (error) {
    document.querySelector("main").innerHTML =
      '<div class="error-box">Nie udało się uruchomić dashboardu. Sprawdź konsolę przeglądarki lub poczekaj na zakończenie wdrożenia GitHub Pages.</div>';
    console.error(error);
  }
}

boot();


const backToTop = document.getElementById("back-to-top");
if (backToTop) {
  const toggleBackToTop = () => {
    backToTop.classList.toggle("visible", window.scrollY > 500);
  };

  window.addEventListener("scroll", toggleBackToTop, { passive: true });
  backToTop.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  toggleBackToTop();
}
