-- Permet aux admins de "supprimer" une annonce (soft delete : on passe is_active=false).
-- On ne fait pas de hard delete pour preserver l'integrite des favorites / price_history
-- (FK on delete cascade existe deja, mais soft delete est reversible et plus prudent).

-- Reutilise la fonction is_admin() definie dans la migration 20260429211435.
drop policy if exists "admin update ads" on public.ads;
create policy "admin update ads" on public.ads
  for update
  using (public.is_admin())
  with check (public.is_admin());
