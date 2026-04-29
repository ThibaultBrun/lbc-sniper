-- =====================================================================
-- FAVORITES : annonces marquees en favori par un user
-- =====================================================================
create table if not exists favorites (
  user_id      uuid not null references auth.users(id) on delete cascade,
  ad_id        bigint not null references ads(id) on delete cascade,
  created_at   timestamptz not null default now(),
  -- Pour l'alerte "baisse de prix": on memorise le prix au moment du favori.
  -- Si current_price descend en dessous, on declenche un mail.
  price_at_fav numeric,
  -- Dernier prix pour lequel l'utilisateur a deja ete notifie (= 0 baisse
  -- recente non vue). Permet d'eviter de spammer si le prix oscille.
  last_notified_price numeric,
  primary key (user_id, ad_id)
);

create index if not exists favorites_user_idx on favorites(user_id);
create index if not exists favorites_ad_idx on favorites(ad_id);

alter table favorites enable row level security;

drop policy if exists "users read own favorites" on favorites;
create policy "users read own favorites" on favorites
  for select using (auth.uid() = user_id);

drop policy if exists "users insert own favorites" on favorites;
create policy "users insert own favorites" on favorites
  for insert with check (auth.uid() = user_id);

drop policy if exists "users delete own favorites" on favorites;
create policy "users delete own favorites" on favorites
  for delete using (auth.uid() = user_id);

drop policy if exists "users update own favorites" on favorites;
create policy "users update own favorites" on favorites
  for update using (auth.uid() = user_id);


-- =====================================================================
-- SAVED_SEARCHES : recherches sauvegardees par un user (filtres + alerte)
-- =====================================================================
create table if not exists saved_searches (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid not null references auth.users(id) on delete cascade,
  name                text not null,
  -- Le set complet des filtres UI (category_label, geo, radiusKm, priceMin,
  -- priceMax, electricFilter, searchText, min_deal_score).
  -- Format : voir SavedSearchFilters cote front.
  filters             jsonb not null default '{}'::jsonb,
  -- Alertes mail : 'off' / 'instant' / 'daily'.
  notify_mode         text not null default 'daily' check (notify_mode in ('off', 'instant', 'daily')),
  last_notified_at    timestamptz,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);

create index if not exists saved_searches_user_idx on saved_searches(user_id);
create index if not exists saved_searches_notify_idx on saved_searches(notify_mode) where notify_mode != 'off';

alter table saved_searches enable row level security;

drop policy if exists "users read own searches" on saved_searches;
create policy "users read own searches" on saved_searches
  for select using (auth.uid() = user_id);

drop policy if exists "users insert own searches" on saved_searches;
create policy "users insert own searches" on saved_searches
  for insert with check (auth.uid() = user_id);

drop policy if exists "users update own searches" on saved_searches;
create policy "users update own searches" on saved_searches
  for update using (auth.uid() = user_id);

drop policy if exists "users delete own searches" on saved_searches;
create policy "users delete own searches" on saved_searches
  for delete using (auth.uid() = user_id);

-- Trigger updated_at
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists saved_searches_touch_updated_at on saved_searches;
create trigger saved_searches_touch_updated_at
  before update on saved_searches
  for each row execute function public.touch_updated_at();
