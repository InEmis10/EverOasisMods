#!/usr/bin/env python3
"""
gsb_asm : convertit un .gsb (bytecode Squirrel 2 d'Ever Oasis) en texte éditable,
et reconstruit le .gsb à partir du texte.

  python3 gsb_asm.py dump  VendorNpc.gsb  VendorNpc.gsa   # binaire -> texte
  python3 gsb_asm.py build VendorNpc.gsa  VendorNpc.gsb   # texte -> binaire
  python3 gsb_asm.py dump  extrait/  textes/              # tout un dossier
  python3 gsb_asm.py build textes/   extrait/             # idem (n'écrit que les .gsb modifiés)

Le .gsa est du texte : ouvre-le dans n'importe quel IDE. Les commentaires (après ';')
sont ignorés à la reconstruction ; ils servent à lire (nom de la fonction appelée,
chaîne chargée, valeur flottante…).

Modifs sûres  : valeurs des LOADINT, des LOADFLOAT (écrire a1 sous la forme float:0.05),
               littéraux (.lit), paramètres d'appel.
Modifs avancées : ajouter/supprimer des instructions. Les sauts (JMP/JZ/JNZ…) sont
relatifs et les tables .line / .local référencent des numéros d'instruction : il faut
les corriger à la main.
"""
import json
import re
import struct
import sys
from pathlib import Path

PART, TAIL, HEAD = b"TRAP", b"LIAT", b"\xfa\xfaRIQS"
OT_NULL, OT_INTEGER, OT_FLOAT, OT_BOOL, OT_STRING = (
    0x01000001, 0x05000002, 0x05000004, 0x01000008, 0x08000010)

OPCODES = [
    "LINE", "LOAD", "LOADINT", "LOADFLOAT", "DLOAD", "TAILCALL", "CALL", "PREPCALL",
    "PREPCALLK", "GETK", "MOVE", "NEWSLOT", "DELETE", "SET", "GET", "EQ", "NE",
    "ARITH", "BITW", "RETURN", "LOADNULLS", "LOADROOTTABLE", "LOADBOOL", "DMOVE",
    "JMP", "JNZ", "JZ", "LOADFREEVAR", "VARGC", "GETVARGV", "NEWTABLE", "NEWARRAY",
    "APPENDARRAY", "GETPARENT", "COMPARITH", "COMPARITHL", "INC", "INCL", "PINC",
    "PINCL", "CMP", "EXISTS", "INSTANCEOF", "AND", "OR", "NEG", "NOT", "BWNOT",
    "CLOSURE", "YIELD", "RESUME", "FOREACH", "POSTFOREACH", "DELEGATE", "CLONE",
    "TYPEOF", "PUSHTRAP", "POPTRAP", "THROW", "CLASS", "NEWSLOTA",
]
OP_NUM = {n: i for i, n in enumerate(OPCODES)}


# ====================== objets Squirrel ======================
# Représentation interne : ("str", bytes) | ("int", int) | ("float", bits_u32)
#                          | ("bool", u32) | ("null",)

class R:
    def __init__(self, d):
        self.d, self.p = d, 0

    def take(self, n):
        b = self.d[self.p:self.p + n]
        if len(b) != n:
            raise ValueError(f"fin de fichier inattendue à 0x{self.p:X}")
        self.p += n
        return b

    def u32(self):
        return struct.unpack("<I", self.take(4))[0]

    def i32(self):
        return struct.unpack("<i", self.take(4))[0]

    def tag(self, t):
        got = self.take(4)
        if got != t:
            raise ValueError(f"tag {t!r} attendu à 0x{self.p - 4:X}, trouvé {got!r}")

    def obj(self):
        t = self.u32()
        if t == OT_STRING:
            return ("str", self.take(self.u32()))
        if t == OT_INTEGER:
            return ("int", self.i32())
        if t == OT_FLOAT:
            return ("float", self.u32())
        if t == OT_BOOL:
            return ("bool", self.u32())
        if t == OT_NULL:
            return ("null",)
        raise ValueError(f"type d'objet inconnu 0x{t:08X} à 0x{self.p - 4:X}")


