"""Hasilkan dataset seed 50-100 Q&A (evaluasi akurasi RAG) dari metadata dataset bencana DKJ.
Jawaban diambil verbatim/terhitung dari metadata (grounded) + sitasi (dokumen+bagian). 5 dataset inti + pertanyaan lintas-dataset.
Keluaran: data/seed_qa.json dan data/seed_qa.csv (supervisor mengisi status/validated_by).
Pakai:  python -m scripts.generate_seed_qa"""
from __future__ import annotations
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kb.config import S  # noqa: E402
from kb.metadata import identity_text, load_docs  # noqa: E402

CORE = ["DOC-017", "DOC-021", "DOC-047", "DOC-043", "DOC-035"]  # banjir, kebakaran, kerusakan infrastruktur, korban/pengungsi, indeks risiko


def qa_for(d):
    t, did, x, out = d["title"], d["doc_id"], d["extra"], []
    add = lambda cat, q, a, sec: out.append({"category": cat, "question": q, "answer": a, "cites": [{"doc_id": did, "section": sec, "item": None}]})
    add("identitas", f'Apa format, kategori, dan tahun data dataset "{t}"?', identity_text(d), "identitas")
    if d["description"]:
        add("deskripsi", f'Apa isi dataset "{t}"?', d["description"], "deskripsi")
    add("satuan", f'Apa satuan dan jenis tabulasi dataset "{t}"?', f'Satuan: {x["satuan"] or "tidak dicatat"}; jenis tabulasi: {d["output_type"]}.', "cakupan")
    add("wilayah", f'Wilayah mana yang dicakup dataset "{t}"?', ", ".join(l["name"] for l in d["locations"]), "cakupan")
    add("sumber", f'Siapa penerbit dan apa sumber data "{t}"?', f'Penerbit: {x["instansi"]}; sumber: {x["sumber_data"]}.', "sumber")
    add("pembaruan", f'Kapan dataset "{t}" diperbarui?', f'Metadata diperbarui {x["metadata_diperbarui"] or "-"}; data diperbarui {x["filedata_diperbarui"] or "-"}.', "pembaruan")
    if d["disasters"]:
        add("bencana", f'Jenis bencana apa yang tercakup dalam "{t}"?', ", ".join(d["disasters"]), "bencana")
    if d["infrastructure"]:
        add("infrastruktur", f'Infrastruktur atau aset apa yang dicatat pada "{t}"?', ", ".join(d["infrastructure"]), "infrastruktur")
    add("tag", f'Apa kata kunci dataset "{t}"?', ", ".join(d["tags"]), "tag")
    return out


def cites(ds, sec="identitas"):
    return [{"doc_id": x["doc_id"], "section": sec, "item": None} for x in ds[:10]]


def cross(docs):
    out, by = [], lambda key: _group(docs, key)
    for sub, ds in by("subcategory").items():
        if len(ds) >= 3:
            out.append({"category": "lintas_dataset", "question": f"Dataset apa saja yang termasuk sub-kategori {sub}?", "answer": "; ".join(f'{x["doc_id"]} {x["title"]}' for x in ds[:10]), "cites": cites(ds)})
    for cat, ds in by("category").items():
        out.append({"category": "rekap", "question": f"Berapa jumlah dataset berkategori {cat}?", "answer": f"{len(ds)} dataset.", "cites": cites(ds)})
    for ft, ds in by("file_type").items():
        out.append({"category": "rekap", "question": f"Berapa dataset berformat {ft}?", "answer": f"{len(ds)} dataset.", "cites": cites(ds)})
    info = [d for d in docs if d["category"] == "Infografis"]
    if info:
        out.append({"category": "lintas_dataset", "question": "Tahun berapa saja infografis kejadian bencana tersedia?", "answer": ", ".join(sorted(d["year"] for d in info)), "cites": cites(info)})
    for t, ds in _group_list(docs, "disasters").items():
        out.append({"category": "lintas_dataset", "question": f"Dataset apa saja yang mencakup bencana {t}?", "answer": "; ".join(x["title"] for x in ds[:8]), "cites": cites(ds, "bencana")})
    return out


def _group(docs, key):
    g = defaultdict(list)
    for d in docs:
        if d[key]:
            g[d[key]].append(d)
    return g


def _group_list(docs, key):
    g = defaultdict(list)
    for d in docs:
        for v in d[key]:
            g[v].append(d)
    return g


def main():
    docs = load_docs(S.metadata_json)
    byid = {d["doc_id"]: d for d in docs}
    items = [q for i in CORE if i in byid for q in qa_for(byid[i])] + cross(docs)
    items = items[:100]
    for i, it in enumerate(items, 1):
        it.update(question_id=f"Q{i:03d}", status="draft", validated_by=None, source="metadata_bencana_dkj")
    assert 50 <= len(items) <= 100, f"jumlah Q&A {len(items)} di luar 50-100"
    S.seed_json.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(S.seed_json.with_suffix(".csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["question_id", "category", "question", "expected_answer", "doc_id", "section", "status", "validated_by", "catatan_supervisor"])
        for it in items:
            w.writerow([it["question_id"], it["category"], it["question"], it["answer"], ";".join(c["doc_id"] for c in it["cites"]), it["cites"][0]["section"], "draft", "", ""])
    print(f"{len(items)} Q&A (5 dataset inti + lintas-dataset)")


if __name__ == "__main__":
    main()
