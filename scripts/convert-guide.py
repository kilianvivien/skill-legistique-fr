#!/usr/bin/env python3
"""Convertit le Guide de légistique (PDF) en fiches Markdown pour la skill.

Usage :
    python3 scripts/convert-guide.py [PDF] [DOSSIER]

Par défaut : Source/guide_legistique_2026.pdf vers legistique-fr/references/guide/.
Dépendance : PyMuPDF (pip install pymupdf).

Le découpage suit les signets du PDF : une fiche numérotée (1.1.1, 5.3…) donne un
fichier, l'annexe typographique en donne un autre, et index.md les recense. La
conversion s'appuie sur la charte graphique du guide (police Marianne) :

- titres de rubrique en gras 13 pt, sous-titres en gras 12 pt ou plus petits ;
- exemples et modèles de rédaction en vert (#006a6f), rendus en citation « > » ;
- puces « − » posées dans un bloc séparé, rattachées à la ligne de même hauteur ;
- repères « // » des recommandations, conservés en tête de paragraphe ;
- exposants (n°, 1er, appels de note) reconstitués ;
- tableaux à filets détectés par PyMuPDF et rendus en tableaux Markdown.

Relancer le script à chaque nouvelle version du guide, puis relire à la main les
fiches à tableaux (1.3.2, 2.1.4, 4.1.3, 4.2.4…) et l'annexe typographique.
"""

import re
import sys
import unicodedata
from pathlib import Path

import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PDF = ROOT / "Source" / "guide_legistique_2026.pdf"
DEFAULT_OUT = ROOT / "legistique-fr" / "references" / "guide"

TEAL = 0x006A6F
BLUE = 0x0000FF  # liens, sans valeur de style
WHITE = 0xFFFFFF
FOOTER_Y = 636  # en dessous : numéro de page et titre courant
SPACES = dict.fromkeys(map(ord, "\xa0\u202f\u2009\u2002\u2003\u2007\t"), " ")
BULLET_GLYPHS = {"−", "–", "-", "•"}
BULLET_INLINE = re.compile(r"^\s*[−–•]\u2002")
LABEL = re.compile(r"^/[/\s]*/\s*(?=[A-ZÉ]{2})")  # « /// EXEMPLE », pas « // Recommandation »
UPDATE = re.compile(r"^\(Mise à jour le (\d\d/\d\d/\d{4})\)$")
FOOTNOTE = re.compile(r"^(\d{1,2})\s+(?=\S)")
FICHE = re.compile(r"^(\d+(?:\.\d+)+)\.?\s+(.*)$")
WORD = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿŒœÆæ]+(?:-[A-Za-zÀ-ÖØ-öø-ÿŒœÆæ]+)*")

GUIDE = ("Guide de légistique, 4e édition (mise à jour 2026), Conseil d'Etat et secrétariat "
         "général du Gouvernement")
LICENCE = ("Texte extrait automatiquement du PDF publié sur Légifrance (contenus sous licence "
           "etalab-2.0). Les tableaux et schémas peuvent être imparfaits : en cas de doute, "
           "vérifier dans le guide en ligne.")


# ---------------------------------------------------------------------------
# Lecture des lignes


def clean(text):
    return text.translate(SPACES)


def is_bold(span):
    return "Bold" in span["font"]


def is_italic(span):
    return "Italic" in span["font"] or bool(span["flags"] & 2)


