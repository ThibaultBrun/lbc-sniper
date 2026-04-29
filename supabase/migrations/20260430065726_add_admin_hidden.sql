-- Colonne separee pour le "hide" admin : le scraper ne la touche pas (contrairement
-- a is_active qu'il remet a true a chaque upsert). Sans ca, supprimer une annonce
-- en tant qu'admin serait annule des le prochain scrape de LBC.
alter table public.ads
  add column if not exists admin_hidden boolean not null default false;

-- Index partiel pour la requete principale du listing.
-- Ancien index : (category_label, deal_score desc nulls last) where is_active = true
-- Nouveau : on ajoute la condition admin_hidden = false pour que la requete
-- "is_active=true AND admin_hidden=false" soit servie directement par l'index.
drop index if exists idx_ads_active_cat_score;
create index if not exists idx_ads_visible_cat_score
  on public.ads (category_label, deal_score desc nulls last)
  where is_active = true and admin_hidden = false;
