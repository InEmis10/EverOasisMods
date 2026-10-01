# Extensions de fichiers d'Ever Oasis

Liste des extensions réellement présentes dans le jeu, avec leur rôle.
Structure détaillée des formats de données : voir [`doc/formats.md`](doc/formats.md).

## Dans le romfs (hors archives)

| Extension | Utilité |
|---|---|
| `.gar` | Archive : regroupe les autres fichiers (4 067 archives, presque tout le contenu du jeu) |
| `.gmsg` | Tous les textes du jeu pour une langue : dialogues, noms et descriptions (`English`, `French`, `Spanish`) |
| `.gzf` | Police d'écriture du jeu |
| `.bcsar` | Archive sonore principale : effets sonores et banques d'instruments (format Nintendo) |
| `.bcstm` | Musiques, lues en streaming (format Nintendo) |
| `.shbin` | Shaders compilés pour le GPU de la 3DS |
| `.acb` | Configuration générale du jeu (`agora_config.acb`) |

## Dans les archives `.gar`

### Données de jeu

| Extension | Utilité |
|---|---|
| `.bdb` | Bases de données : objets, ennemis, boutiques, quêtes, butin, bâtiments, compétences… |
| `.gsb` | Scripts compilés (Squirrel) : logique des scènes, PNJ, événements |
| `.vlb` | Disposition d'une carte : zones, points de repère, placements |
| `.rteb` | Routes : chemins suivis par les PNJ et les objets mobiles |
| `.cidb` | Collisions des décors et des objets |
| `.btb` | Arbre de comportement de l'IA des membres de l'équipe |
| `.acb` | Configuration (paramètres à clés) |
| `.colb` | Palettes de couleurs du ciel et des nuages |

### Graphismes

| Extension | Utilité |
|---|---|
| `.cmb` | Modèle 3D : maillages, matériaux, squelette |
| `.ctxb` | Texture |
| `.cmtb` | Table de matériaux |
| `.cstb` | Vignettes et modèles précalculés |
| `.ptcl` | Effets de particules (format Nintendo) |

### Animations

| Extension | Utilité |
|---|---|
| `.csab` | Animation de squelette (personnages, ennemis) |
| `.cmab` | Animation de matériau (textures qui défilent, couleurs qui changent) |
| `.ccb` | Animation de caméra (cinématiques) |
| `.tlab` | Timeline d'animation (événements synchronisés) |

### Interface

| Extension | Utilité |
|---|---|
| `.ibb` | Mise en page d'un écran d'interface (menus, HUD) |
| `.icab` | Animation d'interface |
| `.itpb` | Changement d'image ou de motif dans l'interface |
| `.amb` | Masque de forme (zones cliquables, découpe de texte) |

## Dans l'exefs

| Fichier | Utilité |
|---|---|
| `code.bin` | Code exécutable du jeu (le moteur) |
| `icon.icn` | Icône et titre affichés dans le menu de la 3DS |
| `banner.bnr` | Bannière animée et son du menu de la 3DS |
