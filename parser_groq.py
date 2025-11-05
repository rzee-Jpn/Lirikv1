import os
import json
from groq import Groq
from bs4 import BeautifulSoup
import textwrap

# --- KONFIGURASI ---
client = Groq(api_key=os.getenv("GROQ_API_KEY1"))
RAW_DIR = "data_raw"
OUT_DIR = "data_clean"
MODEL = "llama-3.3-70b-versatile"
MAX_CHARS_PER_PROMPT = 3000  # bagi teks panjang

# --- UTILITAS ---
def clean_text(html_content):
    """Bersihkan HTML menjadi teks mentah"""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def save_json(filename, data, subfolder=""):
    """Simpan data JSON ke folder yang sesuai"""
    folder = os.path.join(OUT_DIR, subfolder) if subfolder else OUT_DIR
    os.makedirs(folder, exist_ok=True)
    out_path = os.path.join(folder, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Disimpan: {out_path}")

def clean_groq_response(groq_text):
    """Hilangkan blok markdown ```json …``` jika ada"""
    if groq_text.strip().startswith("```json"):
        groq_text = groq_text.strip()
        groq_text = groq_text[len("```json"):].rstrip("` \n")
    return groq_text

def parse_with_groq(raw_text):
    """Memanggil Groq untuk memparsing teks panjang secara aman"""
    try:
        # Bagi teks panjang agar tidak melebihi limit
        chunks = textwrap.wrap(raw_text, MAX_CHARS_PER_PROMPT)
        parsed_chunks = []

        for chunk in chunks:
            prompt = f"""
Kamu adalah sistem yang menstrukturkan data musik dari teks mentah menjadi JSON fleksibel.
Isi data boleh kosong jika tidak ada. Jangan ubah data lama, tapi tambahkan jika ada info baru.
Keluarkan hanya JSON valid.

Teks mentah:
\"\"\"{chunk}\"\"\"
"""
            completion = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            groq_text = completion.choices[0].message.content
            parsed_chunks.append(groq_text)

        # Gabungkan hasil chunk
        combined_json = {
            "raw_text": raw_text,
            "parsed_info": {"Bio / Profil": {}, "Diskografi": [], "Lirik": []},
            "groq_status": "success",
            "raw_response": parsed_chunks
        }

        # Parsing setiap chunk menjadi JSON
        for chunk_text in parsed_chunks:
            chunk_text_clean = clean_groq_response(chunk_text)
            try:
                chunk_data = json.loads(chunk_text_clean)
                # Gabungkan Bio / Profil
                combined_json["parsed_info"]["Bio / Profil"].update(
                    chunk_data.get("bio", {})
                )
                # Gabungkan Diskografi
                combined_json["parsed_info"]["Diskografi"].extend(
                    chunk_data.get("diskografi", [])
                )
                # Gabungkan Lirik
                combined_json["parsed_info"]["Lirik"].extend(
                    chunk_data.get("lirik", [])
                )
            except json.JSONDecodeError:
                combined_json["groq_status"] = "failed"
                combined_json.setdefault("groq_error", []).append(
                    "JSONDecodeError setelah clean response"
                )

        return combined_json

    except Exception as e:
        return {
            "raw_text": raw_text,
            "parsed_info": {"Bio / Profil": {}, "Diskografi": [], "Lirik": []},
            "groq_status": "failed",
            "groq_error": str(e),
            "raw_response": []
        }

# --- PROSES UTAMA ---
for file in os.listdir(RAW_DIR):
    if not file.endswith(".html"):
        continue

    file_path = os.path.join(RAW_DIR, file)
    print(f"🧠 Memproses: {file}")

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    text = clean_text(html)
    result = parse_with_groq(text)

    # Tentukan folder: unknown jika gagal
    folder = "unknown" if result.get("groq_status") == "failed" else ""
    save_json(file.replace(".html", ".json"), result, subfolder=folder)