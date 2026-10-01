# Format `.btb` (arbre de comportement)

Arbre de comportement (behavior tree) de l'IA. Il n'y en a qu'**un** dans le jeu :
`data/party_ai.gar` → `NormalAI.btb` (9 084 octets), l'IA des membres de l'équipe.

- Moteur : `App\lib\GzKit\res\BtbRes.h`, `GzBehaviorTreeFactory.cpp` et
  `GzBehaviorTreeNodeCreator.h`.

> ✅ vérifié sur l'unique fichier · 🟡 très probable · ❓ inconnu. Little endian.

---

## 1. Header (0x1c octets) ✅

| Offset | Type | Nom | Valeur |
|---|---|---|---|
| `0x00` | `char[4]` | magic | `"btb "` (avec un espace) |
| `0x04` | `u32` | size | taille du fichier (`0x237c`) |
| `0x08` | `u32` | version | `1` |
| `0x0c` | `u32` | off_nods | `0x1c` |
| `0x10` | `u32` | off_prms | `0x1008` |
| `0x14` | `u32` | off_strt | `0x16c8` |
| `0x18` | `u32` | off_idxt | `0x2318` |

Les offsets sont en **octets**. Chacun pointe vers un **chunk** qui commence par :

```
char tag[4]   u32 size (en-tête du chunk compris)   u32 count   …
```

## 2. Chunks

| Tag | Taille | Count | Contenu | |
|---|---|---|---|---|
| `nods` | `0xfec` | 127 | **nœuds** de l'arbre : 12 octets d'en-tête + 127 × 32 octets | ✅ taille |
| `prms` | `0x6b8` | — | **paramètres** des nœuds : entrées de 8 octets `{u16 type, u16 ?, valeur 4 octets}` | 🟡 |
| `strt` | `0xc50` | 181 | **table de chaînes** (voir ci-dessous) | ✅ |
| `idxt` | `0x64` | 9 | **index** : u32 `0x14`, u32 `0x28`, puis 9 offsets `u16` et des listes d'octets | 🟡 |

### Table de chaînes `strt` ✅

```
+0x00 "strt"   +0x04 u32 size   +0x08 u32 count (181)   +0x0c u32 0
+0x10 u32 offsets_rel (0x18)    +0x14 u32 strings_rel (0x184)
+0x18 u16 offset[count]         offsets relatifs au début des chaînes
+0x184 chaînes terminées par \0
```

Les chaînes sont les noms des nœuds, des conditions et des variables :
`ai_main`, `battle_loop`, `attack_subsequence`, `SearchEnemy`, `Cond_DistToPlayer`,
`IsInAreaWithPlayer`, `WeaponRange`, `abnormal_run_away`…

### Paramètres `prms` 🟡

Exemples d'entrées : `(type 3, 1, 1.0f)` et `(type 4, 2, 0xa2)`. Le type 3 contient un flottant,
le type 4 semble contenir un **index de chaîne** dans `strt` (162 = `0xa2`).

### Nœuds `nods` ❓

127 nœuds de 32 octets. On y voit des petits entiers (type de nœud, index) et des suites de
`0xff` (pas d'enfant / aucun lien). Leur structure reste à décoder.

## 3. Questions ouvertes

- Structure des nœuds : type, liste d'enfants, lien vers `prms` et `strt`.
- Rôle exact de `idxt`.
- Modifier ce fichier permettrait de changer le comportement des compagnons en combat.
