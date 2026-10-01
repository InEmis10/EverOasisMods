# Format `.rteb` (routes)

Chemins nommés composés de points : trajets de PNJ, de créatures ou d'objets mobiles
(`route0`, `paraflower01_up`, `paraflower01_down`…).

- Emplacement : dans des `.gar` (`town_common.gar`, `field_*.gar`, `Area_*.gar`…).
- Volume : 106 fichiers, dont 52 uniques. De 179 octets à 31 Ko.
- Moteur : classe `RtebRes` (`App\sources\res\RtebRes.h`), parseur à `0x4b9330` dans `code.bin`.

> ✅ vérifié sur les 52 fichiers ou lu dans le code · 🟡 très probable · ❓ inconnu
> Little endian partout.

---

## 1. Vue d'ensemble

```
┌──────────────────────────────┐ 0x00
│ header                       │
├──────────────────────────────┤ 0x14
│ route_offset[nroutes]        │  u16, en mots de 4 octets
├──────────────────────────────┤ points_offset × 4
│ points  (npoints × 32 o)     │
├──────────────────────────────┤ route_offset[0] × 4
│ routes  (taille variable)    │
├──────────────────────────────┤ names_offset × 4
│ table des noms de routes     │
└──────────────────────────────┘ fin du fichier
```

---

## 2. Header

| Offset | Type | Nom | Rôle | |
|---|---|---|---|---|
| `0x00` | `char[4]` | magic | `"rteb"` | ✅ |
| `0x04` | `u16` | version | toujours `6` | ✅ |
| `0x06` | `u16` | npoints | nombre total de points | ✅ |
| `0x08` | `u16` | nroutes | nombre de routes | ✅ |
| `0x0a` | `u16` | nroutes (copie) | toujours égal à `0x08` | ✅ |
| `0x0c` | `u16` | names_offset | table des noms, en mots de 4 octets | ✅ |
| `0x0e` | `u16` | points_offset | début des points, en mots de 4 octets (lu par le moteur) | ✅ |
| `0x10` | `u32` | ❓ | 0 dans les exemples | ❓ |
| `0x14` | `u16[nroutes]` | route_offset | début de chaque route, en mots de 4 octets | ✅ |

**Règle vérifiée sur les 52 fichiers ✅ :**

```
points_offset × 4 + npoints × 32 == route_offset[0] × 4
```

---

## 3. Point (32 octets)

| Offset | Type | Nom | | |
|---|---|---|---|---|
| `+0x00` | `u16` | index | 0, 1, 2… (numéro du point) | 🟡 |
| `+0x02` | `u16` | ❓ | 0 ou 1 selon le fichier | ❓ |
| `+0x04` | `f32[3]` | position | x, y, z | ✅ flottants |
| `+0x10` | `f32[3]` | taille / rayon | souvent (1, 1, 1) ou (0.5, 0.5, 0.5) | 🟡 |
| `+0x1c` | `u32` | ❓ | 0 dans les exemples | ❓ |

---

## 4. Route (taille variable)

| Offset | Type | Nom | | |
|---|---|---|---|---|
| `+0x00` | `u32` | hash | hash du nom ? (ni CRC32 ni FNV-1/1a) | ❓ |
| `+0x04` | `u16` | ❓ | égal au nombre de points de la route dans les exemples | 🟡 |
| `+0x06` | `u16` | ❓ | | ❓ |
| `+0x08` | … | liens | listes d'indices de points ; `0xff` semble marquer une fin ou une absence | ❓ |

La taille d'une route se déduit de l'offset suivant (route suivante, ou table des noms pour la
dernière).

---

## 5. Table des noms ✅

À `names_offset × 4` :

```
u32 name_offset[nroutes]     relatif à la fin de ce tableau
char noms[]                  chaînes terminées par \0, dans l'ordre des routes
```

Vérifié sur les 52 fichiers ✅ : le dernier nom se termine exactement à la fin du fichier.

---

## 6. Lecture

```python
import struct

def read_rteb(data: bytes):
    assert data[:4] == b"rteb"
    ver, npoints, nroutes, _, names_off, points_off = struct.unpack_from("<6H", data, 0x04)
    route_offs = [o * 4 for o in struct.unpack_from(f"<{nroutes}H", data, 0x14)]

    points = []
    for i in range(npoints):
        idx, unk, x, y, z, sx, sy, sz, _ = struct.unpack_from("<HH3f3fI", data, points_off * 4 + 32 * i)
        points.append(dict(index=idx, unk=unk, pos=(x, y, z), size=(sx, sy, sz)))

    base = names_off * 4
    offs = struct.unpack_from(f"<{nroutes}I", data, base)
    start = base + 4 * nroutes
    names = [data[start + o:data.index(b"\0", start + o)].decode() for o in offs]

    ends = route_offs[1:] + [base]
    routes = [dict(name=n, hash=struct.unpack_from("<I", data, a)[0], raw=data[a:b])
              for n, a, b in zip(names, route_offs, ends)]
    return points, routes
```

---

## 7. Questions ouvertes

- Structure exacte des routes : comment les points sont reliés, boucles, sens.
- Algorithme du hash des routes.
- Champs `+0x02` et `+0x1c` des points, et `u32` à `0x10` de l'en-tête.
