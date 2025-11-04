from groq import Groq
import os, json, glob

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def parse_with_groq(text):
    prompt = f"""
Kamu adalah asisten yang menata data musik/artis dari HTML atau teks mentah.
Ekstrak semua informasi ke format JSON terstruktur seperti ini:

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
        model="llama-3.2-70b-versatile",  # ganti ke model baru
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    return completion.choices[0].message.content