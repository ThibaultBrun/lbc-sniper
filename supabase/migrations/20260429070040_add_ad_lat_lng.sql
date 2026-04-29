-- Latitude / longitude de l'annonce (renvoyees par LBC dans ad.location).
-- Utilises pour le filtre geographique cote frontend (calcul de distance Haversine
-- entre la position de l'utilisateur et chaque annonce).

alter table ads add column if not exists ad_lat numeric;
alter table ads add column if not exists ad_lng numeric;
