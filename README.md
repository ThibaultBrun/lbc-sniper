# lbc-sniper

Scrape Le Bon Coin, fait analyser chaque annonce par Claude (estimation de
prix de marchÃƒÂ© + score 0Ã¢â‚¬â€œ100), et expose le tout dans une UI web.

## Architecture

### Vue d'ensemble (simplifiee)

```mermaid
flowchart LR
  LBC[LeBonCoin] --> SCRAPER[scraper.main + cleanup]
  SCRAPER --> DB[(Supabase)]
  DB --> ENRICH[scraper.enricher + Claude]
  ENRICH --> DB
  DB --> WEB[Web Vue 3]
  DB --> NOTIF[scraper.notifier]
  NOTIF --> MAIL[Emails SMTP]
  DB --> SEO[prerender + sitemap]
  SEO --> GOOGLE[Googlebot]
```

### Bloc 1 - Ingestion et nettoyage

```mermaid
flowchart TB
  LBC[LeBonCoin API]
  MAIN[scraper.main]
  CLEAN[scraper.cleanup]
  ADS[(ads)]
  PH[(price_history)]
  RUNS[(runs)]

  LBC --> MAIN
  MAIN --> ADS
  MAIN --> PH
  MAIN --> RUNS

  ADS --> CLEAN
  LBC --> CLEAN
  CLEAN --> ADS
  CLEAN --> RUNS
```

### Bloc 2 - Enrichissement IA

```mermaid
flowchart TB
  ADS[(ads actifs non enrichis)] --> ENR[scraper.enricher]
  ENR --> CLAUDE[Claude CLI\nHaiku puis Opus]
  CLAUDE --> ENR
  ENR --> ADS2[(ads enrichis\nbrand/model/year/deal_score)]
  ENR --> RUNS[(runs)]
```

### Bloc 3 - Alertes utilisateurs

```mermaid
flowchart TB
  ADS[(ads)] --> NOTIF[scraper.notifier]
  FAV[(favorites)] --> NOTIF
  SS[(saved_searches)] --> NOTIF
  PRO[(profiles)] --> NOTIF
  NOTIF --> SMTP[SMTP OVH]
  SMTP --> USER[Utilisateur]
```

### Bloc 4 - Web, auth et SEO

```mermaid
flowchart TB
  USER[Utilisateur] --> APP[App Vue 3]
  APP --> LIST[(listings view)]
  APP --> FAV[(favorites)]
  APP --> SS[(saved_searches)]

  USER --> AUTH[Google OAuth]
  AUTH --> PRO[(profiles)]

  LIST --> PRE[web/scripts/prerender.mjs]
  PRE --> DIST[dist + pages /ad/:id + sitemap.xml]
  DIST --> G[Googlebot / Search Console]
```
- **scraper** (`scraper/main.py`) Ã¢â‚¬â€ fetch LBC via la lib [`lbc`](https://github.com/etienne-hd/lbc), upsert Supabase
- **enricher** (`scraper/enricher.py`) Ã¢â‚¬â€ prend chaque annonce non analysÃƒÂ©e, appelle `claude -p --model opus --json-schema ...`, stocke marque/modÃƒÂ¨le/annÃƒÂ©e/prix marchÃƒÂ©/deal_score
- **web** (`web/`) Ã¢â‚¬â€ Vue 3 + Vite + Tailwind, requÃƒÂªte directe Supabase via clÃƒÂ© `anon`

## Setup

### 1. Supabase

Compte gratuit sur https://supabase.com, crÃƒÂ©e un projet en rÃƒÂ©gion EU. RÃƒÂ©cupÃƒÂ¨re :
- `Project URL` (Settings â†’ API)
- `anon` key (publique)
- `service_role` key (secrÃƒÂ¨te)

### 2. Variables d'env

Copier les templates et remplir :

```bash
cp .env.example .env                 # racine Ã¢â‚¬â€ utilisÃƒÂ©e par le scraper (service_role)
cp web/.env.example web/.env         # web Ã¢â‚¬â€ utilisÃƒÂ©e par le frontend (anon)
```

### 3. Migration DB

```bash
supabase link --project-ref <ton-project-ref>
supabase db push
```

### 4. DÃƒÂ©pendances

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

`config.yaml` Ã¢â‚¬â€ un watch = une recherche LBC rÃƒÂ©guliÃƒÂ¨re :

```yaml
watches:
  - id: vtt-enduro-bayonne
    label: "VTT Enduro - 30km autour de Bayonne"
    category: VEHICULES_VELOS
    accept_category_ids: ["55"]      # filtre cÃƒÂ´tÃƒÂ© client (LBC ÃƒÂ©largit parfois)
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

## HÃƒÂ©bergement (ÃƒÂ  venir)

- **Scraper** : tÃƒÂ¢che planifiÃƒÂ©e Windows toutes les 6h (IP rÃƒÂ©sidentielle FR ÃƒÂ©vite Datadome)
- **Web** : Vercel ou Netlify (statique, gratuit)
- **DB** : Supabase tier gratuit largement suffisant

## Stack

- Python 3.11+ (`lbc`, `supabase-py`)
- Claude CLI (`claude -p --json-schema`)
- Supabase (Postgres + RLS)
- Vue 3 + Vite + Tailwind + supabase-js


