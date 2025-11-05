import os
import json
import re
from bs4 import BeautifulSoup
from groq import Groq

# --- KONFIGURASI ---
client = Groq(api_key=os.getenv("GROQ_API_KEY3"))
RAW_DIR = "data_raw"
OUT_DIR = "data_clean"
MODEL = "llama-3.3-70b-versatile"

# --- UTILITAS ---
def clean_text(html_content):
    """Hapus tag HTML, ambil teks bersih"""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def save_json(filename, data, subfolder=""):
    folder = os.path.join(OUT_DIR, subfolder) if subfolder else OUT_DIR
    os.makedirs(folder, exist_ok=True)
    out_path = os.path.join(folder, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Disimpan: {out_path}")

def extract_json_blocks(raw_responses):
    """Ambil semua blok JSON valid dari response Groq"""
    combined_data = {
        "Bio / Profil": {},
        "Diskografi": [],
        "Lirik": []
    }
    errors = []

    for chunk in raw_responses:
        try:
            json_texts = re.findall(r'\{.*?\}', chunk, flags=re.DOTALL)
            for jt in json_texts:
                data = json.loads(jt)
                if "bio" in data:
                    combined_data["Bio / Profil"].update(data.get("bio", {}))
                if "diskografi" in data:
                    combined_data["Diskografi"].extend(data.get("diskografi", []))
                if "lirik" in data:
                    if isinstance(data["lirik"], dict):
                        combined_data["Lirik"].append(data["lirik"])
                    else:
                        combined_data["Lirik"].extend(data["lirik"])
        except Exception as e:
            errors.append(f"JSONDecodeError: {str(e)}")
    
    return combined_data, errors

def parse_with_groq(raw_text):
    """Memanggil Groq untuk menstrukturkan data musik menjadi JSON"""
    try:
        prompt = f"""
Kamu adalah sistem yang menstrukturkan data musik dari teks mentah menjadi JSON fleksibel.
Isi data boleh kosong jika tidak ada. Jangan ubah data lama, tapi tambahkan jika ada info baru.
Keluarkan hanya JSON valid.

Teks mentah:
\"\"\"{raw_text}\"\"\"
"""
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        raw_response = completion.choices[0].message.content
        parsed_info, errors = extract_json_blocks([raw_response])

        return {
            "raw_text": raw_text,
            "parsed_info": parsed_info,
            "groq_status": "success" if not errors else "failed",
            "groq_error": errors,
            "raw_response": raw_response
        }

    except Exception as e:
        return {
            "raw_text": raw_text,
            "parsed_info": {"Bio / Profil": {}, "Diskografi": [], "Lirik": []},
            "groq_status": "failed",
            "groq_error": [str(e)],
            "raw_response": ""
        }

# --- FUNGSI SPLIT METADATA & LIRIK ---
def split_metadata_lirik(parsed_info):
    """
    Hasil parse akan dipecah menjadi:
    - metadata_album.json → info album + daftar lagu + link file lirik
    - lirik/*.json → lirik tiap lagu
    """
    metadata_album = []

    for album in parsed_info.get("Diskografi", []):
        album_entry = {
            "judul_album": album.get("judul_album", ""),
            "tahun_rilis": album.get("tahun_rilis", ""),
            "jenis_rilis": album.get("jenis_rilis", ""),
            "lokasi_syuting": album.get("lokasi_syuting", ""),
            "tema_album": album.get("tema_album", ""),
            "daftar_lagu": []
        }

        for lagu in album.get("daftar_lagu", []):
            judul_lagu = lagu.get("judul_lagu", "unknown")
            safe_file = re.sub(r"[^\w\d_-]", "_", judul_lagu) + ".json"
            link_file = f"lirik/{safe_file}"

            # Simpan file lirik per lagu
            save_json(safe_file, lagu.get("lirik", {}), subfolder="lirik")

            # Tambahkan ke metadata album
            lagu_entry = {
                "judul_lagu": judul_lagu,
                "penyanyi": lagu.get("penyanyi", ""),
                "tanggal_rilis": lagu.get("tanggal_rilis", ""),
                "link_lirik": link_file
            }
            album_entry["daftar_lagu"].append(lagu_entry)

        metadata_album.append(album_entry)

    # Simpan metadata album
    save_json("metadata_album.json", metadata_album)

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

    folder = "unknown" if result.get("groq_status") == "failed" else ""
    save_json(file.replace(".html", ".json"), result, subfolder=folder)

    if result.get("groq_status") == "success":
        split_metadata_lirik(result["parsed_info"])