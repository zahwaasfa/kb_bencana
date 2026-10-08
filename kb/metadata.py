"""Parser metadata Data Bencana & Kerusakan Infrastruktur (BPBD DKJ) -> dokumen terstruktur + blok teks hierarkis.
Diselaraskan murni untuk skema generik terpadu 11 label."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

MONTHS = {"januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
          "september": 9, "oktober": 10, "november": 11, "desember": 12}
KNOWN_EXT = {"pdf", "xlsx", "xls", "csv", "docx", "doc", "pptx", "ppt", "txt", "md", "json"}
SHEET_KEY = "Metadata_Data_Bencana_DKJ"
PROV = "Provinsi DKJ"
KOTA = {"jakarta pusat": "Jakarta Pusat", "jakarta utara": "Jakarta Utara", "jakarta barat": "Jakarta Barat",
        "jakarta selatan": "Jakarta Selatan", "jakarta timur": "Jakarta Timur", "kepulauan seribu": "Kepulauan Seribu"}


def clean(v) -> str:
    if v is None:
        return ""
    s = str(v).replace("_x000D_", "").replace("\t", " ").strip().strip('"').strip()
    return "" if s in {"-", "–", "nan", "None", "NaN"} else s


def hid(prefix: str, s: str) -> str:
    return f"{prefix}_{hashlib.sha1(s.lower().strip().encode()).hexdigest()[:8]}"


def parse_date(s) -> str | None:
    s = clean(s)
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m[1]}-{m[2]}-{m[3]}"
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", s)
    if m and m[2].lower() in MONTHS:
        return f"{m[3]}-{MONTHS[m[2].lower()]:02d}-{int(m[1]):02d}"
    return None


def split_tags(s) -> list[str]:
    seen, out = set(), []
    for t in re.split(r"[,;\n]", clean(s)):
        t = t.strip().lower()
        if t and t not in seen:
            seen.add(t); out.append(t)
    return out


def detect_locations(text: str, region: str = PROV) -> list[dict]:
    locs = {PROV: {"name": PROV, "level": "provinsi", "code": "32010026", "parent": None}}
    low = text.lower()
    for k, v in KOTA.items():
        if k in low:
            locs[v] = {"name": v, "level": "kabupaten" if v == "Kepulauan Seribu" else "kota", "code": None, "parent": PROV}
    for m in re.finditer(r"\b(Kecamatan|Kelurahan)\s+([A-Z][\w]+(?:\s+[A-Z][\w]+){0,2})", text):
        nm = f"{m[1]} {m[2]}"
        locs[nm] = {"name": nm, "level": m[1].lower(), "code": None, "parent": PROV}
    return list(locs.values())


def extract_facts(text: str) -> dict:
    return {}


def normalise(row: dict, idx: int) -> dict:
    g = lambda k: clean(row.get(k))
    title, fname = g("judul"), g("nama_file")
    m = re.search(r"\.([A-Za-z0-9]{2,4})$", fname)
    ext = m.group(1).lower() if m and m.group(1).lower() in KNOWN_EXT else ""
    cat, sub, desc = g("kategori_data"), g("sub_kategori"), g("deskripsi")
    tags = split_tags(row.get("tag"))
    
    code = (re.search(r"\[(\d+)\]", g("isian_klasifikasi")) or [None, None])[1]
    locs = detect_locations(f"{title} {desc}")
    if code:
        locs[0]["code"] = code
    inst, src = g("instansi") or "BPBD Provinsi DKJ", g("sumber_data")
    refs = []
    for part in [p.strip() for p in re.split(r"/|;", src) if p.strip()]:
        if part.lower() != inst.lower():
            refs.append({"ref_id": hid("SRC", part), "title": part, "ref_type": "Data Sekunder"})
    year = g("tahun")
    yy = re.search(r"\b(19|20)\d{2}\b", year) or re.search(r"\b(19|20)\d{2}\b", title)
    
    return {
        "doc_id": g("id") or f"DOC-{idx:03d}", "title": title, "file_name": fname,
        "file_type": g("jenis_file") or (ext.upper() if ext else "Tidak diketahui"),
        "output_type": g("ukuran") or "Lainnya", "knowledge_type": g("isian_klasifikasi"), "description": desc, "benefit": "",
        "classification": g("klasifikasi_data"), "access_rights": g("sifat_data"), "document_url": "",
        "publish_date": parse_date(row.get("metadata_dibuat")), "year": year or (yy.group(0) if yy else ""),
        "domain": "bencana", "category": cat, "subcategory": sub, "unit_kerja": "", "unit": None, "division": None,
        "tags": tags, "refs": refs, "steps": [], "partners": [],
        "org": {"org_id": hid("ORG", inst), "name": inst, "org_type": "Pemerintah Daerah", "kontak": g("kontak")},
        "locations": locs, "disasters": [sub] if sub else [], "infrastructure": [], "unit_measure": g("satuan"),
        "labels": [],
        "extra": {"satuan": g("satuan"), "ukuran": g("ukuran"), "sumber_data": src, "instansi": inst, "wilayah": g("wilayah"),
                  "jadwal_pemutakhiran": g("jadwal_pemutakhiran"), "metadata_diperbarui": parse_date(row.get("metadata_diperbarui")) or "",
                  "filedata_diperbarui": parse_date(row.get("filedata_diperbarui")) or "", "tags_text": " ".join(tags)},
    }


def load_docs(path: Path) -> list[dict]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        rows = raw.get(SHEET_KEY) or next(v for v in raw.values() if isinstance(v, list) and v and isinstance(v[0], dict) and "judul" in v[0])
    else:
        rows = raw
    return [normalise(r, i) for i, r in enumerate(rows, 1) if clean(r.get("judul"))]


def H(level: int, text: str) -> dict:
    return {"kind": "h", "level": level, "text": text, "page": None}


def P(text: str, section: str, item: int | None = None) -> dict:
    return {"kind": "p", "text": text, "page": None, "atomic": True, "section": section, "item": item}


def identity_text(d: dict) -> str:
    s = (f'Dataset "{d["title"]}" berformat {d["file_type"]}, kategori {d["category"] or "-"} (sub-kategori {d["subcategory"] or "-"}), '
         f'tahun data {d["year"] or "tidak dicatat"}, wilayah {d["extra"]["wilayah"] or PROV}, diterbitkan oleh {d["extra"]["instansi"]}. '
         f'Sifat data: {d["access_rights"] or "tidak dicatat"}.')
    return s


def metadata_blocks(d: dict) -> list[dict]:
    t, x, b = d["title"], d["extra"], [H(1, "Ringkasan Dataset"), P(identity_text(d), "identitas")]
    if d["description"]:
        b.append(P(f'Deskripsi dataset "{t}": {d["description"]}', "deskripsi"))
    b.append(H(1, "Cakupan dan Pengukuran"))
    b.append(P(f'Cakupan dataset "{t}": wilayah {", ".join(l["name"] for l in d["locations"])}; tahun {d["year"] or "tidak dicatat"}; '
               f'jenis tabulasi {d["output_type"]}; satuan {x["satuan"] or "tidak dicatat"}.', "cakupan"))
    b.append(H(1, "Sumber dan Klasifikasi"))
    b.append(P(f'Sumber data "{t}": {x["sumber_data"] or x["instansi"]}; penerbit {x["instansi"]}; klasifikasi data {d["classification"] or "-"}; '
               f'isian klasifikasi {d["knowledge_type"] or "-"}; hak akses {d["access_rights"] or "-"}.', "sumber"))
    if d["disasters"] or d["infrastructure"]:
        b.append(H(1, "Jenis Bencana dan Infrastruktur Terdampak"))
        if d["disasters"]:
            b.append(P(f'Jenis bencana yang tercakup dalam "{t}": {", ".join(d["disasters"])}.', "bencana"))
        if d["infrastructure"]:
            b.append(P(f'Infrastruktur/aset yang dicatat pada "{t}": {", ".join(d["infrastructure"])}.', "infrastruktur"))
    b.append(H(1, "Pembaruan Data"))
    b.append(P(f'Pembaruan "{t}": metadata dibuat {d["publish_date"] or "-"}, metadata diperbarui {x["metadata_diperbarui"] or "-"}, '
               f'data diperbarui {x["filedata_diperbarui"] or "-"}; jadwal pemutakhiran {x["jadwal_pemutakhiran"] or "-"}.', "pembaruan"))
    if d["tags"]:
        b += [H(1, "Kata Kunci"), P(f'Kata kunci dataset "{t}": {", ".join(d["tags"])}', "tag")]
    return b