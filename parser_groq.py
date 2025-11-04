import os
import json
import time
from groq import Groq
from bs4 import BeautifulSoup

# --- KONFIGURASI ---
RAW_DIR = "data_raw"
OUT_DIR = "data_clean"
MODEL = os.getenv("MODEL", "llama-3.3-70b-versatile")
API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=API_KEY)

# --- UTILITAS ---
def clean_text(html_content):
    """Membersihkan HTML jadi teks mentah."""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def save_json(artist, album, data):
    """Menyimpan hasil JSON ke folder per artis."""
    artist_folder = os.path.join(OUT_DIR, artist)
    os.makedirs(artist_folder, exist_ok=True)
    out_path = os.path.join(artist_folder, f"{album}.json")

    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            existing["parsed_info"]["Diskografi"].extend(data["parsed_info"]["Diskografi"])
            data = existing
        except Exception:
            pass

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Disimpan: {out_path}")

def parse_with_groq(raw_text, retry=3):
    """Memanggil Groq API dengan retry dan error handling."""
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

    for attempt in range(1, retry + 1):
        try:
            completion = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            result = completion.choices[0].message.content.strip()
            if not result:
                raise ValueError("Respons kosong dari Groq.")
            return result
        except Exception as e:
            print(f"⚠️ Percobaan {attempt} gagal: {e}")
            if attempt < retry:
                time.sleep(2)
            else:
                raise

# --- PROSES UTAMA ---
for file in os.listdir(RAW_DIR):
    if not file.endswith(".html"):
        continue
    file_path = os.path.join(RAW_DIR, file)
    print(f"🧠 Memproses: {file}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            html = f.read().strip()
        if not html:
            print(f"⚠️ File {file} kosong, dilewati.")
            continue

        text = clean_text(html)
        json_text = parse_with_groq(text)

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            print(f"⚠️ JSON tidak valid untuk {file}, menyimpan teks mentah.")
            data = {
                "raw_text": text,
                "parsed_info": {"Bio / Profil": {}, "Diskografi": []}
            }

        artist = data["parsed_info"].get("Bio / Profil", {}).get("Nama lengkap & nama panggung", "Unknown") or "Unknown"
        album = (
            data["parsed_info"]
            .get("Diskografi", [{}])[0]
            .get("Nama album/single", os.path.splitext(file)[0])
        )

        save_json(artist.strip().replace(" ", "_"), album.strip().replace(" ", "_"), data)

    except Exception as e:
        print(f"⚠️ Gagal memproses {file}: {e}")