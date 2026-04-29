-- Contournement des adblockers grand public (uBlock, AdBlock...) qui bloquent
-- les URLs contenant "/ads?" via pattern matching naif. Symptome cote user :
-- "ERR_BLOCKED_BY_CLIENT" sur les requetes Supabase REST.
--
-- Plutot que de renommer la table (risque sur le scraper Python qui tourne
-- en background, FK, indexes, RLS), on cree une VUE `listings` qui expose
-- la table `ads` 1:1. Postgres rend les vues simples (sans agregat ni jointure)
-- automatiquement updatable, donc INSERT/UPDATE/DELETE marchent en transparent.
--
-- Cote front : on remplace tous les .from("ads") par .from("listings").
-- Cote scraper : on garde .table("ads") (le scraper n'est pas affecte par les
-- adblockers, il tourne cote serveur).

create or replace view public.listings as
  select * from public.ads;

-- Les vues n'heritent pas des policies RLS de la table sous-jacente
-- automatiquement : elles s'executent avec les privileges du proprietaire
-- de la vue (par defaut : postgres / superuser). Pour que la vue respecte
-- les policies de `ads`, on doit la creer avec security_invoker = true
-- (Postgres 15+, Supabase est en 15+).
alter view public.listings set (security_invoker = true);

-- Donner les permissions equivalentes a `ads` sur la vue.
grant select on public.listings to anon, authenticated;
grant insert, update, delete on public.listings to authenticated;
