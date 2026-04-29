-- Categorie d'usage VTT : XC, trail, all-mountain, enduro, DH/freeride.
-- Renseignee par 2 sources (avec priorite) :
--   1. table de mapping marque/modele cote scraper Python (fiable, evolutif)
--   2. fallback IA Claude pendant l'enrichissement
-- NULL = pas encore classifie (annonce ancienne ou modele non reconnu).

-- Enum strict pour eviter le typo-soup.
do $$
begin
  if not exists (select 1 from pg_type where typname = 'vtt_category') then
    create type vtt_category as enum ('xc', 'trail', 'all_mountain', 'enduro', 'dh', 'dirt');
  end if;
end $$;

alter table public.ads
  add column if not exists vtt_category vtt_category;

-- Index pour le filtre UI (avec is_active + admin_hidden, similaire a celui
-- qu'on a deja sur category_label + deal_score).
create index if not exists idx_ads_vtt_category
  on public.ads (vtt_category)
  where is_active = true and admin_hidden = false;

-- Recree la vue listings pour exposer la nouvelle colonne (CREATE OR REPLACE
-- ne suffit pas si on ajoute des colonnes apres coup).
create or replace view public.listings as
  select * from public.ads;
alter view public.listings set (security_invoker = true);
grant select on public.listings to anon, authenticated;
grant insert, update, delete on public.listings to authenticated;