class Line:
    """Une ligne de texte utile, avec ses fragments stylés."""

    def __init__(self, raw, page_no):
        self.page = page_no
        self.x0, self.y0, self.x1, self.y1 = raw["bbox"]
        spans = [s for s in raw["spans"] if s["color"] != WHITE
                 and not s["font"].startswith(("Frutiger", "HelveticaNeue"))]
        body = [s for s in spans if s["text"].strip()]
        self.size = max((s["size"] for s in body), default=0)
        raw_text = "".join(s["text"] for s in spans)
        self.text = clean(raw_text).strip()
        weights = {}
        for s in [s for s in body if s["color"] != BLUE] or body:
            key = (round(s["size"], 1), s["color"], is_bold(s))
            weights[key] = weights.get(key, 0) + len(s["text"].strip())
        self.main_size, self.color, _ = max(weights, key=weights.get) if weights else (0, 0, False)
        self.all_bold = bool(body) and all(is_bold(s) for s in body)
        self.prefix = ""
        self.frags = []  # (texte, italique, gras)
        for s in spans:
            text = clean(s["text"])
            small = s["text"].strip() and s["size"] < 0.72 * self.size
            if small:
                core = text.strip()
                if core == "o":
                    text = "°"
                elif core.isdigit() and s["color"] != TEAL:
                    text = f"[^{page_no}-{core}]"
                else:
                    text = core
            self.frags.append((text, is_italic(s), is_bold(s)))
        if BULLET_INLINE.match(raw_text) and self.text not in BULLET_GLYPHS:
            self.prefix = "- "
            self.strip_leading(re.compile(r"^[−–•]\s*"))

    def strip_leading(self, pattern):
        joined = "".join(f[0] for f in self.frags)
        m = pattern.match(joined.lstrip())
        if not m:
            return
        drop = len(joined) - len(joined.lstrip()) + m.end()
        frags = []
        for text, it, bd in self.frags:
            cut = min(drop, len(text))
            drop -= cut
            if text[cut:]:
                frags.append((text[cut:], it, bd))
        self.frags = frags
        self.text = "".join(f[0] for f in frags).strip()

    @property
    def mid(self):
        return (self.y0 + self.y1) / 2

    @property
    def kind(self):
        if UPDATE.match(self.text):
            return "update"
        if LABEL.match(self.text):
            return "label"
        if 7.5 <= self.main_size <= 8.5 and FOOTNOTE.match(self.text) and self.y0 > 400:
            return "footnote"
        if self.color == TEAL and not self.all_bold:
            return "example"
        if self.main_size <= 7.5:
            return "example"
        return "body"


def page_items(page, page_no):
    """Lignes et tableaux d'une page, dans l'ordre de lecture du PDF."""
    tables = []
    try:
        found = page.find_tables()
        for t in found.tables:
            rows = t.extract()
            if t.row_count >= 2 and t.col_count >= 2 and any(any(c for c in r) for r in rows):
                tables.append((fitz.Rect(t.bbox), rows))
    except Exception:  # la détection de tableaux ne doit jamais bloquer la conversion
        tables = []

    def in_table(line):
        cx, cy = (line.x0 + line.x1) / 2, line.mid
        return any(r.x0 - 2 <= cx <= r.x1 + 2 and r.y0 - 2 <= cy <= r.y1 + 2 for r, _ in tables)

    lines, markers = [], []
    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0:
            continue
        for raw in block["lines"]:
            line = Line(raw, page_no)
            if not line.text or line.y0 >= FOOTER_Y or line.size >= 18 or in_table(line):
                continue
            if line.text in BULLET_GLYPHS or line.text == "//":
                markers.append(line)
                continue
            lines.append(line)

    for m in markers:
        near = [l for l in lines if abs(l.mid - m.mid) < 4 and 0 < l.x0 - m.x0 < 40]
        if near:
            target = min(near, key=lambda l: l.x0 - m.x0)
            if m.text == "//" and LABEL.match("//" + target.text):
                target.text = "//" + target.text  # « // » + « / EXEMPLE » : une étiquette
            elif m.text == "//":
                target.strip_leading(re.compile(r"/[/\s]*"))
                target.frags.insert(0, ("// ", False, False))
            else:
                target.prefix = "- "

    items = list(lines)
    for rect, rows in sorted(tables, key=lambda t: t[0].y0, reverse=True):
        pos = next((i for i, l in enumerate(items)
                    if isinstance(l, Line) and l.y0 > rect.y0), len(items))
        items.insert(pos, ("table", rows))
    return items


