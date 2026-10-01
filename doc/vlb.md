# Format `.vlb` (layout de carte)

Fichier binaire qui décrit la disposition d'une carte : zones, points de repère (tag points),
placements. Il y en a un par ville, donjon ou salle de test, parfois avec des variantes selon
l'avancement (`town_e30.vlb`, `town_e30_chapter4.vlb`, `town_e30_allshop.vlb`…).

- Emplacement : toujours **dans des `.gar`** (aucun `.vlb` isolé dans le romfs).
- Volume : 336 fichiers, dont 199 uniques (les autres sont des doublons entre archives).
- Taille : de 168 octets à environ 45 Ko.
- Moteur : classe `VlbRes` (`App\sources\res\VlbRes.h`), parseur à `0x4af460` dans `code.bin`.

> **Niveaux de confiance** utilisés dans ce document :
> ✅ vérifié sur les 199 fichiers ou lu dans le code du moteur ·
> 🟡 déduit des données, très probable · ❓ inconnu

Toutes les valeurs sont en **little endian**. Les flottants sont des `float32` IEEE 754.

---

## 1. Vue d'ensemble

```
┌──────────────────────────────┐ 0x00
│ magic + version              │
├──────────────────────────────┤ 0x08
│ count[1..27]   (27 × u16)    │  nombre d'enregistrements par section
├──────────────────────────────┤ 0x3e
│ offset[0..27]  (28 × u16)    │  position de chaque section, en mots de 4 octets
├──────────────────────────────┤ 0x76
│ padding (u16 = 0)            │
├──────────────────────────────┤ 0x78
│ sections (body)              │  pas forcément dans l'ordre de la table
└──────────────────────────────┘
```

Le fichier est un **conteneur de 28 sections**. L'en-tête ne contient que des compteurs et des
offsets : le parseur du moteur se contente de mémoriser un pointeur vers chaque section ✅.

---

## 2. Header (0x00 – 0x77)

| Offset | Type | Nom | Valeur / rôle | |
|---|---|---|---|---|
| `0x00` | `char[4]` | magic | `"vlb\0"` | ✅ |
| `0x04` | `u32` | version | toujours `0x11` (17) | ✅ |
| `0x08` | `u16[27]` | count | `count[k]` à `0x08 + 2×(k−1)`, pour k = 1..27 | ✅ |
| `0x3e` | `u16[28]` | offset | `offset[k]` à `0x3e + 2×k`, pour k = 0..27 | ✅ |
| `0x76` | `u16` | padding | toujours `0` | ✅ |

**Calcul de l'adresse d'une section :**

```
adresse_section(k) = offset[k] × 4        (en octets depuis le début du fichier)
```

- La section 0 n'a **pas** de compteur.
- Une section dont le compteur vaut 0 est vide : son offset est alors égal à celui d'une autre
  section.

---

## 3. Les deux variantes

On distingue les deux variantes avec `offset[0]` ✅.

### 3.1 Variante complète : `offset[0] ≠ 0` (144 fichiers)

C'est le cas normal : toutes les sections sont présentes. On la trouve dans `town_common.gar`,
`dungeon_common.gar`, les `.gar` de donjons (`FD_*`, `Underpass_*`…) et les `BattleTest*`.

- `offset[0]` vaut toujours `0x1e`, c'est-à-dire que la section 0 commence à `0x78` ✅.
- Règle de taille, vérifiée sur les 144 fichiers ✅ :
  ```
  taille_fichier == offset[27] × 4 + count[27] × 20
  ```
  La section 27 est physiquement la dernière, avec des enregistrements de 20 octets.

### 3.2 Variante « tag » : `offset[0] == 0` (55 fichiers, tous dans `common_tag.gar`)

Le fichier ne contient **que la section 4** (les tag points) ✅.

- `offset[k] == k` pour toutes les sections, sauf `offset[4] == 0x1e`. Ces petites valeurs ne
  sont pas des offsets : elles pointeraient dans l'en-tête. Il faut les ignorer.
- Les compteurs des autres sections peuvent être non nuls (probablement copiés depuis la
  version complète de la carte), mais **leurs données ne sont pas dans le fichier**.
- Règle de taille, vérifiée sur les 55 fichiers ✅ :
  ```
  taille_fichier == 0x78 + count[4] × 16
  ```

---

## 4. Body : les 28 sections

### 4.1 Ordre physique

