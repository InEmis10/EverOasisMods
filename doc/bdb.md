# Format `.bdb` (base de données)

Tables de données du jeu : objets, ennemis, boutiques, quêtes, bâtiments, compétences, tables
de butin, mouvements… C'est **le format le plus utile pour le modding** de gameplay.

- Emplacement : dans des `.gar`, surtout `data/database.gar` (plus quelques tables de mouvements
  dans les `.gar` des personnages).
- Volume : 164 fichiers, dont 158 uniques. De 232 octets à 146 Ko.
- Moteur : classe `BdbRes` (`App\lib\GzKit\res\BdbRes.h`), parseur à `0x1e0a80` dans
  `code.bin`, gérée par `GzDatabaseMgr`.

> **Niveaux de confiance** : ✅ vérifié sur les 158 fichiers ou lu dans le code du moteur ·
> 🟡 déduit des données, très probable · ❓ inconnu

Toutes les valeurs sont en **little endian**.

---

## 1. Vue d'ensemble

Une `.bdb` est **une seule table** : des lignes de taille fixe, dont les colonnes sont décrites
dans l'en-tête.

```
┌──────────────────────────────┐ 0x00
│ header (0x20 octets)         │
├──────────────────────────────┤ 0x20
│ définitions de colonnes      │  ncols × 4 octets
├──────────────────────────────┤ zone[0]
│ table de correctifs          │  quelles colonnes sont des pointeurs (chaînes…)
├──────────────────────────────┤ zone[1]
│ pool de chaînes              │  chaînes terminées par \0
├──────────────────────────────┤ zone[2]
│ données annexes (blobs)      │  vide sauf dans 4 fichiers
├──────────────────────────────┤ zone[3]
│ index de hachage             │  recherche d'une ligne par id
├──────────────────────────────┤ zone[4]
│ lignes                       │  nrows × row_size
└──────────────────────────────┘ fin du fichier
```

---

## 2. Header (0x00 – 0x1f)

| Offset | Type | Nom | Rôle | |
|---|---|---|---|---|
| `0x00` | `char[4]` | magic | `"bdb\0"` | ✅ |
| `0x04` | `u32` | ❓ | différent pour chaque table (ex. `0x66` pour `item_db`, `0x137` pour `shopstock_database`) : identifiant de table ? | ❓ |
| `0x08` | `u16` | version | toujours `1` | ✅ |
| `0x0a` | `u16` | ncols | nombre de colonnes | ✅ |
| `0x0c` | `u16` | row_size | taille d'une ligne en octets | ✅ |
| `0x0e` | `u16` | nrows | nombre de lignes | ✅ |
| `0x10` | `u16` | nfix | nombre de colonnes « pointeur » (voir 4.1) | ✅ |
| `0x12` | `u16` | hash_size | nombre de cases de l'index de hachage : 32, 64, 128 ou 512 | ✅ |
| `0x14` | `u16[5]` | zone | offsets des zones 0 à 4, **en mots de 4 octets** | ✅ |
| `0x1e` | `u16` | padding | toujours `0` | ✅ |

```
adresse_zone(i) = zone[i] × 4
```

**Règles vérifiées sur les 158 fichiers ✅ :**

```
zone[0] × 4 == 0x20 + ncols × 4                     (les colonnes suivent l'en-tête)
zone[4] × 4 + nrows × row_size == taille_fichier    (les lignes vont jusqu'à la fin)
```

---

## 3. Définitions de colonnes (0x20)

`ncols` entrées de 4 octets :

| Offset | Type | Nom |
|---|---|---|
| `+0x00` | `u16` | type (voir le tableau suivant) |
| `+0x02` | `u16` | offset du champ dans la ligne, en octets |

- La **colonne 0** est toujours de type 5 à l'offset 0 : c'est l'**id** de la ligne, qui sert
  de clé de recherche ✅.
- Les colonnes sont normalement listées dans l'ordre des offsets, mais il vaut mieux toujours
  utiliser l'offset.

### Types de colonnes

La taille de chaque type est vérifiée sur les 158 fichiers ✅. Le sens (signé ou non, etc.)
est déduit des valeurs 🟡.

