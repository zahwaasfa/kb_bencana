# ARCANA — Knowledge Base Graf Data Bencana & Kerusakan Infrastruktur (Neo4j + LangChain/Groq + FastAPI + Streamlit)

Struktur sama dengan proyek Bappenas; domain: katalog 87 dataset kebencanaan BPBD Provinsi DKJ. Kontrak graf: `docs/GRAPH_CONTRACT.md` · jadwal: `docs/TIMELINE.md` · query analitik: `queries/queries_core.cypher`.

## Menjalankan
```bash
cp .env.example .env      # isi kredensial Aura/Groq (atau gunakan .env Anda)
# metadata: data/metadata_bencana.json (atau data/data_bencana.json); berkas data opsional: data/documents/
docker compose run --rm loader                     # skema + muat + seed -> reports/ingest_report.md
docker compose up -d kb-api streamlit-ui           # API :8000/docs, UI :8501
# Neo4j lokal (APOC+volume): NEO4J_USERNAME=neo4j, NEO4J_URI_DOCKER=bolt://neo4j:7687 ; docker compose --profile local-db up -d neo4j
```
Idempoten: loader aman diulang. Tes tanpa DB: `python -m pytest -q tests`. Seed ulang: `python -m scripts.generate_seed_qa`.

## Alur jawaban
Pertanyaan serupa (full-text) → jawaban seed + sitasi, atau full-text chunk → konteks + entitas (jenis bencana, infrastruktur, lokasi, tahun) → LangChain `prompt | ChatGroq` (persona *Analis Data Kebencanaan & Kerusakan Infrastruktur*) → jawaban ber-sitasi [n]. Groq gagal/nonaktif → jawaban ekstraktif otomatis.

## Catatan
Metadata katalog tidak memuat nilai genangan/kerusakan per kejadian; angka tersebut diambil dari baris tabel berkas data yang dimuat (`extract_facts`). Jangan commit `.env` (kunci Aura/Groq).
