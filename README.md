# ŁKS Dashboard

Lekki dashboard kibicowski ŁKS Łódź dla sezonu 2026/27. Strona pokazuje bieżącą tabelę I ligi, ostatni i następny mecz, formę, statystyki sezonowe, terminarz oraz podstawowe porównanie z najbliższym rywalem.

**Aplikacja:** https://darekpe79.github.io/lks-dashboard/

## Co pokazuje dashboard

- ostatni i następny mecz ŁKS,
- datę, dzień tygodnia i godzinę spotkania,
- miejsce, punkty, bilans i bramki,
- formę z ostatnich 5 meczów,
- statystyki dom / wyjazd i serie,
- najbliższe mecze z dniem tygodnia i godziną,
- tabelę I ligi,
- statystyki najbliższego przeciwnika,
- liderów wybranych statystyk ligowych.

## Dane i automatyczne aktualizacje

Dane są pobierane z **Free API Live Football Data** przez RapidAPI. Klucz API nie trafia do frontendu — jest przechowywany jako sekret GitHub Actions `RAPIDAPI_KEY`.

Automatyzacja znajduje się w:

- `.github/workflows/refresh-data.yml` — pobieranie i przebudowa danych,
- `.github/workflows/pages.yml` — publikacja strony na GitHub Pages.

Aktualnie pełne odświeżenie tabeli i terminarza uruchamia się codziennie rano oraz dodatkowo w poniedziałek wieczorem. W piątek, sobotę i niedzielę wieczorem wykonywane jest dodatkowe odświeżenie terminarza ŁKS.

## Jak działa przepływ danych

```text
RapidAPI
  ↓
data/i_liga_standing.json
data/lks_match_search.json
  ↓
scripts/build_current_season.py
  ↓
scripts/build_dashboard_stats.py
  ↓
data/dashboard.json
  ↓
GitHub Pages
```

Frontend (`index.html`, `styles.css`, `app.js`) czyta wyłącznie przygotowany plik `data/dashboard.json`.

## Uruchomienie lokalne

Po sklonowaniu repozytorium:

```powershell
git pull
python scripts/build_dashboard_stats.py
python -m http.server 8000
```

Następnie otwórz:

```text
http://localhost:8000
```

Do lokalnych wywołań RapidAPI potrzebny jest plik `.env` z:

```text
RAPIDAPI_KEY=...
```

Plik `.env` jest ignorowany przez Git.
