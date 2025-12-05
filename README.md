# CSC410FinalProject
AI NFL Offensive Player Stat Predictor

## Django app (local)

1) Create venv and install deps:
```
python -m venv env
source env/bin/activate
pip install -r requirements.txt
```
2) Run migrations and create a superuser:
```
cd backend
python manage.py migrate
python manage.py createsuperuser
```
3) Start the dev server:
```
python manage.py runserver
```

## API endpoints (stubs)
- `GET /api/health/` simple health check.
- `GET /api/projections/?position=WR&season=2025&scoring=ppr&top=10` calls `fantasy_ml.predict_upcoming_week_topn`.
- `GET /api/historical/?position=WR&season=2024&week=1&scoring=ppr&top=10` calls `nfl.get_top_players_week`.
- `GET /api/player-search/?q=just` placeholder typeahead.
- Authenticated: `GET/POST /api/favorites/`, `/api/saved-searches/`, `/api/cached-results/`.

Hook up templates/HTMX or a JS frontend to render pages for search, favorites, and “This Week’s Top Predictions.” Tailwind can be added via `django-tailwind` or a static build step if desired.


How to run the files:
python3 nfl.py --season 2025 --position WR --week 13 --top 10 python3 fantasy_ml.py --season 2025 --position WR --top 10 --scoring ppr
