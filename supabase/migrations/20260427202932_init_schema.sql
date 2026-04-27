-- ============================================================================
-- LBC Parser - Schema Supabase
-- À exécuter dans le SQL Editor de Supabase (1 seule fois)
-- ============================================================================

-- Annonces : 1 ligne par annonce LBC unique (clé = list_id LBC)
create table if not exists ads (
  id                bigint primary key,
  watch_id          text not null,
  subject           text not null,
  body              text,
  url               text not null,
  image_url         text,
  city              text,
  zipcode           text,
  category_id       text,
  category_name     text,

  -- Prix actuel (le scraper le met à jour à chaque run)
  current_price     numeric,

  -- Champs enrichis par Claude (peuplés par enricher.py)
  brand                  text,
  model                  text,
  year                   int,
  frame_material         text,
  wheel_size             text,
  electric               boolean,
  size_label             text,
  condition_score        int,        -- 0-100
  estimated_market_eur   numeric,
  deal_score             int,        -- 0-100, pivot du tri/filtre
  reasoning              text,
  enriched_at            timestamptz,
  enrich_model           text,        -- "opus" / "haiku"
  enrich_error           text,        -- si l'enrichissement a échoué

  -- Métadonnées de découverte
  first_publication      timestamptz,
  first_seen_at          timestamptz not null default now(),
  last_seen_at           timestamptz not null default now(),
  is_active              boolean not null default true
);

create index if not exists ads_watch_id_idx           on ads(watch_id);
create index if not exists ads_deal_score_idx         on ads(deal_score desc nulls last);
create index if not exists ads_enriched_at_idx        on ads(enriched_at);
create index if not exists ads_is_active_idx          on ads(is_active);

-- Historique des prix : 1 ligne à chaque fois qu'un prix change
create table if not exists price_history (
  id        bigserial primary key,
  ad_id     bigint not null references ads(id) on delete cascade,
  price     numeric not null,
  seen_at   timestamptz not null default now()
);

create index if not exists price_history_ad_id_idx on price_history(ad_id, seen_at desc);

-- Runs du scraper (audit / debug / observabilité)
create table if not exists runs (
  id              bigserial primary key,
  watch_id        text not null,
  kind            text not null,    -- "scrape" ou "enrich"
  started_at      timestamptz not null default now(),
  finished_at     timestamptz,
  ads_processed   int default 0,
  ads_new         int default 0,
  ads_updated     int default 0,
  error           text
);

create index if not exists runs_watch_started_idx on runs(watch_id, started_at desc);

-- ============================================================================
-- Row Level Security
-- Lecture publique (le site web utilise la clé anon)
-- Écriture interdite via API publique (le scraper utilise la service_role key)
-- ============================================================================

alter table ads            enable row level security;
alter table price_history  enable row level security;
alter table runs           enable row level security;

-- Lecture publique pour le site web
drop policy if exists "public read ads" on ads;
create policy "public read ads" on ads
  for select using (true);

drop policy if exists "public read price_history" on price_history;
create policy "public read price_history" on price_history
  for select using (true);

-- runs : pas de lecture publique (info technique interne)
-- Pas de policy = personne ne lit via la clé anon. La service_role bypass RLS.
