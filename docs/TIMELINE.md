# Rencana Kerja — KB Graf Data Bencana & Kerusakan Infrastruktur (8 deliverable, 5 hari kerja; geser sesuai kalender)
| Hari | # | Deliverable | Berkas / verifikasi | Status |
|---|---|---|---|---|
| 1 | 1 | Neo4j reprodusibel (Compose: APOC, volume, memori, kredensial `.env`) | `docker-compose.yml` (`--profile local-db`), `/kb/health` | ✅ |
| 1 | 2 | Skema Cypher berversi & idempoten | `schema/001–004`; `python -m scripts.run_schema` 2× | ✅ |
| 2 | 3 | Dataset seed 50–100 Q&A + sitasi, validasi supervisor | `data/seed_qa.json` (68 Q&A), `seed_qa.csv` | ✅ draft → ⏳ validasi |
| 2–3 | 4 | Loader + data benih termuat | `scripts/run_ingest.py`; `reports/ingest_report.md` | ✅ |
| 3 | 5 | Query Cypher teruji (agregasi sebaran, keparahan, dampak infrastruktur) | `queries/queries_core.cypher` (A1–A9, B1–B6) | ✅ |
| 4 | 6 | API FastAPI `/kb/health`, `/kb/query` | `kb_api/main.py`, `:8000/docs` | ✅ |
| 4 | 7 | UI Streamlit (jawaban LLM Groq + sitasi + graf) | `ui/app.py` `:8501` | ✅ |
| 5 | 8 | Demo + notulen umpan balik | `docs/demo_notes_template.md` | ⏳ |

Risiko: berkas data (xls/csv/pdf) belum ada → graf tetap terbentuk dari metadata (≥5 chunk/dataset), tetapi tanpa nilai genangan/kerusakan; taruh berkas di `data/documents/` lalu jalankan ulang loader (idempoten).
