import os, json, glob
from groq import Groq

# === KONFIGURASI ===
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
RAW_DIR = "data_raw"
CLEAN_DIR = "data_clean"

# === PASTIKAN FOLDER ADA ===
os.makedirs(CLEAN_DIR, exist_ok=True)

def parse_with_groq(text):
    prompt = f"""
Kamu adalah AI yang menata data musik/artis dari HTML mentah menjadi JSON terstruktur.
Gunakan format seperti ini:

{{
  "raw_text": "<isi text>",
  "parsed_info": {{
    "Bio / Profil": {{
      "Nama lengkap & nama panggung": "",
      "Asal / domisili": "",
      "Tanggal lahir": "",
      "Genre musik": "",
      "Influences / inspirasi": "",
      "Cerita perjalanan musik": "",
      "Foto profil": "",
      "Link media sosial": {{}}
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
Hasilkan hanya JSON valid tanpa penjelasan tambahan.

Teks mentah:
{text}
"""
    completion = client.chat.completions.create(
        model="llama-3.2-70b-versatile",  # gunakan model baru
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return completion.choices[0].message.content


def safe_filename(name: str):
    """Ubah nama jadi aman untuk file path."""
    return "".join(c if c.isalnum() or c in "_-" else "_" for c in name.strip())


# === LOOP SEMUA FILE ===
for html_file in glob.glob(os.path.join(RAW_DIR, "*.html")):
    print(f"🧠 Memproses: {os.path.basename(html_file)}")

    try:
        with open(html_file, "r", encoding="utf-8") as f:
            text = f.read()

        result_json = parse_with_groq(text)
        result = json.loads(result_json)

        # Ambil info artis & album
        artis = result["parsed_info"]["Bio / Profil"].get("Nama lengkap & nama panggung", "Unknown")
        album = result["parsed_info"]["Diskografi"][0].get("Nama album/single", "Unknown_Album")

        # Buat folder per-artis
        artist_folder = os.path.join(CLEAN_DIR, safe_filename(artis))
        os.makedirs(artist_folder, exist_ok=True)

        # Simpan file per album
        output_path = os.path.join(artist_folder, f"{safe_filename(album)}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"✅ Sukses: {output_path}")

    except Exception as e:
        print(f"⚠️ Gagal memproses {html_file}: {e}")