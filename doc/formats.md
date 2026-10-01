# Formats de fichiers : index

Inventaire de `workspace/base/extracted/` (contenu des 4 067 `.gar` du romfs) : **21 extensions**,
32 950 fichiers.

Le magic est la signature des 4 premiers octets du fichier. Statut de la documentation :
**✅ doc** = structure documentée · **🟡 partiel** = en-tête seulement · **— hors périmètre**.

## Données (gameplay, niveaux, configuration)

| Ext. | Fichiers | Taille totale | Magic | Rôle | Statut |
|---|---|---|---|---|---|
| `.bdb` | 164 | 1,7 Mo | `bdb\0` | **Bases de données** (objets, ennemis, boutiques, quêtes…) | ✅ [bdb.md](bdb.md) |
| `.vlb` | 336 | 1,7 Mo | `vlb\0` | **Disposition des cartes** (zones, tag points, placements) | ✅ [vlb.md](vlb.md) |
| `.rteb` | 106 | 0,15 Mo | `rteb` | **Routes** (chemins nommés de points) | ✅ [rteb.md](rteb.md) |
| `.acb` | 1 (+1 hors `.gar`) | < 1 Ko | aucun | **Configuration** (arbre à clés hachées) | ✅ [acb.md](acb.md) |
| `.colb` | 24 | 0,01 Mo | `colb` | **Palettes** du ciel et des nuages | ✅ [colb.md](colb.md) |
| `.btb` | 1 | 9 Ko | `btb ` | **Arbre de comportement** de l'IA de l'équipe | 🟡 [btb.md](btb.md) |
| `.cidb` | 938 | 15,4 Mo | `cidb` | **Collisions** (formes simples, maillages) | 🟡 [cidb.md](cidb.md) |
| `.gsb` | 310 | 6 Mo | `FA FA 52 49` | **Scripts** Squirrel compilés | outils existants : `tool/decompile`, `tool/sqc` |

## Interface (à documenter plus tard)

| Ext. | Fichiers | Magic | Rôle probable |
|---|---|---|---|
| `.ibb` | 387 | `ibb\0` | mise en page d'écrans d'interface (`IbbRes`, GzKit UIKit) |
| `.icab` | 561 | `icab` | animations d'interface (`IcabRes`) |
| `.itpb` | 333 | `itpb` | motifs d'UV / changement d'image d'interface (`ItpbRes`) |
| `.amb` | 119 | aucun | masques 1 bit (zones cliquables, noms de donjons dans les polices) |

## Hors périmètre (graphismes, animations)

| Ext. | Fichiers | Magic | Rôle |
|---|---|---|---|
| `.cmb` | 2 880 | `cmb ` | modèle 3D |
| `.ctxb` | 11 940 | `ctxb` | texture |
| `.csab` | 12 121 | `csab` | animation de squelette |
| `.cmab` | 1 775 | `cmab` | animation de matériau |
| `.cmtb` | 65 | `cmtb` | table de matériaux (chunk `mats`) |
| `.cstb` | 475 | `cstb` | vignettes / modèles précalculés (chunk `mats`) |
| `.ptcl` | 112 | `SPBD` | effets de particules (format Nintendo) |
| `.ccb` | 264 | `ccb\0` | animation de caméra (chunk `caad`) |
| `.tlab` | 38 | `TPAB` | timeline d'animation (`TlabRes`) |

## Fichiers hors `.gar` dans le romfs

`romfs/data/` contient aussi, en dehors des `.gar` : `agora_config.acb`, et les dossiers
`async/`, `Region_US/` (contenu localisé), `scripts/` et `sound/`.

## Conventions communes

- **Little endian** partout.
- **Offsets en mots de 4 octets** (valeur × 4) dans `vlb`, `bdb`, `rteb` et `cidb`. En revanche,
  `acb` et `btb` utilisent des offsets en octets.
- Les formats GzKit (`bdb`, `btb`, `ibb`, `icab`, `itpb`) et les formats propres au jeu (`vlb`,
  `rteb`, `acb`, `cidb`) sont chargés par des classes `XxxRes` du moteur. Le parseur de chacune
  est indiqué dans sa doc, ce qui permet d'aller vérifier une hypothèse dans le code.