| Type | Taille | Sens probable | Indices |
|---|---|---|---|
| 0 | 1 | `s8` | contient `0xff` (−1) |
| 1 | 2 | `s16` | contient souvent `0xffff` (−1) |
| 2 | 4 | `s32` | |
| 3 | 1 | `u8` | type le plus fréquent |
| 4 | 2 | `u16` | |
| 5 | 4 | `u32` | ids (colonne 0), prix, quantités |
| 6 | 4 | `f32` | valeurs comme 1.0, 255.0, 15.0, 10.0 |
| 7 | 1 | `bool` | uniquement 0 ou 1 |
| 14 | 4 | **chaîne** | pointeur dans le pool de chaînes (zone 1) ✅ |
| 15 | 4 | **blob** | pointeur dans la zone 2 ✅ |

Les types 8 à 13 n'apparaissent dans aucun fichier.

---

## 4. Zones

### 4.1 Zone 0 : table de correctifs ✅

Au chargement, le moteur remplace la valeur de certaines colonnes par un vrai pointeur. Cette
zone dit lesquelles, et vers où.

```
desc[nfix]          nfix × { u16 colonne, u16 genre }
value[nrows][nfix]  nrows × nfix × u16          (puis complété à un multiple de 4)
```

| Genre | Type de colonne | Le pointeur vaut |
|---|---|---|
| 1 | 14 (chaîne) | `zone[1]×4 + value` : une chaîne du pool |
| 0 | 15 (blob) | `zone[2]×4 + value` : des données dans la zone 2 |

- `value[r][j]` est l'offset **en octets** pour la ligne r et le j-ème descripteur.
- Taille de la zone : `align4(4×nfix + 2×nfix×nrows)`, vérifiée sur les 158 fichiers ✅.
- Dans les 450 colonnes de chaînes du jeu, chaque offset tombe soit sur 0, soit juste après
  un `\0` ✅.

**Pour lire une chaîne, il faut utiliser cette table.** La valeur brute stockée dans la ligne
n'est pas fiable, puisque le moteur l'écrase au chargement.

### 4.2 Zone 1 : pool de chaînes ✅

Chaînes ASCII terminées par `\0`. Le premier octet est `\0`, donc l'offset 0 = chaîne vide.
Exemple (`item_db`) : `\0f000\0f001\0f002\0…` (noms de modèles).

### 4.3 Zone 2 : blobs 🟡

Vide, sauf dans 4 tables de quêtes et de livraisons : `spiritquest_database`,
`quest_property_db`, `shopdeliver_database` et `optionalquest_database`. Elle est référencée
par les colonnes de type 15. Le format du contenu n'est pas encore connu ❓.

### 4.4 Zone 3 : index de hachage

```
bucket[hash_size]   hash_size × { u16 count, u16 first_row }
(+ données supplémentaires dans 87 fichiers ❓)
```

- La somme des `count` des `hash_size` premières entrées est égale à `nrows`, sur les 158
  fichiers ✅.
- **Index simple (71 fichiers)** : les lignes sont triées par case, et l'id de la ligne vérifie
  `id % hash_size == n° de case` ✅. Les lignes de la case b sont
  `first_row … first_row + count − 1`.
- **Autres fichiers (87)** : des entrées supplémentaires suivent les cases, et `first_row` ne
  désigne pas directement une ligne. Probablement une indirection, pas encore comprise ❓.

### 4.5 Zone 4 : lignes ✅

`nrows` lignes de `row_size` octets. Chaque champ se lit à l'offset donné par sa définition de
colonne.

---

## 5. Algorithme de lecture

