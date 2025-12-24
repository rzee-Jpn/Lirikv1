#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import fitz
import pytesseract
from PIL import Image
import json, os, hashlib
from datetime import date
from slugify import slugify

INPUT_DIR = "input_pdfs"
OUTPUT_DIR = "output"
CACHE_FILE = "cache/results_cache.json"

MIN_TEXT_THRESHOLD = 30

BOOK_TEMPLATE = {
    "subtitle": "Antologi Teks dan Ingatan Peradaban",
    "author": "Anonim",
    "publisher": "Arsip Digital Nusantara",
    "language": "multi",
    "readingDirection": "ltr",
    "settings": {
        "defaultTheme": "paper",
        "defaultFontSize": 17,
        "enableTTS": True,
        "enableBookmark": True
    }
}

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def ocr_page(page):
    pix = page.get_pixmap(dpi=300)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return pytesseract.image_to_string(img)

def normalize_paragraphs(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    paragraphs, buf = [], ""

    for line in lines:
        if len(line) < 80:
            if buf:
                paragraphs.append(buf.strip())
                buf = ""
            paragraphs.append(line)
        else:
            buf += " " + line

    if buf:
        paragraphs.append(buf.strip())

    return paragraphs

def estimate_minutes(paragraphs):
    chars = sum(len(p) for p in paragraphs)
    return max(1, chars // 200)

def process_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    texts = []

    for page in doc:
        t = page.get_text().strip()
        if len(t) < MIN_TEXT_THRESHOLD:
            t = ocr_page(page)
        texts.append(t)

    full_text = "\n".join(texts)
    paragraphs = normalize_paragraphs(full_text)

    chapter = {
        "id": "gabungan",
        "title": "Gabungan Teks",
        "order": 0,
        "estimatedMinutes": estimate_minutes(paragraphs),
        "content": paragraphs
    }

    name = os.path.splitext(os.path.basename(pdf_path))[0]
    slug = slugify(name)

    book = {
        "id": slug,
        "title": name.replace("-", " ").title(),
        "created": "2025-01-01",
        "updated": date.today().isoformat(),
        **BOOK_TEMPLATE,
        "chapters": [chapter]
    }

    return book, slug

def main():
    cache = load_cache()

    for file in os.listdir(INPUT_DIR):
        if not file.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(INPUT_DIR, file)
        pdf_hash = file_hash(pdf_path)

        if pdf_path in cache and cache[pdf_path]["hash"] == pdf_hash:
            print("⏭ SKIP (cached):", file)
            continue

        print("▶ Proses:", file)
        book, slug = process_pdf(pdf_path)

        book_dir = os.path.join(OUTPUT_DIR, slug)
        os.makedirs(book_dir, exist_ok=True)

        out_file = os.path.join(book_dir, "book.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(book, f, ensure_ascii=False, indent=2)

        cache[pdf_path] = {
            "hash": pdf_hash,
            "updated": date.today().isoformat(),
            "output": out_file
        }

    save_cache(cache)
    print("✔ Batch selesai")

if __name__ == "__main__":
    main()