Les sections ne sont pas rangées dans l'ordre de leur index. L'ordre le plus fréquent est :

```
0 1 2 3 4 5 6 18 7 8 19 9 10 11 12 17 13 14 15 16 20 21 22 23 24 25 26 27
```

Il existe 4 ordres différents dans le jeu. Pour connaître la fin d'une section, **ne pas
supposer que la section k+1 suit la section k** : il faut trier les offsets, ou utiliser
`count × taille_enregistrement` quand la taille est fixe.

### 4.2 Tableau des sections (variante complète)

| k | Champ count | Champ offset | Taille d'un enregistrement | Contenu |
|---|---|---|---|---|
| 0 | — | `0x3e` | — (bloc : 12 octets d'en-tête + données) | 🟡 infos générales de la carte (voir 5.3) |
| 1 | `0x08` | `0x40` | **16** ✅ | ❓ |
| 2 | `0x0a` | `0x42` | **56** ✅ | 🟡 zones / volumes (voir 5.2) |
| 3 | `0x0c` | `0x44` | — (compteur toujours 0) | ❓ inutilisée |
| 4 | `0x0e` | `0x46` | **16** ✅ | 🟡 tag points (voir 5.1) |
| 5 | `0x10` | `0x48` | **20** ✅ | ❓ |
| 6 | `0x12` | `0x4a` | variable (~48) | 🟡 placements (id + position + paramètres) |
| 7 | `0x14` | `0x4c` | **8** ✅ | ❓ |
| 8 | `0x16` | `0x4e` | variable (12 à 36) | ❓ |
| 9 | `0x18` | `0x50` | **4** ✅ | ❓ |
| 10 | `0x1a` | `0x52` | — (bloc de 12 octets) | ❓ |
| 11 | `0x1c` | `0x54` | **20** ✅ | ❓ |
| 12 | `0x1e` | `0x56` | variable (~48–52) | ❓ |
| 13 | `0x20` | `0x58` | **24** ✅ | ❓ |
| 14 | `0x22` | `0x5a` | **12** ✅ | ❓ |
| 15 | `0x24` | `0x5c` | **4** ✅ | ❓ |
| 16 | `0x26` | `0x5e` | **6** + alignement sur 4 🟡 | ❓ |
| 17 | `0x28` | `0x60` | — (compteur toujours 0, données présentes) | 🟡 données annexes de la section 12 |
| 18 | `0x2a` | `0x62` | — (compteur toujours 0, données présentes) | 🟡 données annexes de la section 6 |
| 19 | `0x2c` | `0x64` | — (compteur toujours 0, données présentes) | 🟡 données annexes de la section 8 |
| 20 | `0x2e` | `0x66` | — (bloc de 4 octets) | ❓ |
| 21 | `0x30` | `0x68` | variable (8 à 16) | ❓ |
| 22 | `0x32` | `0x6a` | — (compteur toujours 0) | ❓ |
| 23 | `0x34` | `0x6c` | **20** ✅ | ❓ |
| 24 | `0x36` | `0x6e` | **24** ✅ | ❓ |
| 25 | `0x38` | `0x70` | **20** ✅ | ❓ |
| 26 | `0x3a` | `0x72` | **2** + alignement sur 4 🟡 | ❓ |
| 27 | `0x3c` | `0x74` | **20** ✅ | ❓ (toujours la dernière section) |

**Remarques :**

- **« ✅ » dans la colonne taille** : `taille_section / count` donne exactement cette valeur dans
  tous les fichiers où la section est présente.
- **« variable »** : le compteur donne le nombre d'éléments, mais les éléments n'ont pas tous la
  même taille. Il y a probablement des sous-listes.
- **Sections 17, 18 et 19** : elles sont toujours placées juste après les sections 12, 6 et 8
  dans l'ordre physique. Ce sont probablement leurs données de longueur variable.

---

## 5. Enregistrements connus

### 5.1 Section 4 : tag point (16 octets)

Points de repère nommés par un id, utilisés par les scripts (`get_tag_point`,
`get_tag_direction`, `set_actor_pos_by_tagpoint`…).

| Offset | Type | Nom | Notes | |
|---|---|---|---|---|
| `+0x00` | `u16` | id | ex. 200, 300, 301, 400, 1000… | ✅ entier |
| `+0x02` | `u16` | direction | angle sur 16 bits (65536 = 360°) | 🟡 70 % des valeurs sont des multiples exacts de 2,5° |
| `+0x04` | `f32` | x | de −1787 à 2310 | ✅ flottant |
| `+0x08` | `f32` | y | hauteur, de −750 à 251 | ✅ flottant |
| `+0x0c` | `f32` | z | de −3099 à 2373 | ✅ flottant |

Exemple (`town_e30.vlb`) : `2c 01 b7 f0 | 00 c0 1e 44 | …`, soit id = 300, direction = 0xf0b7,
position (635.0, −5.93, 156.0).

### 5.2 Section 2 : zone / volume (56 octets)

| Offset | Type | Nom | Notes | |
|---|---|---|---|---|
| `+0x00` | `u32` | id | ex. 202, 250, 400 | ✅ entier, jamais flottant |
| `+0x04` | `u32` | ❓ | petit entier ou champ de bits | 🟡 |
| `+0x08` | `u32` | ❓ | petit entier | 🟡 |
| `+0x0c` | `f32[3]` | position | centre ou coin x, y, z | 🟡 |
| `+0x18` | `f32[3]` | dimensions | largeur, hauteur, profondeur (ex. 20, 40, 100) | 🟡 |
| `+0x24` | `f32[3]` | 2ᵉ position | optionnelle (souvent 0) : destination, sortie ? | ❓ |
| `+0x30` | `f32` | angle ? | valeurs typiques 0, 90, 180 (en degrés) | ❓ |
| `+0x34` | `u32` | ❓ | presque toujours 0 | ❓ |

### 5.3 Section 0 : bloc d'en-tête de la carte

- Le moteur garde deux pointeurs : un vers le début de la section, un vers **début + 12** ✅.
  C'est donc un en-tête de 12 octets suivi de données.
- Exemple : `28 00 14 00 | 00 00 00 00 | 00 00 70 41`, soit deux `u16` (40, 20), puis 0, puis
  le flottant 15.0. 🟡 Ça pourrait être une grille (40 × 20 cases de 15 unités : voir
  `Town\TownGrid.cpp` dans les sources du moteur).

---

## 6. Algorithme de lecture

```python
import struct

def read_vlb(data: bytes):
    assert data[:4] == b"vlb\0"
    version, = struct.unpack_from("<I", data, 0x04)        # 0x11
    count  = [None] + list(struct.unpack_from("<27H", data, 0x08))  # count[1..27]
    offset = [o * 4 for o in struct.unpack_from("<28H", data, 0x3e)]

    tag_only = offset[0] == 0
    sections = {}
    for k in range(28):
        if tag_only and k != 4:
            continue                       # offsets factices dans la variante "tag"
        start = offset[k]
        # fin = prochain offset strictement supérieur (ordre physique), ou fin du fichier
        end = min([o for o in offset if o > start] + [len(data)])
        if k > 0 and count[k] == 0:
            end = start                    # section vide
        sections[k] = data[start:end]
    return version, count, sections

def tag_points(count, sections):
    s = sections[4]
    for i in range(count[4]):
        id_, direction, x, y, z = struct.unpack_from("<HH3f", s, i * 16)
        yield dict(id=id_, direction=direction * 360 / 65536, pos=(x, y, z))
```

---

## 7. Pour réécrire un `.vlb`

- Garder la version `0x11`.
- Les offsets sont en **mots de 4 octets** : chaque section doit commencer à une adresse
  multiple de 4. Les sections de taille non multiple de 4 (16 et 26) sont complétées par des
  zéros.
- Ajouter un enregistrement dans une section décale toutes les sections placées **après elle
  physiquement** : il faut recalculer tous les offsets concernés.
- Pour vérifier une réécriture : relire le fichier produit, puis contrôler les règles de taille
  de la partie 3.

---

## 8. Questions ouvertes

- Rôle des sections 1, 3, 5, 7–15, 20–27.
- Structure exacte des sections variables (6, 8, 12, 16, 21, 26) et de leurs données annexes
  (17, 18, 19).
- Sens des champs `+0x04` / `+0x08` / `+0x24` / `+0x30` de la section 2.
- Comment le moteur charge la variante « tag » (même classe `VlbRes` ? fusion avec la carte
  complète ?).

**Méthode conseillée** : modifier une seule valeur (par exemple la position d'un tag point),
repacker le `.gar`, puis observer le résultat en jeu sur l'émulateur.
