#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import fitz
import pytesseract
from pytesseract import Output
from PIL import Image
import json, os, hashlib
from datetime import date
from slugify import slugify

INPUT_DIR = "input_pdfs"
OUTPUT_DIR = "output"
CACHE_FILE = "cache/results_cache.json"

MIN_TEXT_THRESHOLD = 30
OCR_LANGS = "eng+ind+rus+jav"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs("cache", exist_ok=True)

# ---------- UTIL ----------
def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(8192), b""):
            h.update(c)
    return h.hexdigest()

def load_cache():
    if os.path.exists(CACHE_FILE):
        return json.load(open(CACHE_FILE, "r", encoding="utf-8"))
    return {}

def save_cache(c):
    json.dump(c, open(CACHE_FILE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

# ---------- OCR ----------
def ocr_page(page):
    pix = page.get_pixmap(dpi=300)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    data = pytesseract.image_to_data(
        img, lang=OCR_LANGS, output_type=Output.DICT
    )

    lines = []
    confidences = []

    for i in range(len(data["text"])):
        txt = data["text"][i].strip()
        if txt:
            conf = int(data["conf"][i])
            lines.append({
                "text": txt,
                "confidence": max(conf, 0) / 100
            })
            confidences.append(conf)

    avg_conf = (sum(confidences) / len(confidences)) / 100 if confidences else 0
    return lines, avg_conf

# ---------- MAIN PROCESS ----------
def process_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    pages_out = []
    book_lines = []
    ocr_stats = {}

    for i, page in enumerate(doc, start=1):
        raw_text = page.get_text().strip()
        source = "text"

        lines = []
        avg_conf = 1.0

        if len(raw_text) < MIN_TEXT_THRESHOLD:
            source = "ocr"
            lines, avg_conf = ocr_page(page)
            book_lines.extend([l["text"] for l in lines])
        else:
            for ln in raw_text.splitlines():
                ln = ln.strip()
                if ln:
                    lines.append({"text": ln, "confidence": 1.0})
                    book_lines.append(ln)

        page_json = {
            "page": i,
            "source": source,
            "lines": lines,
            "pageHash": sha256_text("".join(l["text"] for l in lines))
        }

        pages_out.append(page_json)
        ocr_stats[str(i)] = {
            "source": source,
            "avgConfidence": round(avg_conf, 3)
        }

    return pages_out, book_lines, ocr_stats

# ---------- ENTRY ----------
def main():
    cache = load_cache()

    for file in os.listdir(INPUT_DIR):
        if not file.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(INPUT_DIR, file)
        pdf_hash = sha256_file(pdf_path)

        if pdf_path in cache and cache[pdf_path]["hash"] == pdf_hash:
            print("⏭ SKIP:", file)
            continue

        name = os.path.splitext(file)[0]
        slug = slugify(name)

        print("▶ FORENSIK:", file)

        pages, all_lines, ocr_stats = process_pdf(pdf_path)

        book_dir = os.path.join(OUTPUT_DIR, slug)
        pages_dir = os.path.join(book_dir, "pages")
        audit_dir = os.path.join(book_dir, "audit")

        os.makedirs(pages_dir, exist_ok=True)
        os.makedirs(audit_dir, exist_ok=True)

        # save pages
        for p in pages:
            with open(f"{pages_dir}/{p['page']:03}.json", "w", encoding="utf-8") as f:
                json.dump(p, f, ensure_ascii=False, indent=2)

        # book.json (reader)
        book = {
            "id": slug,
            "title": name,
            "created": "2025-01-01",
            "updated": date.today().isoformat(),
            "chapters": [{
                "id": "gabungan",
                "title": "Gabungan Teks",
                "order": 0,
                "estimatedMinutes": max(1, len("".join(all_lines)) // 200),
                "content": all_lines,
                "sourcePages": list(range(1, len(pages)+1))
            }]
        }

        with open(f"{book_dir}/book.json", "w", encoding="utf-8") as f:
            json.dump(book, f, ensure_ascii=False, indent=2)

        # audit
        audit = {
            "pdf": file,
            "pages": ocr_stats
        }

        with open(f"{audit_dir}/ocr_report.json", "w", encoding="utf-8") as f:
            json.dump(audit, f, ensure_ascii=False, indent=2)

        with open(f"{audit_dir}/content.sha256", "w", encoding="utf-8") as f:
            for root, _, files in os.walk(book_dir):
                for fn in files:
                    path = os.path.join(root, fn)
                    if fn.endswith(".json"):
                        f.write(f"{fn}: {sha256_file(path)}\n")

        cache[pdf_path] = {
            "hash": pdf_hash,
            "updated": date.today().isoformat(),
            "output": book_dir
        }

    save_cache(cache)
    print("✔ MODE FORENSIK SELESAI")

if __name__ == "__main__":
    main()