# ---------------------------------------------------------------------------
# Assemblage en paragraphes


def build_vocab(doc):
    vocab = set()
    for page in doc:
        text = page.get_text().replace("\xad\n", "").replace("\xad", "")
        vocab.update(w.lower() for w in WORD.findall(text))
    return vocab


class Para:
    def __init__(self, line):
        self.kind = line.kind
        self.prefix = line.prefix
        self.frags = list(line.frags)
        self.size = line.main_size
        self.color = line.color
        self.all_bold = line.all_bold
        self.last = line

    @property
    def text(self):
        return "".join(f[0] for f in self.frags).strip()

    def append(self, line, vocab):
        prev_text, it, bd = self.frags[-1] if self.frags else ("", False, False)
        stripped = prev_text.rstrip()
        nxt = line.text
        glue = " "
        if stripped.endswith("\xad"):
            stripped, glue = stripped[:-1], ""
        elif stripped.endswith("-") and nxt[:1].islower():
            left = re.search(r"([\wÀ-ÿ]+)-$", stripped)
            right = WORD.match(nxt)
            glue = ""
            if left and right:
                joined = (left.group(1) + right.group(0)).lower()
                hyphenated = (left.group(1) + "-" + right.group(0)).lower()
                if joined in vocab and hyphenated not in vocab:
                    stripped = stripped[:-1]
        elif nxt[:1] in ";:,.)»" and not nxt.startswith("»"):
            glue = ""
        if self.frags:
            self.frags[-1] = (stripped + glue, it, bd)
        self.frags.extend(line.frags)
        self.all_bold = self.all_bold and line.all_bold
        self.last = line

    def accepts(self, line):
        if line.prefix or line.kind != self.kind or self.kind in ("update", "label"):
            return False
        prev = self.last
        text = self.text
        # phrase coupée par la mise en page (modèles en petit corps, fins de ligne serrées)
        if line.page == prev.page and 0 < line.y0 - prev.y0 <= 2 * max(self.size, 1) \
                and re.search(r"[\wÀ-ÿ,]$", text) and re.match(r"[a-zà-ÿ0-9]", line.text) \
                and abs(line.main_size - self.size) <= 0.8:
            return True
        # suite de phrase après un saut de colonne ou de page
        if (line.page != prev.page or line.y0 < prev.y0 - 2) and text \
                and text[-1] not in ".:;!?»)" and line.text[:1].islower():
            return True
        if line.page != prev.page or line.y0 < prev.y0 - 2:
            return False
        if line.text[:1] in ";:,.)" and line.y0 - prev.y0 < 2 * self.size:
            return True
        if abs(line.main_size - self.size) > 0.8 or line.all_bold != self.all_bold:
            return False
        return line.y0 - prev.y0 <= 1.35 * max(self.size, 1)


def render_frags(frags):
    runs = []
    for text, it, bd in frags:
        if not text.strip():
            it = bd = False  # espaces jamais balisés
        if runs and runs[-1][1:] == [it, bd]:
            runs[-1][0] += text
        else:
            runs.append([text, it, bd])
    out = []
    for text, it, bd in runs:
        text = text.replace("\xad", "").replace("*", "\\*")
        core = text.strip()
        if not core or not (it or bd) or not re.search(r"[\wÀ-ÿ]", core):
            out.append(text)
            continue
        mark = ("**" if bd else "") + ("*" if it else "")
        lead = text[: len(text) - len(text.lstrip())]
        trail = text[len(text.rstrip()):]
        out.append(f"{lead}{mark}{core}{mark[::-1]}{trail}")
    md = "".join(out)
    md = re.sub(r"\*\*\*\*|(?<!\*)\*\*(?!\*)(?=\*\*)", "", md)
    md = re.sub(r" {2,}", " ", md)
    return md.strip()


