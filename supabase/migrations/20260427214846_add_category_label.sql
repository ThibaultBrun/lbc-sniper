-- Etiquette de categorie utilisee pour regrouper les watches dans l'UI.
-- Plusieurs watches (un par modele) partagent le meme label (ex: "Voitures").
-- Le scraper le copie depuis le config a chaque upsert.

alter table ads add column if not exists category_label text;
create index if not exists ads_category_label_idx on ads(category_label);
