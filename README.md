# Price Tracker

Sistema di monitoraggio prezzi per tour turistici da Civitatis.

## Funzionalità

- **Catalogo Tour**: Esplora tour da 10+ destinazioni (Roma, Firenze, Venezia, Parigi, Barcellona, ecc.)
- **Monitoraggio Prezzi**: Sync automatico ogni 6 ore con storico completo
- **Grafici Prezzi**: Visualizza l'andamento dei prezzi nel tempo
- **Sistema Alert**: Notifiche su variazioni prezzo (drop, increase, % change)
- **Dashboard**: Panoramica statistiche e tour monitorati

## Tech Stack

| Layer | Tecnologie |
|-------|------------|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy (async), PostgreSQL, APScheduler |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, React Query, Recharts |
| **Scraping** | Playwright (Chromium), BeautifulSoup4 |
| **Infrastructure** | Docker, docker-compose, Nginx |

## Quick Start

### Sviluppo

```bash
# Clone repository
git clone https://github.com/pietro1412/PRICE-TRACKER.git
cd PRICE-TRACKER

# Configura environment
cp .env.example .env

# Avvia i servizi
docker-compose up -d

# Inizializza database
docker-compose exec backend alembic upgrade head

# Accedi
# Frontend: http://localhost:5173
# API Docs: http://localhost:8000/api/docs
```

### Produzione

```bash
# Configura environment per produzione
cp .env.example .env
# Modifica .env con valori sicuri (SECRET_KEY, POSTGRES_PASSWORD, ecc.)

# Avvia in produzione
docker-compose -f docker-compose.prod.yml up -d

# Accedi
# http://localhost:80
```

## Struttura Progetto

```
PRICE-TRACKER/
├── backend/
│   ├── src/
│   │   ├── api/           # FastAPI routes
│   │   ├── core/          # Config, database, security
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic (scraper, sync, alerts)
│   │   └── utils/         # Logger, rate limiter
│   ├── alembic/           # Database migrations
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Route pages
│   │   ├── lib/           # API client
│   │   └── stores/        # Zustand stores
│   └── Dockerfile
├── nginx/                 # Reverse proxy config
├── scripts/               # Startup scripts
├── docker-compose.yml     # Development
└── docker-compose.prod.yml # Production
```

## API Endpoints

| Endpoint | Metodi | Descrizione |
|----------|--------|-------------|
| `/api/auth/*` | POST, GET | Autenticazione (register, login, refresh) |
| `/api/tours` | GET, POST | Lista e creazione tour |
| `/api/tours/{id}` | GET, PATCH, DELETE | Operazioni su singolo tour |
| `/api/tours/{id}/prices` | GET | Storico prezzi |
| `/api/alerts` | GET, POST | Gestione alert |
| `/api/notifications` | GET, POST | Notifiche utente |
| `/api/admin/*` | GET, POST | Amministrazione (sync, scheduler) |

Documentazione completa: `http://localhost:8000/api/docs`

## Configurazione

Variabili ambiente principali (`.env`):

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `SECRET_KEY` | - | Chiave segreta JWT (min 32 chars) |
| `POSTGRES_PASSWORD` | postgres | Password database |
| `SYNC_PRICES_INTERVAL_HOURS` | 6 | Intervallo sync prezzi |
| `SCRAPE_RATE_LIMIT_SECONDS` | 30 | Rate limit tra richieste |

## Branching Strategy

| Branch | Scopo |
|--------|-------|
| `main` | Produzione stabile |
| `develop` | Integrazione feature |
| `feature/*` | Sviluppo nuove funzionalità |

## License

MIT
