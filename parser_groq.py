import os
import json
from groq import Groq

# Inisialisasi client Groq
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Folder input/output
data_raw_dir = "data_raw"
data_clean_dir = "data_clean"
os.makedirs(data_clean_dir, exist_ok=True)

# Ambil semua file HTML di data_raw
files = [f for f in os.listdir(data_raw_dir) if f.endswith(".html")]

if not files:
    print("❌ Tidak ada file HTML di folder data_raw/")
    exit()

for filename in files:
    path = os.path.join(data_raw_dir, filename)
    print(f"🧠 Memproses: {filename}")

    with open(path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Prompt untuk model Groq
    prompt = f"""
Kamu adalah parser musik pintar.
Ekstrak data lagu dari HTML berikut:
- Judul lagu
- Artis
- Album
- Label
- Tanggal rilis
- Lirik (Romaji, Kanji, English jika ada)
- Link gambar cover
- Link YouTube (jika ada)

Balas dalam format JSON valid seperti ini:
{{
  "title": "",
  "artist": "",
  "album": "",
  "label": "",
  "release_date": "",
  "lyrics": {{
    "romaji": "",
    "kanji": "",
    "english": ""
  }},
  "cover": "",
  "youtube": "",
  "source": "{filename}"
}}

HTML:
{html_content[:4000]}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        text = response.choices[0].message.content.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Jika tidak valid JSON, simpan mentah
            data = {"raw_output": text, "source": filename}

        out_path = os.path.join(data_clean_dir, filename.replace(".html", ".json"))
        with open(out_path, "w", encoding="utf-8") as out_f:
            json.dump(data, out_f, ensure_ascii=False, indent=2)

        print(f"✅ Selesai: {out_path}")

    except Exception as e:
        print(f"⚠️ Gagal memproses {filename}: {e}")