# main.py
import os
import glob
from pathlib import Path
from .parser import parse_txt, parse_csv, parse_html
from .smart_merger import merge_song_into_artist
from scripts.utils import save_json, load_json, safe_slug, now_iso, guess_artist_from_filename

DATA_DIR = Path('datalake')
ARTISTS_DIR = Path('artists')
ARTISTS_DIR.mkdir(exist_ok=True)

SUPPORTED = ['.txt', '.csv', '.html', '.htm']


def build_song_obj(parsed, source_file):
    # normalized song object
    artist = parsed.get('artist') or guess_artist_from_filename(source_file)
    return {
        'title': parsed.get('title') or parsed.get('judul') or '',
        'artist': artist,
        'album': parsed.get('album') or '',
        'release_date': parsed.get('release_date') or parsed.get('rilis') or '',
        'lyrics': parsed.get('lyrics') or '',
        'translations': parsed.get('translations') or [],
        'extra_info': parsed.get('extra_info') or {},
        'lirik_meta': parsed.get('lirik_meta') or {},
        'fetched_at': now_iso(),
        'confidence': parsed.get('confidence') or {}
    }


def process_file(path):
    ext = path.suffix.lower()
    parsed = {}
    if ext == '.txt':
        parsed = parse_txt(str(path))
    elif ext == '.csv':
        parsed = parse_csv(str(path))
    elif ext in ('.html', '.htm'):
        parsed = parse_html(str(path))
    else:
        return

    song = build_song_obj(parsed, str(path))

    artist_slug = safe_slug(song['artist'])
    artist_path = ARTISTS_DIR / f"{artist_slug}.json"
    existing = load_json(str(artist_path)) or None
    merged_artist = merge_song_into_artist(existing, song)
    save_json(str(artist_path), merged_artist)
    print(f"Merged: {song['title']} -> {artist_slug}.json")


if __name__ == '__main__':
    files = [Path(p) for p in glob.glob(str(DATA_DIR / '*')) if Path(p).suffix.lower() in SUPPORTED]
    for f in files:
        try:
            process_file(f)
        except Exception as e:
            print(f"Error processing {f}: {e}")
