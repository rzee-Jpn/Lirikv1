import os
import json
from groq import Groq
from bs4 import BeautifulSoup

# --- KONFIGURASI ---
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
RAW_DIR = "data_raw"
OUT_DIR = "data_clean"
MODEL = "llama-3.3-70b-versatile"

# --- UTILITAS ---
def clean_text(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def save_json(artist, album, data):
    artist_folder = os.path.join(OUT_DIR, artist)
    os.makedirs(artist_folder, exist_ok=True)
    out_path = os.path.join(artist_folder, f"{album}.json")

    if os.path.exists(out_path):
        with open(out_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        existing["parsed_info"]["Diskografi"].extend(data["parsed_info"]["Diskografi"])
        data = existing

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Disimpan: {out_path}")

def parse_with_groq(raw_text):
    prompt = f"""
Kamu adalah sistem yang menstrukturkan data musik dari teks mentah menjadi JSON dengan format berikut:

{{
  "raw_text": "...",
  "parsed_info": {{
    "Bio / Profil": {{
      "Nama lengkap & nama panggung": "",
      "Asal / domisili": "",
      "Tanggal lahir": "",
      "Genre musik": "",
      "Influences / inspirasi": "",
      "Cerita perjalanan musik": "",
      "Foto profil": "",
      "Link media sosial": ""
    }},
    "Diskografi": [
      {{
        "Nama album/single": "",
        "Tanggal rilis": "",
        "Label": "",
        "Jumlah lagu": "",
        "Cover art": "",
        "Produksi oleh / kolaborator tetap": "",
        "Lagu / Song List": [
          {{
            "Judul lagu": "",
            "Composer": "",
            "Lyricist": "",
            "Featuring": "",
            "Tahun rilis": "",
            "Album asal": "",
            "Durasi": "",
            "Genre": "",
            "Key": "",
            "Chord & lyrics": "",
            "Terjemahan": ""
          }}
        ]
      }}
    ]
  }}
}}

Teks mentah:
\"\"\"{raw_text}\"\"\"

Keluarkan hanya JSON valid.
"""
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return completion.choices[0].message.content

# --- PROSES UTAMA ---
for file in os.listdir(RAW_DIR):
    if not file.endswith(".html"):
        continue
    file_path = os.path.join(RAW_DIR, file)
    print(f"🧠 Memproses: {file}")

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    text = clean_text(html)
    try:
        json_text = parse_with_groq(text)
        data = json.loads(json_text)
        artist = data["parsed_info"]["Bio / Profil"]["Nama lengkap & nama panggung"] or "Unknown"
        album = data["parsed_info"]["Diskografi"][0]["Nama album/single"] or os.path.splitext(file)[0]
        save_json(artist.strip().replace(" ", "_"), album.strip().replace(" ", "_"), data)
    except Exception as e:
        print(f"⚠️ Gagal memproses {file}: {e}")