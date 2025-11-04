import os
import json
import requests
from bs4 import BeautifulSoup

# Ambil API key Groq dari environment GitHub
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY belum diset di Secrets GitHub Actions.")

HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

# Direktori output
os.makedirs("data_clean", exist_ok=True)

# File input (misal berisi list URL lagu)
input_file = "data_raw/links.json"

if not os.path.exists(input_file):
    print("⚠️ File input tidak ditemukan: data_raw/links.json")
    exit(0)

with open(input_file, "r", encoding="utf-8") as f:
    links = json.load(f)

# Fungsi untuk ambil HTML
def fetch_html(url):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.text
    except Exception as e:
        print(f"❌ Gagal ambil {url}: {e}")
    return None

# Fungsi untuk bersihkan lirik dari HTML
def clean_lyrics(html):
    soup = BeautifulSoup(html, "html.parser")

    # Hapus script/style
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()

    # Cari teks utama
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines[:2000])  # batasi panjang teks

# Fungsi untuk minta Groq mem-parsing isi
def parse_with_groq(text, url):
    prompt = f"""
Kamu adalah sistem ekstraksi informasi lagu.
Ambil dan strukturkan data dari teks berikut ke dalam JSON.

Teks dari: {url}

Output JSON harus berformat seperti ini:
{{
  "title": "...",
  "artist": "...",
  "album": "...",
  "label": "...",
  "release_date": "...",
  "lyrics_romaji": "...",
  "lyrics_kanji": "...",
  "lyrics_english": "...",
  "cover_image": "...",
  "youtube": "...",
  "source": "{url}"
}}

Berikut teks yang harus kamu analisis:

{text}
"""

    payload = {
        "model": "llama-3.1-70b-versatile",
        "messages": [
            {"role": "system", "content": "Kamu adalah asisten ekstraksi data lagu yang akurat."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    try:
        res = requests.post("https://api.groq.com/openai/v1/chat/completions",
                            headers=HEADERS, json=payload, timeout=60)
        data = res.json()
        reply = data["choices"][0]["message"]["content"]

        # Coba ubah ke JSON langsung
        try:
            parsed = json.loads(reply)
        except:
            parsed = {"raw_output": reply}

        return parsed
    except Exception as e:
        return {"error": str(e)}

# Jalankan parsing semua link
for i, url in enumerate(links, start=1):
    print(f"\n🔍 [{i}/{len(links)}] Parsing: {url}")

    html = fetch_html(url)
    if not html:
        print("⛔ Skip karena gagal ambil HTML")
        continue

    text = clean_lyrics(html)
    parsed = parse_with_groq(text, url)

    # Simpan hasil
    filename = f"data_clean/{str(i).zfill(4)}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)

    print(f"✅ Tersimpan: {filename}")

print("\n🎉 Semua proses selesai!")