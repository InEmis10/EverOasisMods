# Format `.colb` (palette de couleurs d'environnement)

Liste de couleurs utilisée pour le ciel et les nuages (dégradés).

- Emplacement : `data/environment.gar`.
- Volume : 24 fichiers uniques, de 212 à 296 octets.
- Noms : `t00_{cl,dk,fn}_{kumo_a0..a3, tenkyu_0..3}.colb`.
  - `kumo` = nuage, `tenkyu` = voûte céleste (en japonais).
  - Les préfixes `cl` / `dk` / `fn` désignent probablement des ambiances différentes
    (`dk` = sombre ?) 🟡.
  - Les suffixes `0` à `3` sont des variantes, peut-être selon le moment de la journée 🟡.

> ✅ vérifié sur les 24 fichiers · 🟡 très probable · ❓ inconnu. Little endian.

---

## 1. Structure

| Offset | Type | Nom | Rôle | |
|---|---|---|---|---|
| `0x00` | `char[4]` | magic | `"colb"` | ✅ |
| `0x04` | `u32` | size | taille totale du fichier | ✅ |
| `0x08` | `u32` | count | nombre de couleurs (49, 65 ou 70) | ✅ |
| `0x0c` | `u32` | padding | toujours 0 | ✅ |
| `0x10` | `u8[4] × count` | couleurs | une couleur par entrée | ✅ |

**Règle ✅** : `0x10 + count × 4 == taille du fichier`.

## 2. Couleur (4 octets) 🟡

Ordre probable : **R, G, B, A**. Le 4ᵉ octet vaut souvent `0xff` (opaque).
Exemple : `bd 71 73 ff` donne R=189, G=113, B=115, A=255.

Les couleurs se suivent de façon progressive : chaque fichier est vraisemblablement un dégradé
échantillonné (de l'horizon au zénith, ou selon l'heure).

## 3. Lecture

```python
import struct

def read_colb(data: bytes):
    assert data[:4] == b"colb"
    size, count, _ = struct.unpack_from("<3I", data, 4)
    return [tuple(data[0x10 + 4 * i: 0x14 + 4 * i]) for i in range(count)]   # (R, G, B, A)
```

C'est un format idéal pour un premier mod visible : changer la couleur du ciel.
