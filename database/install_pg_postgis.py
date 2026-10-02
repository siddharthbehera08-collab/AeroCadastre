from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import shutil
import struct
import subprocess
import tarfile
import zipfile
import zlib

DB_DIR = Path("D:/SIH26012_AeroCadastre/database")
DL_DIR = DB_DIR / "downloads"
PG_DIR = DB_DIR / "pgsql"
PG_JAR = DL_DIR / "pg16.jar"
ZIP_CD = DL_DIR / "zip_cd.bin"
PARTIAL_ZIP = DL_DIR / "postgis_pg16.zip"
URL = "https://download.osgeo.org/postgis/windows/pg16/postgis-bundle-pg16-3.6.2x64.zip"


def ensure_postgres_extracted() -> None:
    if (PG_DIR / "bin" / "postgres.exe").exists():
        print("PostgreSQL 16.4 binaries already extracted.")
        return
    PG_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(PG_JAR, "r") as zf:
        txz_names = [n for n in zf.namelist() if n.endswith(".txz")]
        txz_path = DL_DIR / txz_names[0]
        if not txz_path.exists():
            zf.extract(txz_names[0], DL_DIR)
    print("Extracting PostgreSQL 16.4 txz archive...", flush=True)
    with tarfile.open(txz_path, "r:xz") as tf:
        tf.extractall(PG_DIR)
    print("PostgreSQL 16.4 extracted:", (PG_DIR / "bin" / "postgres.exe").exists(), flush=True)


def parse_central_directory() -> list[tuple[str, int, int, int, int]]:
    cd = ZIP_CD.read_bytes()
    pos = 0
    entries = []
    while pos < len(cd) - 46:
        if cd[pos : pos + 4] != b"PK\x01\x02":
            break
        vals = struct.unpack("<4sHHHHHHIIIHHHHHII", cd[pos : pos + 46])
        comp_method = vals[4]
        comp_size = vals[8]
        uncomp_size = vals[9]
        fname_len, extra_len, comment_len = vals[10], vals[11], vals[12]
        local_offset = vals[16]
        fname = cd[pos + 46 : pos + 46 + fname_len].decode("utf-8", "ignore")
        entries.append((fname, comp_method, comp_size, uncomp_size, local_offset))
        pos += 46 + fname_len + extra_len + comment_len
    return entries


def should_extract(fname: str) -> bool:
    if fname.endswith("/"):
        return False
    rel = fname.split("/", 1)[1] if "/" in fname else fname
    if rel.startswith("bin/") and rel.count("/") == 1 and rel.endswith(".dll"):
        dll_name = rel.split("/")[1]
        if dll_name in ("libgdal-35.dll", "libSFCGAL.dll"):
            return False
        return True
    if rel in (
        "lib/postgis-3.dll",
        "lib/postgis_topology-3.dll",
        "share/contrib/postgis-3.6/proj/proj.db",
        "share/contrib/postgis-3.6/proj/proj.ini",
        "share/contrib/postgis-3.6/spatial_ref_sys.sql",
        "share/extension/postgis.control",
        "share/extension/postgis--3.6.2.sql",
        "share/extension/postgis_topology.control",
        "share/extension/postgis_topology--3.6.2.sql",
    ):
        return True
    return False


def fetch_range_bytes(start: int, end: int) -> bytes:
    if PARTIAL_ZIP.exists() and PARTIAL_ZIP.stat().st_size > end:
        with open(PARTIAL_ZIP, "rb") as f:
            f.seek(start)
            return f.read(end - start + 1)

    chunk_size = 128 * 1024
    ranges = []
    cur = start
    while cur <= end:
        r_end = min(cur + chunk_size - 1, end)
        ranges.append((cur, r_end))
        cur = r_end + 1

    def _download_subrange(r: tuple[int, int]) -> tuple[int, bytes]:
        s, e = r
        cmd = [
            "curl.exe",
            "-s",
            "--retry",
            "5",
            "--retry-delay",
            "1",
            "-r",
            f"{s}-{e}",
            URL,
        ]
        res = subprocess.run(cmd, capture_output=True, check=True, timeout=60)
        return s, res.stdout

    if len(ranges) == 1:
        _, data = _download_subrange(ranges[0])
        return data

    parts = {}
    with ThreadPoolExecutor(max_workers=min(len(ranges), 12)) as pool:
        futs = [pool.submit(_download_subrange, r) for r in ranges]
        for fut in as_completed(futs):
            s, data = fut.result()
            parts[s] = data
    return b"".join(parts[r[0]] for r in ranges)


def extract_entry(entry: tuple[str, int, int, int, int]) -> str:
    fname, comp_method, comp_size, uncomp_size, local_offset = entry
    rel = fname.split("/", 1)[1]
    target = PG_DIR / rel
    if target.exists() and target.stat().st_size == uncomp_size:
        return f"SKIP {rel}"

    end_offset = local_offset + 30 + len(fname.encode("utf-8")) + 256 + comp_size
    raw = fetch_range_bytes(local_offset, end_offset)
    if raw[:4] != b"PK\x03\x04":
        raise RuntimeError(f"Invalid local header for {rel}")
    _, _, _, _, _, _, _, _, _, lf_fname_len, lf_extra_len = struct.unpack("<4sHHHHHIIIHH", raw[:30])
    data_start = 30 + lf_fname_len + lf_extra_len
    comp_data = raw[data_start : data_start + comp_size]

    if comp_method == 0:
        out_data = comp_data
    elif comp_method == 8:
        out_data = zlib.decompress(comp_data, -15)
    else:
        raise RuntimeError(f"Unsupported compression method {comp_method} for {rel}")

    if len(out_data) != uncomp_size:
        raise RuntimeError(f"Size mismatch for {rel}: got {len(out_data)}, expected {uncomp_size}")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(out_data)
    return f"OK {rel} ({uncomp_size // 1024} KB)"


def main() -> None:
    ensure_postgres_extracted()
    entries = parse_central_directory()
    selected = [e for e in entries if should_extract(e[0])]
    print(f"Selected {len(selected)} core PostGIS 3.6.2 files ({sum(e[2] for e in selected)/1024/1024:.2f} MB compressed)", flush=True)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {pool.submit(extract_entry, e): e[0] for e in selected}
        for fut in as_completed(futs):
            print(" ", fut.result(), flush=True)

    print("PostGIS 3.6.2 core extraction complete!", flush=True)


if __name__ == "__main__":
    main()
