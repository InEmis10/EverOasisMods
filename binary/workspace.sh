#!/usr/bin/env bash
# Crée (ou complète) une workspace de modding Ever Oasis.
#
#   workspace/
#   ├── workspace.json   marqueur + infos (version du format, title ID)
#   ├── base/            jeu d'origine extrait : ncchheader.bin, exh.bin, exefs/, romfs/,
#   │                    extracted/ (GAR ouverts)
#   ├── mods/<id>/       mods en développement : mod.json, scripts/, romfs/, code/
#   ├── deps/<id>/       mods bibliothèques tierces (même format que mods/)
#   ├── modified/        généré par le build : uniquement les fichiers modifiés
#   └── output/          généré par le build : paquets distribuables
#
# Relançable sans risque : ce qui existe déjà n'est jamais écrasé.
# Les dépendances manquantes ne sont installées qu'avec l'accord de l'utilisateur.
set -euo pipefail

TOOL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TITLE_ID="00040000001a4800"
FORMAT_VERSION=1

T3DS_URL="https://github.com/dnasdw/3dstool/releases/download/v1.2.6/3dstool_linux_x86_64.tar.gz"
T3DS_SHA256="d42e3de7766ee552b3609ac5acb7ad3f07209dd91bc45a21d3fc2b049790ede2"

usage() {
    cat >&2 <<EOF
usage: $0 [-o chemin] [-n id_du_mod] [-g jeu] [--reextract] [-y]

  -o, --output CHEMIN   dossier où créer workspace/ (défaut : dossier courant)
  -n, --name ID         crée le mod mods/ID (minuscules, chiffres, - et _)
  -g, --game JEU        remplit base/ depuis le jeu : .3ds/.cci, .cxi,
                        ou dossier déjà extrait (contenant exh.bin, exefs/, romfs/)
      --reextract       réextrait base/ même s'il est déjà rempli
  -y, --yes             installe les dépendances manquantes sans demander
  -h, --help            affiche cette aide

Variable d'environnement : THREEDSTOOL=chemin/vers/3dstool
EOF
    exit "${1:-1}"
}

die()  { echo "erreur : $*" >&2; exit 1; }
info() { echo "==> $*"; }
warn() { echo "attention : $*" >&2; }

# Question oui/non sur le terminal ; non par défaut, et non si aucun terminal.
ask() {
    [ "$YES" -eq 1 ] && return 0
    local ans=""
    { printf '%s [o/N] ' "$1" >/dev/tty; read -r ans </dev/tty; } 2>/dev/null || return 1
    [[ "$ans" =~ ^[oOyY] ]]
}

# ---------------------------------------------------------------- arguments
OUT="."
MOD_ID=""
GAME=""
REEXTRACT=0
YES=0
while [ $# -gt 0 ]; do
    case "$1" in
        -o|--output) [ $# -ge 2 ] || usage; OUT="$2"; shift 2 ;;
        -n|--name)   [ $# -ge 2 ] || usage; MOD_ID="$2"; shift 2 ;;
        -g|--game)   [ $# -ge 2 ] || usage; GAME="$2"; shift 2 ;;
        --reextract) REEXTRACT=1; shift ;;
        -y|--yes)    YES=1; shift ;;
        -h|--help)   usage 0 ;;
        *) echo "argument inconnu : $1" >&2; usage ;;
    esac
done

if [ -n "$MOD_ID" ] && ! [[ "$MOD_ID" =~ ^[a-z0-9][a-z0-9_-]{0,63}$ ]]; then
    die "id de mod invalide : '$MOD_ID' (attendu : minuscules, chiffres, - et _, 64 caractères max)"
fi
if [ -n "$GAME" ]; then
    [ -e "$GAME" ] || die "jeu introuvable : $GAME"
    if [ -f "$GAME" ]; then
        case "${GAME,,}" in
            *.3ds|*.cci|*.cxi) ;;
            *) die "format non reconnu : $GAME (.3ds, .cci, .cxi ou dossier)" ;;
        esac
    fi
    GAME="$(cd "$(dirname "$GAME")" && pwd)/$(basename "$GAME")"
fi
if [ -e "$OUT" ] && [ ! -d "$OUT" ]; then
    die "$OUT existe mais n'est pas un dossier"
