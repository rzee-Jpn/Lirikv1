import os
import json
from groq import Groq

# ============================================================
#  GROQ MUSIC PARSER - MULTI ARTIST & MULTI ALBUM
# ============================================================

# Inisialisasi klien Groq
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Folder input/output
raw_root = "data_raw"
clean_root = "data_clean"
os.makedirs(clean_root, exist_ok=True)

# ============================================================
#  LOOP ARTIST DAN ALBUM
# ============================================================

for artist_name in os.listdir(raw_root):
    artist_path = os.path.join(raw_root, artist_name)
    if not os.path.isdir(artist_path):
        continue

    print(f"\n🎤 Memproses artis: {artist_name}")
    os.makedirs(os.path.join(clean_root, artist_name), exist_ok=True)

    # Loop album/single (subfolder dalam artis)
    for album_name in os.listdir(artist_path):
        album_path = os.path.join(artist_path, album_name)
        if not os.path.isdir(album_path):
            continue

        print(f"💿 Album: {album_name}")

        # Gabungkan semua HTML/text di dalam album jadi satu
        combined_text = ""
        for file_name in os.listdir(album_path):
            if file_name.endswith(".html") or file_name.endswith(".txt"):
                file_path = os.path.join(album_path, file_name)
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    combined_text += f"\n\n---- {file_name} ----\n"
                    combined_text += f.read()

        if not combined_text.strip():
            print(f"⚠️ Tidak ada file HTML/TXT ditemukan di {album_name}")
            continue

        # ============================================================
        #  PROMPT GROQ UNTUK PEMBENTUKAN JSON TERSTRUKTUR
        # ============================================================

        prompt = f"""
Kamu adalah sistem ekstraksi data musik.
Analisis teks/HTML berikut dan ubah menjadi JSON dengan struktur yang konsisten.

Keluaran harus dalam format JSON:
{{
  "raw_text": "<salin seluruh isi text>",
  "parsed_info": {{
    "Bio / Profil": {{
      "Nama lengkap & nama panggung": "",
      "Asal / domisili": "",
      "Tanggal lahir": "",
      "Genre musik": "",
      "Influences / inspirasi": "",
      "Cerita perjalanan musik": "",
      "Foto profil": "",
      "Link media sosial": {{
        "YouTube": "",
        "Spotify": "",
        "Instagram": "",
        "BandLab": ""
      }}
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

Teks/HTML untuk diproses:
{combined_text}
"""

        # ============================================================
        #  PANGGIL API GROQ
        # ============================================================

        try:
            response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )

            content = response.choices[0].message.content.strip()

            # ============================================================
            #  CEK VALIDITAS OUTPUT
            # ============================================================
            try:
                parsed_json = json.loads(content)
            except json.JSONDecodeError:
                # Jika bukan JSON valid, bungkus manual
                parsed_json = {"raw_text": combined_text, "parsed_info": content}

            # ============================================================
            #  SIMPAN KE FOLDER data_clean/<ARTIST>/<ALBUM>.json
            # ============================================================

            output_path = os.path.join(clean_root, artist_name, f"{album_name}.json")

            # Jika file sudah ada → merge update
            if os.path.exists(output_path):
                with open(output_path, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                if (
                    "parsed_info" in old_data
                    and "Diskografi" in old_data["parsed_info"]
                    and "parsed_info" in parsed_json
                    and "Diskografi" in parsed_json["parsed_info"]
                ):
                    old_data["parsed_info"]["Diskografi"].extend(
                        parsed_json["parsed_info"]["Diskografi"]
                    )
                parsed_json = old_data

            with open(output_path, "w", encoding="utf-8") as out:
                json.dump(parsed_json, out, ensure_ascii=False, indent=2)

            print(f"✅ Disimpan ke: {output_path}")

        except Exception as e:
            print(f"❌ Error pada {artist_name}/{album_name}: {e}")

# ============================================================
#  SELESAI
# ============================================================

print("\n🎯 Parsing selesai untuk semua artis & album di data_raw/")