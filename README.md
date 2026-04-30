# lbc-sniper

Scrape Le Bon Coin, fait analyser chaque annonce par Claude (estimation de
prix de marchÃ© + score 0â€“100), et expose le tout dans une UI web.

## Architecture

```mermaid
flowchart TB
  U[Utilisateur]
  A[Admin]
  LBC[LeBonCoin API]
  CLAUDE[Claude CLI]
  SMTP[SMTP OVH]
  G[Googlebot / Search Console]

  subgraph ORCH[Pipeline backend - run.bat]
    M[scraper.main\nfetch + upsert]
    C[scraper.cleanup\nverif annonces disparues]
    E[scraper.enricher\nHaiku -> Opus]
    N[scraper.notifier\nprice drops + saved searches]
  end

  subgraph DB[Supabase Postgres]
    ADS[(ads)]
    LIST[(listings view)]
    PH[(price_history)]
    FAV[(favorites)]
    SS[(saved_searches)]
    PRO[(profiles)]
    RUNS[(runs)]
  end

  subgraph WEB[Frontend Vue 3]
    APP[App.vue + router]
    AUTH[Google OAuth via Supabase Auth]
  end

  subgraph SEO[Build SEO]
    PRE[web/scripts/prerender.mjs]
    DIST[dist + /ad/:id + sitemap.xml + robots.txt]
  end

  LBC --> M
  M --> ADS
  M --> PH
  M --> RUNS

  ADS --> C
  LBC --> C
  C --> ADS
  C --> RUNS

  ADS --> E
  CLAUDE --> E
  E --> ADS
  E --> RUNS

  ADS --> N
  FAV --> N
  SS --> N
  PRO --> N
  N --> SMTP

  U --> APP
  APP --> LIST
  APP --> FAV
  APP --> SS
  U --> AUTH
  AUTH --> PRO
  A --> LIST

  LIST --> PRE
  PRE --> DIST
  DIST --> G
```

- **scraper** (`scraper/main.py`) â€” fetch LBC via la lib [`lbc`](https://github.com/etienne-hd/lbc), upsert Supabase
- **enricher** (`scraper/enricher.py`) â€” prend chaque annonce non analysÃ©e, appelle `claude -p --model opus --json-schema ...`, stocke marque/modÃ¨le/annÃ©e/prix marchÃ©/deal_score
- **web** (`web/`) â€” Vue 3 + Vite + Tailwind, requÃªte directe Supabase via clÃ© `anon`

## Setup

### 1. Supabase

Compte gratuit sur https://supabase.com, crÃ©e un projet en rÃ©gion EU. RÃ©cupÃ¨re :
- `Project URL` (Settings → API)
- `anon` key (publique)
- `service_role` key (secrÃ¨te)

### 2. Variables d'env

Copier les templates et remplir :

```bash
cp .env.example .env                 # racine â€” utilisÃ©e par le scraper (service_role)
cp web/.env.example web/.env         # web â€” utilisÃ©e par le frontend (anon)
```

### 3. Migration DB

```bash
supabase link --project-ref <ton-project-ref>
supabase db push
```

### 4. DÃ©pendances

```bash
pip install -r requirements.txt
cd web && npm install
```

### 5. CLI Claude

```bash
claude
/login
/exit
```

(Une seule fois par machine, persiste ensuite.)

## Utilisation

```bash
# Pipeline complet : scrape + enrich
./run.bat

# Lancer le site
./start-web.bat        # http://localhost:5173
```

Ou manuellement :

```bash
python -m scraper.main                        # scrape uniquement
python -m scraper.enricher --limit 10         # enrich (max 10 annonces)
python -m scraper.enricher --model haiku      # mode rapide / moins fin
```

## Configuration des watches

`config.yaml` â€” un watch = une recherche LBC rÃ©guliÃ¨re :

```yaml
watches:
  - id: vtt-enduro-bayonne
    label: "VTT Enduro - 30km autour de Bayonne"
    category: VEHICULES_VELOS
    accept_category_ids: ["55"]      # filtre cÃ´tÃ© client (LBC Ã©largit parfois)
    text: "enduro"
    location:
      city: Bayonne
      lat: 43.4933
      lng: -1.4747
      radius_km: 30
    price_max: 5000
    limit: 100
    enrichment_domain: "vtt_enduro"  # pilote le contexte expert du prompt Claude
```

## HÃ©bergement (Ã  venir)

- **Scraper** : tÃ¢che planifiÃ©e Windows toutes les 6h (IP rÃ©sidentielle FR Ã©vite Datadome)
- **Web** : Vercel ou Netlify (statique, gratuit)
- **DB** : Supabase tier gratuit largement suffisant

## Stack

- Python 3.11+ (`lbc`, `supabase-py`)
- Claude CLI (`claude -p --json-schema`)
- Supabase (Postgres + RLS)
- Vue 3 + Vite + Tailwind + supabase-js