def w_obj(o) -> bytes:
    k = o[0]
    if k == "str":
        return struct.pack("<II", OT_STRING, len(o[1])) + o[1]
    if k == "int":
        return struct.pack("<Ii", OT_INTEGER, o[1])
    if k == "float":
        return struct.pack("<II", OT_FLOAT, o[1])
    if k == "bool":
        return struct.pack("<II", OT_BOOL, o[1])
    return struct.pack("<I", OT_NULL)


# ---- objet <-> texte ----

def f32(bits):
    return struct.unpack("<f", struct.pack("<I", bits))[0]


def obj_txt(o) -> str:
    k = o[0]
    if k == "str":
        try:
            return json.dumps(o[1].decode("utf-8"), ensure_ascii=False)
        except UnicodeDecodeError:
            # chaînes Shift-JIS (commentaires de debug japonais) : octets bruts
            return "bytes:" + o[1].hex() + "  ; " + o[1].decode("shift_jis", "replace")
    if k == "int":
        return str(o[1])
    if k == "float":
        return f"float:0x{o[1]:08X}  ; {f32(o[1]):g}"
    if k == "bool":
        return "true" if o[1] == 1 else ("false" if o[1] == 0 else f"bool:{o[1]}")
    return "null"


def txt_obj(s: str):
    s = s.strip()
    if s.startswith('"'):
        val, fin = json.JSONDecoder().raw_decode(s)
        return ("str", val.encode("utf-8")), s[fin:]
    m = re.match(r"(\S+)(.*)", s)
    tok, reste = m.group(1), m.group(2)
    if tok.startswith("bytes:"):
        return ("str", bytes.fromhex(tok[6:])), reste
    if tok.startswith("float:"):
        v = tok[6:]
        if v.lower().startswith("0x"):
            return ("float", int(v, 16)), reste
        return ("float", struct.unpack("<I", struct.pack("<f", float(v)))[0]), reste
    if tok == "true":
        return ("bool", 1), reste
    if tok == "false":
        return ("bool", 0), reste
    if tok.startswith("bool:"):
        return ("bool", int(tok[5:])), reste
    if tok == "null":
        return ("null",), reste
    return ("int", int(tok, 0)), reste


# ====================== binaire -> structure ======================

def lire_fn(r: R) -> dict:
    f = {}
    r.tag(PART)
    f["source"], f["name"] = r.obj(), r.obj()
    r.tag(PART)
    n = [r.u32() for _ in range(8)]
    r.tag(PART)
    f["lit"] = [r.obj() for _ in range(n[0])]
    r.tag(PART)
    f["param"] = [r.obj() for _ in range(n[1])]
    r.tag(PART)
    f["outer"] = [(r.u32(), r.obj(), r.obj()) for _ in range(n[2])]
    r.tag(PART)
    f["local"] = [(r.obj(), r.u32(), r.u32(), r.u32()) for _ in range(n[3])]
    r.tag(PART)
    f["line"] = [(r.i32(), r.i32()) for _ in range(n[4])]
    r.tag(PART)
    f["default"] = [r.i32() for _ in range(n[5])]
    r.tag(PART)
    f["code"] = []
    for _ in range(n[6]):
        a1 = r.i32()
        op, a0, a2, a3 = r.take(4)
        f["code"].append([op, a0, a1, a2, a3])
    r.tag(PART)
    f["fn"] = [lire_fn(r) for _ in range(n[7])]
    f["stack"] = r.u32()
    f["gen"], f["vargs"] = r.take(1)[0], r.take(1)[0]
    return f


def lire_gsb(data: bytes) -> dict:
    if data[:6] != HEAD:
        raise ValueError("pas un .gsb (magic FAFA SQIR absent)")
    r = R(data)
    r.p = 6
    if r.u32() != 1:
        raise ValueError("sizeof(char) != 1")
    f = lire_fn(r)
    r.tag(TAIL)
    if r.p != len(data):
        raise ValueError(f"{len(data) - r.p} octets en trop après TAIL")
    return f