fi

# Ce qui sera fait (pour ne vérifier que les dépendances utiles).
NEED_BASE=0
if [ -n "$GAME" ] && { [ ! -f "$OUT/workspace/base/.complete" ] || [ "$REEXTRACT" -eq 1 ]; }; then
    NEED_BASE=1
fi
NEED_3DSTOOL=0
[ "$NEED_BASE" -eq 1 ] && [ -f "$GAME" ] && NEED_3DSTOOL=1

# ---------------------------------------------------------------- dépendances
find_3dstool() {
    if [ -n "${THREEDSTOOL:-}" ]; then
        [ -x "$THREEDSTOOL" ] || die "THREEDSTOOL n'est pas exécutable : $THREEDSTOOL"
        echo "$THREEDSTOOL"; return
    fi
    local c
    for c in "$TOOL_DIR/3dstool" "$TOOL_DIR/../src/3dstool" "$(command -v 3dstool || true)"; do
        if [ -n "$c" ] && [ -x "$c" ]; then echo "$c"; return; fi
    done
}

detect_pm() {
    local pm
    for pm in dnf apt-get pacman zypper; do
        command -v "$pm" >/dev/null && { echo "$pm"; return; }
    done
}

# Nom du paquet fournissant une commande, selon le gestionnaire.
pkg_for() {
    case "$2:$1" in
        pacman:python3) echo python ;;
        *:python3)      echo python3 ;;
        apt-get:g++)    echo g++ ;;
        pacman:g++)     echo gcc ;;
        *:g++)          echo gcc-c++ ;;
        *)              echo "$1" ;;
    esac
}

install_cmd() {
    local sudo=""
    [ "$(id -u)" -ne 0 ] && sudo="sudo "
    case "$1" in
        dnf)     echo "${sudo}dnf install -y" ;;
        apt-get) echo "${sudo}apt-get install -y" ;;
        pacman)  echo "${sudo}pacman -S --needed --noconfirm" ;;
        zypper)  echo "${sudo}zypper install -y" ;;
    esac
}

download_3dstool() {
    local tmp
    tmp="$(mktemp -d)"
    info "téléchargement de 3dstool v1.2.6"
    if ! curl -fsSL --retry 2 -o "$tmp/3dstool.tar.gz" "$T3DS_URL"; then
        rm -rf "$tmp"; die "échec du téléchargement de $T3DS_URL"
    fi
    if ! echo "$T3DS_SHA256  $tmp/3dstool.tar.gz" | sha256sum -c --quiet - >/dev/null 2>&1; then
        rm -rf "$tmp"; die "somme SHA-256 de 3dstool incorrecte : téléchargement refusé"
    fi
    tar -xzf "$tmp/3dstool.tar.gz" -C "$tmp" 3dstool ignore_3dstool.txt
    install -m 755 "$tmp/3dstool" "$TOOL_DIR/3dstool"
    install -m 644 "$tmp/ignore_3dstool.txt" "$TOOL_DIR/ignore_3dstool.txt"
    rm -rf "$tmp"
}

