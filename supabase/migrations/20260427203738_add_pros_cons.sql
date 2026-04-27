-- Ajoute des champs structurés pour l'analyse Claude :
--   pros : points forts perçus (jsonb array of strings)
--   cons : points de vigilance / faiblesses (jsonb array of strings)
-- Le champ `reasoning` existant peut être plus long désormais.

alter table ads add column if not exists pros jsonb;
alter table ads add column if not exists cons jsonb;
