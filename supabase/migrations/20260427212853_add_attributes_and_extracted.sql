-- Stocke les attributs structurés LBC + champs derives pratiques pour le tri/affichage.
--
-- attributes : tout le dict brut renvoyé par LBC (mileage, gearbox, fuel, regdate,
--              bicycle_type, condition, cubic_capacity, etc.). Permet de ne plus
--              jamais perdre une info, et de pouvoir filtrer dessus en SQL.
-- mileage_km : kilometrage extrait (voitures/motos). Plus simple a afficher/sort.
-- fuel       : energie ("Essence", "Diesel", "Hybride", "Electrique", ...).
-- gearbox    : type de boite ("Manuelle", "Automatique").
-- regyear    : annee de mise en circulation (voitures/motos), distincte du `year`
--              modele estime par Claude.

alter table ads add column if not exists attributes jsonb;
alter table ads add column if not exists mileage_km int;
alter table ads add column if not exists fuel text;
alter table ads add column if not exists gearbox text;
alter table ads add column if not exists regyear int;