check_deps() {
    local required=() optional=() get_3dstool=0 build_sqc=0 c

    [ "$NEED_BASE" -eq 1 ] && ! command -v python3 >/dev/null && required+=(python3)

    if [ "$NEED_3DSTOOL" -eq 1 ] && [ -z "$(find_3dstool)" ]; then
        [ "$(uname -m)" = "x86_64" ] || die "3dstool introuvable, et pas de binaire officiel pour $(uname -m) : compile-le depuis github.com/dnasdw/3dstool"
        get_3dstool=1
        for c in curl tar sha256sum; do command -v "$c" >/dev/null || required+=("$c"); done
    fi

    if [ ! -x "$TOOL_DIR/sqc" ]; then
        build_sqc=1
        for c in git g++; do command -v "$c" >/dev/null || optional+=("$c"); done
    fi

    [ ${#required[@]} -eq 0 ] && [ $get_3dstool -eq 0 ] && [ $build_sqc -eq 0 ] && return 0

    info "dépendances manquantes :"
    for c in "${required[@]}"; do echo "    $c  (requis)"; done
    [ $get_3dstool -eq 1 ] && echo "    3dstool  (requis : téléchargé depuis github.com/dnasdw/3dstool vers tool/)"
    for c in "${optional[@]}"; do echo "    $c  (pour compiler tool/sqc)"; done
    [ $build_sqc -eq 1 ] && echo "    tool/sqc  (compilateur de scripts : construit par tool/init, clone un dépôt GitHub)"

    local pkgs=() pm="" cmd=""
    if [ ${#required[@]} -gt 0 ] || [ ${#optional[@]} -gt 0 ]; then
        pm="$(detect_pm)"
        for c in "${required[@]}" "${optional[@]}"; do [ -n "$pm" ] && pkgs+=("$(pkg_for "$c" "$pm")"); done
        if [ -n "$pm" ]; then
            cmd="$(install_cmd "$pm") ${pkgs[*]}"
            echo "    commande d'installation : $cmd"
        fi
    fi

    if ! ask "Installer les dépendances manquantes ?"; then
        if [ ${#required[@]} -gt 0 ] || [ $get_3dstool -eq 1 ]; then
            die "dépendances requises absentes ; installe-les puis relance (ou relance avec -y)"
        fi
        warn "tool/sqc non construit : les scripts ne pourront pas être compilés (lance tool/init plus tard)"
        return 0
    fi

    if [ ${#pkgs[@]} -gt 0 ]; then
        [ -n "$pm" ] || die "gestionnaire de paquets non reconnu : installe à la main : ${required[*]} ${optional[*]}"
        info "$cmd"
        $cmd || die "échec de l'installation des paquets"
    fi
    [ $get_3dstool -eq 1 ] && download_3dstool
    if [ $build_sqc -eq 1 ]; then
        info "construction de tool/sqc"
        bash "$TOOL_DIR/init" || warn "échec de tool/init : les scripts ne pourront pas être compilés"
    fi
}

check_deps

# ---------------------------------------------------------------- dossier de sortie
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
WS="$OUT/workspace"

if [ -e "$WS" ] && [ ! -f "$WS/workspace.json" ]; then
    if [ -d "$WS" ] && [ -z "$(ls -A "$WS")" ]; then
        :   # dossier vide : on peut l'utiliser
    else
        die "$WS existe mais n'est pas une workspace (pas de workspace.json) ; choisis un autre -o"
    fi
fi

# ---------------------------------------------------------------- structure
if [ -f "$WS/workspace.json" ]; then
    info "workspace existante : $WS"
else
    info "création de la workspace : $WS"
fi
mkdir -p "$WS"/{base,mods,deps,modified,output}

if [ ! -f "$WS/workspace.json" ]; then
    cat > "$WS/workspace.json" <<EOF
{
  "format": $FORMAT_VERSION,
  "game": "Ever Oasis",
  "title_id": "$TITLE_ID"
}
EOF
fi

# ---------------------------------------------------------------- mod
if [ -n "$MOD_ID" ]; then
    MOD="$WS/mods/$MOD_ID"
    if [ -e "$MOD" ]; then
        warn "le mod '$MOD_ID' existe déjà, il n'est pas modifié"
    elif [ -e "$WS/deps/$MOD_ID" ]; then
        die "'$MOD_ID' existe déjà dans deps/ ; un id doit être unique"
    else
        info "création du mod : mods/$MOD_ID"
        mkdir -p "$MOD"/{scripts,romfs,code}
        cat > "$MOD/mod.json" <<EOF
{
  "id": "$MOD_ID",
  "name": "$MOD_ID",
  "version": "0.1.0",
  "description": "",
  "authors": [],
  "priority": 0,
  "dependencies": []
}
EOF
    fi
fi

# ---------------------------------------------------------------- base/ (jeu d'origine)
# Lit le title ID de l'exheader (offset 0x200, little endian) : vérifie le jeu
# et détecte une ROM chiffrée (l'exheader serait illisible).
check_exheader() {
    local id
    id="$(python3 -c 'import struct,sys; print("%016x" % struct.unpack_from("<Q", open(sys.argv[1],"rb").read(), 0x200)[0])' "$1")" \
        || die "exheader illisible : $1"
    if [ "$id" != "$TITLE_ID" ]; then
        die "title ID $id au lieu de $TITLE_ID.
  Soit ce n'est pas Ever Oasis (ou pas la même région), soit la ROM est chiffrée.
  Il faut un dump déchiffré : sur 3DS, GodMode9 permet de dumper la cartouche
  ou le jeu installé en .3ds déchiffré (ou de déchiffrer un .3ds existant)."
    fi
}

populate_base() {
    local game="$1" base="$WS/base"
    local tmp
    tmp="$(mktemp -d "$WS/.extract.XXXXXX")"
    trap 'rm -rf "$tmp"' EXIT

    if [ -d "$game" ]; then
        info "copie du jeu déjà extrait depuis $game"
        [ -f "$game/exh.bin" ] && [ -d "$game/exefs" ] && [ -d "$game/romfs" ] \
            || die "$game doit contenir exh.bin, exefs/ et romfs/"
        check_exheader "$game/exh.bin"
        cp -a --reflink=auto "$game/exh.bin" "$game/exefs" "$game/romfs" "$tmp/"
        if [ -f "$game/ncchheader.bin" ]; then
            cp -a "$game/ncchheader.bin" "$tmp/"
        else
            warn "pas de ncchheader.bin dans $game (seulement utile pour reconstruire un .3ds/.cia)"
        fi
    else
        local t3ds cxi
        t3ds="$(find_3dstool)"
        [ -n "$t3ds" ] || die "3dstool introuvable"
        case "${game,,}" in
            *.3ds|*.cci)
                info "extraction de la partition 0 du .3ds"
                "$t3ds" -xt0f cci "$tmp/0.cxi" "$game" >/dev/null
                cxi="$tmp/0.cxi" ;;
            *.cxi) cxi="$game" ;;
        esac
        [ -s "$cxi" ] || die "échec de l'extraction du .3ds"

        info "extraction du CXI (en-tête NCCH, exheader, exefs, romfs)"
        "$t3ds" -xtf cxi "$cxi" --header "$tmp/ncchheader.bin" --exh "$tmp/exh.bin" \
            --exefs "$tmp/exefs.bin" --romfs "$tmp/romfs.bin" >/dev/null
        check_exheader "$tmp/exh.bin"
        [ "$cxi" = "$tmp/0.cxi" ] && rm -f "$cxi"

        info "extraction de l'exefs (code.bin décompressé)"
        "$t3ds" -xtfu exefs "$tmp/exefs.bin" --exefs-dir "$tmp/exefs/" >/dev/null
        rm -f "$tmp/exefs.bin"

        info "extraction du romfs (peut prendre un moment)"
        "$t3ds" -xtf romfs "$tmp/romfs.bin" --romfs-dir "$tmp/romfs/" >/dev/null
        rm -f "$tmp/romfs.bin"
    fi
    [ -f "$tmp/exefs/code.bin" ] || die "exefs/code.bin manquant après extraction"
    [ -d "$tmp/romfs" ] || die "romfs/ manquant après extraction"

    info "ouverture des archives .gar"
    python3 "$TOOL_DIR/extract" extract "$tmp/romfs" -o "$tmp/extracted" | tail -n 2

    # Remplacement atomique de base/ : jamais de base/ à moitié rempli.
    rm -rf "$base.old"
    mv "$base" "$base.old"
    mv "$tmp" "$base"
    trap - EXIT
    rm -rf "$base.old"
    date -Iseconds > "$base/.complete"
}

if [ -n "$GAME" ]; then
    if [ "$NEED_BASE" -eq 0 ]; then
        warn "base/ est déjà rempli (utilise --reextract pour recommencer)"
    elif [ ! -f "$WS/base/.complete" ] && [ -n "$(ls -A "$WS/base")" ] && [ "$REEXTRACT" -eq 0 ]; then
        die "base/ contient des fichiers qui ne viennent pas de ce script ; vide-le ou utilise --reextract"
    else
        populate_base "$GAME"
        info "base/ prêt"
    fi
elif [ ! -f "$WS/base/.complete" ]; then
    warn "base/ est vide : relance avec -g chemin/vers/EverOasis.3ds pour le remplir"
fi

info "workspace prête : $WS"
