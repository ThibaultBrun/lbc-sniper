-- Fix : la policy "admins read all profiles" creait une recursion infinie
-- (USING fait un SELECT sur profiles -> trigger la meme policy -> SELECT...).
-- Resultat: timeout silencieux des qu'on lit sa propre ligne profile.
-- On la remplace par un appel a public.is_admin() qui est SECURITY DEFINER,
-- donc bypasse RLS lors du check (pas de recursion).

drop policy if exists "admins read all profiles" on profiles;

create policy "admins read all profiles" on profiles
  for select using (public.is_admin());
