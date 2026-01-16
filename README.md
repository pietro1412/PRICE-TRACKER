# Price Tracker

Sistema di monitoraggio prezzi per tour turistici.

## Descrizione

Piattaforma web per il monitoraggio automatico dei prezzi dei tour turistici con:
- Catalogo tour da Civitatis
- Tracciamento variazioni prezzo
- Storico e grafici
- Sistema di alert

## Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy, PostgreSQL
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS
- **Scraping**: Playwright, BeautifulSoup4
- **Infrastructure**: Docker, docker-compose

## Branching Strategy

| Branch | Scopo | Deploy |
|--------|-------|--------|
| `main` | Produzione stabile | Production |
| `develop` | Integrazione feature | Staging |

## Getting Started

```bash
# Clone repository
git clone https://github.com/pietro1412/PRICE-TRACKER.git
cd PRICE-TRACKER

# Start with Docker
docker-compose up -d

# Access
# Frontend: http://localhost:5174
# Backend API: http://localhost:8000/api/docs
```

## Project Management

Le evolutive sono tracciate nel GitHub Project **EVOLUTIVE**.

## License

MIT