# ====================== structure -> binaire ======================

def ecrire_fn(f: dict) -> bytes:
    o = bytearray(PART) + w_obj(f["source"]) + w_obj(f["name"]) + PART
    o += struct.pack("<8I", len(f["lit"]), len(f["param"]), len(f["outer"]),
                     len(f["local"]), len(f["line"]), len(f["default"]),
                     len(f["code"]), len(f["fn"]))
    o += PART + b"".join(w_obj(x) for x in f["lit"])
    o += PART + b"".join(w_obj(x) for x in f["param"])
    o += PART + b"".join(struct.pack("<I", t) + w_obj(s) + w_obj(n) for t, s, n in f["outer"])
    o += PART + b"".join(w_obj(n) + struct.pack("<III", a, b, c) for n, a, b, c in f["local"])
    o += PART + b"".join(struct.pack("<ii", a, b) for a, b in f["line"])
    o += PART + b"".join(struct.pack("<i", d) for d in f["default"])
    o += PART
    for op, a0, a1, a2, a3 in f["code"]:
        for nom, v, lo, hi in (("op", op, 0, 255), ("a0", a0, 0, 255),
                               ("a2", a2, 0, 255), ("a3", a3, 0, 255)):
            if not lo <= v <= hi:
                raise ValueError(f"{f['name']}: {nom}={v} hors de 0..255")
        o += struct.pack("<iBBBB", a1, op, a0, a2, a3)
    o += PART + b"".join(ecrire_fn(s) for s in f["fn"])
    o += struct.pack("<IBB", f["stack"], f["gen"], f["vargs"])
    return bytes(o)


def ecrire_gsb(f: dict) -> bytes:
    return HEAD + struct.pack("<I", 1) + ecrire_fn(f) + TAIL


# ====================== structure -> texte ======================

def commentaire(f, op, a0, a1, a2, a3) -> str:
    nom = OPCODES[op] if op < len(OPCODES) else ""
    lit = f["lit"]
    if nom in ("LOAD", "PREPCALLK", "GETK", "DLOAD") and 0 <= a1 < len(lit):
        s = obj_txt(lit[a1]).split("  ;")[0]
        if nom == "DLOAD" and 0 <= a3 < len(lit):
            s += ", " + obj_txt(lit[a3]).split("  ;")[0]
        return s
    if nom == "LOADFLOAT":
        return f"{f32(a1 & 0xFFFFFFFF):g}"
    if nom == "LOADINT":
        return str(a1)
    if nom in ("JMP", "JZ", "JNZ"):
        return f"-> saut relatif {a1:+d}"
    if nom == "CLOSURE" and 0 <= a1 < len(f["fn"]):
        return "fonction " + obj_txt(f["fn"][a1]["name"])
    return ""


def fn_txt(f: dict, ind: str = "") -> list:
    L = []
    i2 = ind + "    "
    L.append(f"{ind}.function {obj_txt(f['name'])}")
    L.append(f"{i2}.source {obj_txt(f['source'])}")
    L.append(f"{i2}.stack {f['stack']}  .generator {f['gen']}  .varargs {f['vargs']}")
    for p in f["param"]:
        L.append(f"{i2}.param {obj_txt(p)}")
    for d in f["default"]:
        L.append(f"{i2}.default {d}")
    for k, x in enumerate(f["lit"]):
        L.append(f"{i2}.lit {obj_txt(x)}" + ("" if "  ;" in obj_txt(x) else f"  ; #{k}"))
    for t, s, n in f["outer"]:
        L.append(f"{i2}.outer {t} {obj_txt(s)} {obj_txt(n)}")
    for n, a, b, c in f["local"]:
        L.append(f"{i2}.local {obj_txt(n)} {a} {b} {c}")
    for a, b in f["line"]:
        L.append(f"{i2}.line {a} {b}")
    L.append(f"{i2}.code")
    for k, (op, a0, a1, a2, a3) in enumerate(f["code"]):
        nom = OPCODES[op] if op < len(OPCODES) else f"OP_{op}"
        c = commentaire(f, op, a0, a1, a2, a3)
        L.append(f"{i2}    {nom:<13} {a0:3} {a1:11} {a2:3} {a3:3}  ; {k:4}"
                 + (f"  {c}" if c else ""))
    L.append(f"{i2}.endcode")
    for s in f["fn"]:
        L.append("")
        L += fn_txt(s, i2)
    L.append(f"{ind}.endfunction  ; {obj_txt(f['name'])}")
    return L


