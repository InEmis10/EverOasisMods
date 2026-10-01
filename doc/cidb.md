# Format `.cidb` (collisions) : aperçu

Données de collision des décors et des objets. **Documentation partielle** : seul l'en-tête est
décodé.

- Emplacement : dans les `.gar` de décors (`B13m_3.gar` → `B13_3.cidb`) et d'objets
  (`O331.gar` → `O331_prim.cidb`).
- Volume : 938 fichiers, dont 746 uniques. De 76 octets à 202 Ko (15 Mo au total).
- Moteur : classe `CidbRes` (`App\sources\res\CidbRes.h`), parseur à `0x4af5e8` dans
  `code.bin`. Plusieurs fichiers de collision existent côté moteur : `CollisionManager.cpp`,
  `CollisionModelFactory.cpp`, `CollisionShapeTriangles.cpp`, `CollisionWorld.cpp`.

> ✅ vérifié sur les 746 fichiers ou lu dans le code · 🟡 très probable · ❓ inconnu.

## 1. Deux familles 🟡

| Famille | Fichiers | Contenu probable |
|---|---|---|
| `*_prim.cidb` | 188 | surtout des **formes simples** (boîtes…) : par exemple min (−2.2, −2.2, −2.2) et max (2.2, 2.2, 2.2) |
| autres | 558 | surtout des **maillages** de collision (triangles), probablement avec une structure d'accélération |

Le type réel est donné par l'en-tête, pas par le nom (voir la partie 2).

## 2. Header

| Offset | Type | Nom | Rôle | |
|---|---|---|---|---|
| `0x00` | `char[4]` | magic | `"cidb"` | ✅ |
| `0x04` | `u32` | version | toujours `4` | ✅ |
| `0x08` | `u16` | off_a | toujours `3`, soit l'octet `0x0c` (en mots de 4 octets) | ✅ |
| `0x0a` | `u16` | off_b | toujours `4`, soit l'octet `0x10` | ✅ |
| `0x0c` | `u16[2]` | bloc A | lu par le moteur à `off_a × 4` | ✅ lu |
| `0x10` | `u16[2]` | bloc B | lu par le moteur à `off_b × 4` | ✅ lu |

Le moteur lit le `u16` à `off_a × 4` et celui à `off_b × 4`. Chaque bloc ressemble à une
paire **(nombre d'éléments, offset des données en mots de 4 octets)** 🟡. Par exemple,
`(1, 5)` désigne 1 élément à l'octet `0x14`, et `(2, 6)` désigne 2 éléments à l'octet `0x18`.

Répartition sur les 746 fichiers uniques ✅ :

| Bloc A | Bloc B | Fichiers `_prim` | Autres fichiers |
|---|---|---|---|
| `(1, 5)` | `(0, 0)` | 4 | 535 |
| `(0, 0)` | `(1, 5)` | 177 | 23 |
| `(0, 0)` | `(2, 6)` | 7 | 0 |

Un fichier contient donc soit des éléments de type A (surtout dans les maillages), soit des
éléments de type B (surtout dans les `_prim`). Le nom du fichier ne suffit pas à savoir lequel :
il faut lire l'en-tête.

La suite (sommets, triangles, nœuds) reste à décoder ❓.

## 3. Priorité

Faible pour le modding de données. Utile seulement pour modifier des niveaux (murs
infranchissables, zones accessibles).
