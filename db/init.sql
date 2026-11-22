-- La base de la boutique, au premier démarrage seulement (quand le volume est vide).
-- Ensuite, les données viennent du volume, ou d'une sauvegarde.
CREATE TABLE IF NOT EXISTS produits (
    id      SERIAL PRIMARY KEY,
    nom     TEXT NOT NULL,
    prix    INTEGER NOT NULL CHECK (prix >= 0),
    cree_le TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO produits (nom, prix) VALUES
    ('Savon de Marseille', 450),
    ('Riz parfumé 5 kg', 4500),
    ('Huile de palme 1 L', 1600),
    ('Poivre de Penja 100 g', 1500),
    ('Café de l''Ouest 250 g', 2000),
    ('Miel blanc d''Oku 500 g', 3500);