def gsb_vers_texte(f: dict, nom: str) -> str:
    entete = [
        f"; {nom} : bytecode Squirrel 2 (Ever Oasis), généré par gsb_asm.py",
        "; Reconstruire : python3 gsb_asm.py build <ce_fichier>.gsa <sortie>.gsb",
        "; Instruction : OPCODE a0 a1 a2 a3   (a1 = entier 32 bits signé, autres 0..255)",
        "",
    ]
    return "\n".join(entete + fn_txt(f)) + "\n"


# ====================== texte -> structure ======================

def sans_commentaire(ligne: str) -> str:
    # retire ce qui suit un ';' situé hors d'une chaîne "..."
    dans, esc = False, False
    for i, c in enumerate(ligne):
        if dans:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                dans = False
        elif c == '"':
            dans = True
        elif c == ";":
            return ligne[:i].strip()
    return ligne.strip()


def texte_vers_gsb(texte: str) -> dict:
    lignes = [(n + 1, sans_commentaire(l)) for n, l in enumerate(texte.splitlines())]
    lignes = [(n, l) for n, l in lignes if l]
    pos = 0

    def erreur(n, msg):
        raise ValueError(f"ligne {n} : {msg}")

    def lire_fonction():
        nonlocal pos
        n, l = lignes[pos]
        if not l.startswith(".function"):
            erreur(n, "'.function' attendu")
        f = {"param": [], "default": [], "lit": [], "outer": [], "local": [],
             "line": [], "code": [], "fn": [], "stack": 0, "gen": 0, "vargs": 0}
        f["name"], _ = txt_obj(l[len(".function"):])
        f["source"] = ("str", b"")
        pos += 1
        en_code = False
        while pos < len(lignes):
            n, l = lignes[pos]
            try:
                if en_code:
                    if l == ".endcode":
                        en_code = False
                        pos += 1
                        continue
                    t = l.split()
                    if len(t) != 5:
                        erreur(n, "instruction : OPCODE a0 a1 a2 a3 attendu")
                    op = OP_NUM.get(t[0].upper())
                    if op is None:
                        if t[0].upper().startswith("OP_"):
                            op = int(t[0][3:])
                        else:
                            erreur(n, f"opcode inconnu {t[0]!r}")
                    a0, a2, a3 = int(t[1], 0), int(t[3], 0), int(t[4], 0)
                    if t[2].lower().startswith("float:"):   # LOADFLOAT 5 float:0.05 0 0
                        a1 = struct.unpack("<i", struct.pack("<f", float(t[2][6:])))[0]
                    else:
                        a1 = int(t[2], 0)
                    f["code"].append([op, a0, a1, a2, a3])
                    pos += 1
                    continue
                if l.startswith(".function"):
                    f["fn"].append(lire_fonction())
                    continue
                if l.startswith(".endfunction"):
                    pos += 1
                    return f
                mot, _, reste = l.partition(" ")
                if mot == ".source":
                    f["source"], _ = txt_obj(reste)
                elif mot == ".stack":
                    t = l.split()
                    f["stack"], f["gen"], f["vargs"] = int(t[1]), int(t[3]), int(t[5])
                elif mot == ".param":
                    f["param"].append(txt_obj(reste)[0])
                elif mot == ".default":
                    f["default"].append(int(reste, 0))
                elif mot == ".lit":
                    f["lit"].append(txt_obj(reste)[0])
                elif mot == ".outer":
                    t, r1 = reste.split(None, 1)
                    s, r2 = txt_obj(r1)
                    nm, _ = txt_obj(r2)
                    f["outer"].append((int(t, 0), s, nm))
                elif mot == ".local":
                    nm, r1 = txt_obj(reste)
                    a, b, c = (int(x, 0) for x in r1.split())
                    f["local"].append((nm, a, b, c))
                elif mot == ".line":
                    a, b = (int(x, 0) for x in reste.split())
                    f["line"].append((a, b))
                elif mot == ".code":
                    en_code = True
                else:
                    erreur(n, f"directive inconnue {mot!r}")
            except ValueError as e:
                if str(e).startswith("ligne "):
                    raise
                erreur(n, str(e))
            pos += 1
        erreur(lignes[-1][0], "'.endfunction' manquant")

    f = lire_fonction()
    if pos != len(lignes):
        erreur(lignes[pos][0], "contenu après la fonction principale")
    return f


