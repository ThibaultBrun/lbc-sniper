-- Index partiel qui matche pile la requete de la home :
--   WHERE is_active = true AND category_label IN (...) ORDER BY deal_score DESC NULLS LAST
-- Sans cet index : seq scan + tri en memoire a chaque hit.
-- Avec : lecture ordonnee directe, ~10x plus rapide sur le first paint.
create index if not exists idx_ads_active_cat_score
  on public.ads (category_label, deal_score desc nulls last)
  where is_active = true;