def cell(text, vocab):
    if not text:
        return ""
    text = text.replace("\xad\n", "").replace("\xad", "")
    parts = text.split("\n")
    out = parts[0]
    for part in parts[1:]:
        m = re.search(r"([\wÀ-ÿ]+)-$", out)
        w = WORD.match(part)
        if m and w and part[:1].islower() and (m.group(1) + w.group(0)).lower() in vocab:
            out = out[:-1] + part
        else:
            out = out + ("" if out.endswith("-") else " ") + part
    text = clean(out)
    text = re.sub(r"(?<![\wÀ-ÿ])no\s*(?=\d)", "n° ", text)
    text = re.sub(r",(?=n° )", ", ", text)
    return re.sub(r" {2,}", " ", text).replace("|", "\\|").strip()


def render_table(rows, vocab):
    width = max(len(r) for r in rows)
    rows = [[cell(c, vocab) for c in r] + [""] * (width - len(r)) for r in rows]
    header = [c or " " for c in rows[0]]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * width]
    lines += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(lines)


def convert_unit(doc, first, last, vocab):
    """Convertit les pages [first, last] (index 0) ; renvoie (markdown, date de mise à jour)."""
    blocks, para, updated = [], None, None

    def flush():
        nonlocal para
        if para is not None:
            blocks.append(para)
        para = None

    for page_no in range(first, last + 1):
        for item in page_items(doc[page_no], page_no + 1):
            if isinstance(item, tuple):
                flush()
                blocks.append(render_table(item[1], vocab))
                continue
            if item.kind == "update":
                updated = updated or UPDATE.match(item.text).group(1)
                continue
            if para is not None and para.accepts(item):
                para.append(item, vocab)
            else:
                flush()
                para = Para(item)
    flush()

    out = []
    for b in blocks:
        if isinstance(b, str):
            out.append(b)
            continue
        md = render_frags(b.frags)
        if not md:
            continue
        plain = re.sub(r"[*\\]", "", md)
        if b.kind == "label":
            rest = re.sub(r"^[/\s]+", "", plain)
            if rest:
                out.append(f"**/// {rest}**")
        elif b.kind == "footnote":
            m = FOOTNOTE.match(plain)
            out.append(f"[^{b.last.page}-{m.group(1)}]: {plain[m.end():]}")
        elif b.kind == "example":
            out.append("> " + b.prefix + md)
        elif b.all_bold and not b.prefix and (
                b.size >= 11.5 or b.color == TEAL
                or (len(plain) <= 110 and plain[-1] not in ".;,:")):
            level = "##" if b.size >= 12.5 else "###" if (b.size >= 11.5 or b.color == TEAL) else "####"
            out.append(f"{level} {plain}")
        else:
            out.append(b.prefix + md)

    text = ""
    for chunk in out:
        if text:
            same_list = chunk.startswith("- ") and text.rsplit("\n", 1)[-1].startswith("- ")
            same_quote = chunk.startswith("> - ") and text.rsplit("\n", 1)[-1].startswith("> ")
            text += "\n" if (same_list or same_quote) else ("\n>\n" if chunk.startswith("> ")
                                                            and text.rsplit("\n", 1)[-1].startswith("> ")
                                                            else "\n\n")
        text += chunk
    return text.strip() + "\n", updated


# ---------------------------------------------------------------------------
# Découpage et index


def slug(title):
    title = re.sub(r"[’']", "-", title).replace("œ", "oe").replace("Œ", "Oe")
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")
    return s[:60].rstrip("-")