# ====================== CLI ======================

def parse_args(argv):
    """Sépare l'option -o/--output des autres arguments."""
    out, rest, i = None, [], 0
    while i < len(argv):
        if argv[i] in ("-o", "--output"):
            if i + 1 >= len(argv):
                sys.exit("erreur : -o attend un chemin")
            out = argv[i + 1]
            i += 2
        else:
            rest.append(argv[i])
            i += 1
    return rest, out


def sortie_defaut(src: Path, ext: str) -> Path:
    """Sortie par défaut dans le dossier courant : fichier -> nom.ext, dossier -> nom_ext/"""
    if src.is_dir():
        return Path.cwd() / f"{src.resolve().name}_{ext.lstrip('.')}"
    return Path.cwd() / (src.stem + ext)

def dump(src: Path, dst: Path):
    if src.is_dir():
        n = 0
        for fp in sorted(src.rglob("*.gsb")):
            cible = dst / fp.relative_to(src).with_suffix(".gsa")
            cible.parent.mkdir(parents=True, exist_ok=True)
            try:
                cible.write_text(gsb_vers_texte(lire_gsb(fp.read_bytes()), fp.name), "utf-8")
                n += 1
            except Exception as e:
                print(f"[ERREUR] {fp} : {e}")
        print(f"{n} fichiers convertis en texte dans {dst}/")
    else:
        dst.write_text(gsb_vers_texte(lire_gsb(src.read_bytes()), src.name), "utf-8")
        print(f"-> {dst}")


def build(src: Path, dst: Path):
    if src.is_dir():
        n = 0
        for fp in sorted(src.rglob("*.gsa")):
            cible = dst / fp.relative_to(src).with_suffix(".gsb")
            try:
                data = ecrire_gsb(texte_vers_gsb(fp.read_text("utf-8")))
            except Exception as e:
                print(f"[ERREUR] {fp} : {e}")
                continue
            if cible.is_file() and cible.read_bytes() == data:
                continue
            cible.parent.mkdir(parents=True, exist_ok=True)
            cible.write_bytes(data)
            print(f"modifié : {cible}")
            n += 1
        print(f"{n} .gsb réécrit(s). Lance ensuite gar_tool.py repack.")
    else:
        data = ecrire_gsb(texte_vers_gsb(src.read_text("utf-8")))
        dst.write_bytes(data)
        print(f"-> {dst} ({len(data)} octets)")


def main():
    a, out = parse_args(sys.argv[1:])
    if len(a) == 2 and a[0] in ("dump", "build"):
        src = Path(a[1])
        ext = ".gsa" if a[0] == "dump" else ".gsb"
        dst = Path(out) if out else sortie_defaut(src, ext)
        if not src.is_dir():
            dst.parent.mkdir(parents=True, exist_ok=True)
        (dump if a[0] == "dump" else build)(src, dst)
    else:
        print(__doc__)
        print("Option : -o CHEMIN  (sinon : dossier courant, même nom, nouvelle extension)")
        sys.exit(1)


if __name__ == "__main__":
    main()