```python
import struct

TYPES = {0: "<b", 1: "<h", 2: "<i", 3: "<B", 4: "<H", 5: "<I", 6: "<f", 7: "<?",
         14: "<I", 15: "<I"}

def read_bdb(data: bytes):
    assert data[:4] == b"bdb\0"
    ver, ncols, row_size, nrows, nfix, hash_size = struct.unpack_from("<6H", data, 0x08)
    zone = [z * 4 for z in struct.unpack_from("<5H", data, 0x14)]
    cols = [struct.unpack_from("<2H", data, 0x20 + 4 * i) for i in range(ncols)]

    # table de correctifs : (colonne -> (genre, [offset par ligne]))
    fix = {}
    for j in range(nfix):
        col, kind = struct.unpack_from("<2H", data, zone[0] + 4 * j)
        vals = [struct.unpack_from("<H", data, zone[0] + 4 * nfix + 2 * (r * nfix + j))[0]
                for r in range(nrows)]
        fix[col] = (kind, vals)

    def cstr(off):
        end = data.index(b"\0", off)
        return data[off:end].decode("ascii", "replace")

    rows = []
    for r in range(nrows):
        base = zone[4] + r * row_size
        row = []
        for c, (typ, off) in enumerate(cols):
            if c in fix:
                kind, vals = fix[c]
                row.append(cstr(zone[1] + vals[r]) if kind == 1 else ("blob", vals[r]))
            else:
                row.append(struct.unpack_from(TYPES[typ], data, base + off)[0])
        rows.append(row)
    return cols, rows
```

Avec ce lecteur, une table s'exporte facilement en CSV pour la lire dans un tableur.

---

## 6. Pour modifier une `.bdb`

- **Changer une valeur numérique** (prix, PV, dégâts…) : il suffit de réécrire le champ dans la
  ligne. Aucun autre changement n'est nécessaire.
- **Changer une chaîne** : on peut ajouter la nouvelle chaîne à la fin du pool, mettre à jour
  la valeur dans la table de correctifs, puis décaler les zones 2, 3 et 4 (et leurs offsets
  dans l'en-tête, en mots de 4 octets).
- **Ajouter ou supprimer une ligne** : il faut aussi agrandir la table de correctifs et
  **reconstruire l'index de hachage**, car les lignes sont triées par case. Ce n'est faisable
  sans risque que pour les 71 tables à index simple, tant que la zone 3 des autres n'est pas
  comprise.

---

## 7. Tables présentes dans le jeu

Quelques tables notables (158 au total) :

| Domaine | Fichiers |
|---|---|
| Objets | `item_db`, `item_location_db`, `mix_table_db`, `multi_item_model_database` |
| Boutiques | `shopitem_database`, `shopstock_database`, `shopsales_ratio_database`, `shopdeliver_database`, `bazaar_db`, `peddleritem_database`, `peddlertrade_database` |
| Ennemis et combat | `enemy_database`, `enemy_level_database`, `attack_db`, `attack_enemy_db`, `attack_resist_db`, `damage_table_db`, `combo_list_db`, `skill2_database` |
| Butin | `drop_table_database`, `drop_table_bgobj_database`, `drop_table_bgobj_roomrank` |
| Personnages | `character_property`, `chara_exp_db`, `spiritlevel_database`, `face_param_database` |
| Quêtes | `quest_property_db`, `optionalquest_database`, `spiritquest_database`, `encounterquest_database`, `mercenary_quest_*`, `sub_mission_db` |
| Oasis et ville | `building_db`, `townroad_database`, `visitor_*_data_db`, `vender_assign_data`, `oasis_chaos_database`, `grass_*` |
| Donjons et cartes | `dungeon_property`, `dungeon_structure`, `dungeon_parts`, `door_db`, `switch_db`, `portal_database`, `zone_tbl`, `scenetbl_db`, `worldmap_zone_database` |
| Mouvements | `*_motion_db` (un par type de personnage ou d'ennemi) |
| Divers | `achievement_database`, `staff_roll_data`, `soundeff_db`, `soundenv_db`, `sceneenv_db` |

**Les noms de colonnes ne sont pas stockés dans le fichier** : il faut deviner le rôle de
chaque colonne à partir des valeurs (ou du code du jeu).

---

## 8. Questions ouvertes

- Rôle du `u32` à `0x04`.
- Structure de la zone 3 dans les 87 fichiers à index étendu.
- Format des blobs de la zone 2 (colonnes de type 15).
- Signification des colonnes de chaque table : c'est le plus gros du travail, table par table.
