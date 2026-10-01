# Format `.acb` (configuration)

Petit arbre de paramètres dont les clés sont hachées. Il n'en existe que deux :

| Fichier | Taille |
|---|---|
| `romfs/data/agora_config.acb` (hors `.gar`) | 328 octets |
| `data/town_common.gar` → `config.acb` | 400 octets |

- Moteur : classe `AcbRes` (`App\sources\res\AcbRes.h`), parseur à `0x4a79c4` dans `code.bin`.

> ✅ vérifié sur les 2 fichiers ou lu dans le code · 🟡 très probable · ❓ inconnu
> Little endian partout.

---

## 1. Header (16 octets) ✅

| Offset | Type | Nom | Rôle |
|---|---|---|---|
| `0x00` | `u32` | count | nombre d'entrées (7 dans les deux fichiers) |
| `0x04` | `u32` | entries_offset | début des entrées, en **octets** (`0x10`) |
| `0x08` | `u32` | children_offset | début des listes d'enfants, en octets |
| `0x0c` | `u32` | values_offset | début des valeurs, en octets |

Le moteur transforme directement ces trois offsets en pointeurs ✅. Il n'y a **pas** de magic.

---

## 2. Entrée (24 octets) ✅

| Offset | Type | Nom | Rôle |
|---|---|---|---|
| `+0x00` | `u32` | key_hash | nom de la clé, haché (algorithme inconnu ❓) |
| `+0x04` | `s32` | parent | index de l'entrée parente, `−1` pour la racine |
| `+0x08` | `u32` | nchildren | nombre d'enfants |
| `+0x0c` | `u32` | nvalues | nombre de valeurs |
| `+0x10` | `u32` | children_ptr | position (en octets) de la liste des enfants : `nchildren × u32` (index d'entrées) |
| `+0x14` | `u32` | values_ptr | position (en octets) des valeurs : `nvalues × 4 octets` |

- Vérifié ✅ : `children_offset − entries_offset == count × 24`.
- Dans les deux fichiers, l'entrée 0 est la racine et les entrées 1 à 6 sont ses enfants.

---

## 3. Valeurs 🟡

Chaque valeur occupe 4 octets, mais **son type n'est pas stocké** : c'est le code du jeu qui
sait, pour chaque clé, s'il faut la lire comme un entier ou un flottant.

Exemples :

- `config.acb`, entrée 5 : 30 entiers `5000, 5001, 5020, 5021, 5200…`. Ce sont des ids d'objets
  (on les retrouve dans `item_db.bdb`).
- `agora_config.acb`, entrée 2 : `0x40833333`, soit le flottant **4.1**.
- `agora_config.acb`, entrée 5 : `0x41000000`, soit le flottant **8.0**.

Pour repérer un flottant : une valeur entière énorme (supérieure à `0x3c000000` environ) est
probablement un flottant.

---

## 4. Lecture

```python
import struct

def read_acb(data: bytes):
    count, entries_off, _, _ = struct.unpack_from("<4I", data, 0)
    entries = []
    for i in range(count):
        key, parent, nchild, nval, coff, voff = struct.unpack_from("<IiIIII", data, entries_off + 24 * i)
        children = list(struct.unpack_from(f"<{nchild}I", data, coff)) if nchild else []
        raw = [data[voff + 4 * k: voff + 4 * k + 4] for k in range(nval)]
        entries.append(dict(key=hex(key), parent=parent, children=children,
                            as_int=[struct.unpack("<I", r)[0] for r in raw],
                            as_float=[struct.unpack("<f", r)[0] for r in raw]))
    return entries
```

---

## 5. Questions ouvertes

- Algorithme de hachage des clés (pour retrouver leurs noms).
- Signification de chaque paramètre. La méthode : modifier une valeur et observer en jeu.
