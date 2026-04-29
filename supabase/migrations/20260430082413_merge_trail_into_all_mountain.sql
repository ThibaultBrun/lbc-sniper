-- Fusion : "trail" et "all_mountain" sont devenues une seule categorie.
-- En pratique les VTT 130-150mm chevauchent ces 2 labels et le marche FR
-- d'occasion ne fait pas la distinction.
--
-- 1. Mettre a jour les ads existantes : trail -> all_mountain
-- 2. Modifier l'enum vtt_category pour retirer 'trail'

-- Etape 1 : reclasser les annonces existantes
update public.ads
set vtt_category = 'all_mountain'::vtt_category
where vtt_category = 'trail';

-- Etape 2 : recreer l'enum sans 'trail'
-- Postgres ne permet pas de retirer une valeur d'un enum, on recree le type.
-- Il faut DROP la vue qui depend de la colonne avant de modifier le type colonne.

drop view if exists public.listings;

alter type vtt_category rename to vtt_category_old;

create type vtt_category as enum ('xc', 'all_mountain', 'enduro', 'dh', 'dirt');

-- Convertir la colonne (les valeurs sont deja toutes dans le nouveau set apres l'update)
alter table public.ads
  alter column vtt_category type vtt_category
  using vtt_category::text::vtt_category;

drop type vtt_category_old;

-- Recreer la vue avec le nouveau type
create view public.listings as
  select * from public.ads;
alter view public.listings set (security_invoker = true);
grant select on public.listings to anon, authenticated;
grant insert, update, delete on public.listings to authenticated;
