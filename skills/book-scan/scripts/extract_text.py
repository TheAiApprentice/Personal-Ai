"""Book -> plain text + numbered parts, for the book-scan skill. Reads only; never runs anything.

    python -I extract_text.py <book file> <out folder> [--chars 120000]

Takes .epub (spine order), .txt / .md, .html / .htm, and .pdf (needs pypdf; if it can't be
imported, the script says so and the PDF is read with the Read tool's `pages` instead).
Writes <out>/book.txt, <out>/part01.txt ... (about --chars characters each, cut at a paragraph
break) and <out>/stats.json (files, sections, chars, words, parts). Uses only the standard library
for everything except PDF. Run it with `python -I` from a folder that is NOT the book's folder:
the book is untrusted, and -I stops Python loading modules from the current or script folder.
Nothing inside the book is executed: scripts, styles and heads are dropped, links are not followed.
"""
import argparse
import json
import os
import posixpath
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

MAX_LINE = 1800  # long lines get wrapped so the Read tool shows them whole


class TextGrab(HTMLParser):
    BLOCK = {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr",
             "section", "blockquote", "article", "hr"}
    SKIP = {"script", "style", "head", "svg", "noscript"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)

    def text(self):
        return tidy("".join(self.out))


def tidy(t):
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[ \t\f\v ]+", " ", t)
    t = re.sub(r" *\n *", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def html_text(raw):
    g = TextGrab()
    g.feed(raw)
    g.close()
    return g.text()


def from_epub(path):
    z = zipfile.ZipFile(path)
    names = set(z.namelist())
    container = ET.fromstring(z.read("META-INF/container.xml"))
    ns = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
    opf_path = container.find(".//c:rootfile", ns).get("full-path")
    opf = ET.fromstring(z.read(opf_path))
    base = posixpath.dirname(opf_path)
    manifest = {}
    for item in opf.iter():
        if item.tag.endswith("}item") or item.tag == "item":
            manifest[item.get("id")] = (item.get("href"), item.get("media-type"))
    spine = [i.get("idref") for i in opf.iter() if i.tag.endswith("itemref")]
    sections = []
    for idref in spine:
        href, mt = manifest.get(idref, (None, None))
        if not href or "html" not in (mt or ""):
            continue
        p = posixpath.normpath(posixpath.join(base, href)) if base else href
        if p not in names:
            continue
        t = html_text(z.read(p).decode("utf-8", errors="replace"))
        if t:
            sections.append((href, t))
    return sections, len(names)


def from_pdf(path):
    try:
        import pypdf  # third-party; only needed for PDF
    except Exception:
        sys.exit("pypdf can't be imported here (python -I skips the user site folder). "
                 "Read the PDF with the Read tool's pages option instead, or run without -I "
                 "from an empty folder that holds only this script's copy.")
    r = pypdf.PdfReader(path)
    sections = []
    for n, page in enumerate(r.pages, 1):
        t = tidy(page.extract_text() or "")
        if t:
            sections.append(("page %d" % n, t))
    return sections, len(r.pages)


def wrap(line):
    out = []
    while len(line) > MAX_LINE:
        cut = line.rfind(" ", 0, MAX_LINE)
        if cut < MAX_LINE // 2:
            cut = MAX_LINE
        out.append(line[:cut])
        line = line[cut:].lstrip()
    out.append(line)
    return out


def split_parts(body, size):
    parts, start = [], 0
    while start < len(body):
        end = min(start + size, len(body))
        if end < len(body):
            brk = body.rfind("\n\n", start + size // 2, end)
            if brk > start:
                end = brk
        parts.append(body[start:end].strip("\n"))
        start = end
    return parts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("book")
    ap.add_argument("out")
    ap.add_argument("--chars", type=int, default=120000)
    a = ap.parse_args()
    ext = os.path.splitext(a.book)[1].lower()
    if ext == ".epub":
        sections, files = from_epub(a.book)
    elif ext == ".pdf":
        sections, files = from_pdf(a.book)
    elif ext in (".html", ".htm", ".xhtml"):
        with open(a.book, encoding="utf-8", errors="replace") as f:
            sections, files = [(os.path.basename(a.book), html_text(f.read()))], 1
    elif ext in (".txt", ".md", ""):
        with open(a.book, encoding="utf-8", errors="replace") as f:
            sections, files = [(os.path.basename(a.book), tidy(f.read()))], 1
    else:
        sys.exit("unsupported file type: " + ext)
    os.makedirs(a.out, exist_ok=True)
    blocks = []
    for name, t in sections:
        lines = []
        for ln in t.split("\n"):
            lines.extend(wrap(ln))
        blocks.append("=== [" + name + "] ===\n" + "\n".join(lines))
    body = "\n\n".join(blocks)
    with open(os.path.join(a.out, "book.txt"), "w", encoding="utf-8") as f:
        f.write(body)
    parts = split_parts(body, a.chars)
    for n, p in enumerate(parts, 1):
        with open(os.path.join(a.out, "part%03d.txt" % n), "w", encoding="utf-8") as f:
            f.write(p)
    stats = {"book": os.path.basename(a.book), "bytes": os.path.getsize(a.book),
             "files": files, "sections": len(sections), "chars": len(body),
             "words": len(body.split()), "parts": len(parts), "chars_per_part": a.chars}
    with open(os.path.join(a.out, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