def units_from_toc(doc):
    toc = doc.get_toc()
    units, part, section = [], None, None
    for level, title, page in toc:
        title = " ".join(title.split())
        if level == 1:
            part, section = title, None
        elif level == 2 and not FICHE.match(title):
            section = title
        m = FICHE.match(title)
        if m and level >= 2:
            units.append(dict(number=m.group(1), title=m.group(2), part=part,
                              section=section if level == 3 else None, start=page - 1))
        elif level == 1 and title.startswith("Principales règles typographiques"):
            units.append(dict(number=None, title=title, part=title, section=None, start=page - 1))
    for i, u in enumerate(units):
        u["end"] = units[i + 1]["start"] - 1 if i + 1 < len(units) else doc.page_count - 1
        u["file"] = (f"{u['number']}-{slug(u['title'])}.md" if u["number"]
                     else "annexe-regles-typographiques.md")
    return units


def section_label(title):
    if not title:
        return None
    return title[:1] + title[1:].lower() if title.isupper() else title


def main():
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PDF
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT
    doc = fitz.open(pdf)
    vocab = build_vocab(doc)
    units = units_from_toc(doc)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.md"):
        old.unlink()

    for u in units:
        body, updated = convert_unit(doc, u["start"], u["end"], vocab)
        label = f"Fiche {u['number']}. {u['title']}" if u["number"] else u["title"]
        meta = [f"Partie : {u['part']}"]
        if u["section"]:
            meta.append(f"Rubrique : {section_label(u['section'])}")
        if updated:
            meta.append(f"Mise à jour de la fiche : {updated}")
        meta.append(f"Pages {u['start'] + 1} à {u['end'] + 1} du PDF")
        header = f"# {label}\n\n> {GUIDE}.\n> {' · '.join(meta)}.\n> {LICENCE}\n\n"
        (out_dir / u["file"]).write_text(header + body, encoding="utf-8")
        u["updated"], u["words"] = updated, len(body.split())
        print(f"{u['file']:<70} {u['words']:>6} mots")

    index = [
        "# Guide de légistique : index des fiches",
        "",
        f"{GUIDE}. Texte intégral du guide, une fiche par fichier, converti depuis le PDF publié "
        "sur Légifrance (contenus sous licence etalab-2.0). Source subsidiaire : ne l'ouvrir que si "
        "les fiches de synthèse de `references/` ne suffisent pas (voir SKILL.md).",
        "",
        "Pour trouver un passage : repérer la fiche dans les tableaux ci-dessous, ou chercher un "
        "mot-clé dans ce dossier avec l'outil de recherche de l'agent (par exemple "
        "`grep -ril \"contreseing\" references/guide/`). Avant de lire une fiche, lister ses titres "
        "(`grep -n \"^#\" references/guide/3.4.1-*.md`) et ne lire que la section utile : les fiches "
        "de plus de 5 000 mots ne se lisent jamais en entier.",
        "",
        "Conventions de conversion : « > » signale un exemple ou un modèle de rédaction (en vert dans "
        "le guide) ; « // » ouvre une recommandation mise en avant par le guide ; « /// EXEMPLE » "
        "annonce des exemples ; « [^page-n] » renvoie à une note de bas de page.",
        "",
    ]
    part = section = object()
    for u in units:
        if u["part"] != part:
            part, section = u["part"], object()
            index += [f"## {part}", ""]
        if u["section"] != section:
            section = u["section"]
            if section:
                index += [f"### {section_label(section)}", ""]
            index += ["| Fiche | Titre | Fichier | Mots | Mise à jour |", "|---|---|---|---|---|"]
        index.append(f"| {u['number'] or '—'} | {u['title']} | `{u['file']}` | {u['words']} | "
                     f"{u['updated'] or '—'} |")
        nxt = units[units.index(u) + 1] if u is not units[-1] else None
        if not nxt or nxt["part"] != part or nxt["section"] != section:
            index.append("")
    (out_dir / "index.md").write_text("\n".join(index), encoding="utf-8")
    total = sum(u["words"] for u in units)
    print(f"{len(units)} fichiers, {total} mots, index : {out_dir / 'index.md'}")


if __name__ == "__main__":
    main()
