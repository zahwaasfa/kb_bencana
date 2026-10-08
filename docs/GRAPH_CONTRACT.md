# Kontrak Graf — Data Bencana & Kerusakan Infrastruktur DKJ
Struktur identik dengan proyek Bappenas (Document → Chunk hierarkis tak terbatas); hanya entitas domain yang berbeda.

```
(:Document[:DisasterEvent|:DamageReport]) -[:PUBLISHED_BY]-> (:Organization BPBD Provinsi DKJ)
   -[:IN_CATEGORY]-> (:Category) <-[:SUBCATEGORY_OF]- (:SubCategory) <-[:IN_SUB_CATEGORY]- (:Document)
   -[:COVERS_DISASTER]-> (:DisasterType)         -[:AFFECTS_INFRASTRUCTURE]-> (:Infrastructure)
   -[:LOCATED_IN]-> (:Location)                  -[:FOR_YEAR]-> (:Year)      -[:MEASURED_IN]-> (:MeasureUnit)
   -[:USES_REFERENCE {citation_role:'data_input'}]-> (:Reference)             -[:TAGGED_WITH {frequency}]-> (:Tag) <-[:TAGGED_WITH]- (:Chunk)
(:Location kelurahan) -[:PART_OF_LOCATION]-> (:Location kecamatan) -> (:Location kota) -> (:Location Provinsi DKJ)
(:Document) -[:CONTAINS_CHUNK]-> (:Chunk L0) <-[:SUB_CHUNK_OF {order, level_diff}]- (:Chunk L1) <- ... Ln
(:Chunk) -[:NEXT_CHUNK]-> (:Chunk) ; (:Chunk) -[:REFERENCES_CHUNK {similarity, type: semantic_similarity|impact_evidence}]-> (:Chunk)
(:Chunk) -[:ABOUT_LOCATION]-> (:Location)       -- hanya chunk baris tabel yang memuat kolom lokasi
(:Question) -[:ANSWERED_BY]-> (:Answer) -[:CITES]-> (:Chunk) ; (:Question) -[:ASKED_ABOUT]-> (:Document)
```

## Pemetaan metadata → graf
| Kolom JSON | Graf |
|---|---|
| id, judul, nama_file, jenis_file | `Document.doc_id/title/file_name/file_type` |
| kategori_data / sub_kategori | `Category` / `SubCategory` (+ label tambahan `DisasterEvent` untuk *Data Kejadian*, `DamageReport` untuk *Data Dampak*) |
| instansi, kontak | `Organization` (BPBD Provinsi DKJ) |
| sumber_data | `Reference` (sumber selain penerbit, mis. Satu Data Jakarta) + `Document.sumber_data` |
| wilayah, isian_klasifikasi `[32010026]` | `Location` Provinsi DKJ (`code`) + kota/kecamatan/kelurahan yang terdeteksi |
| tahun | `Year` ; satuan → `MeasureUnit` ; ukuran → `Document.output_type` |
| tag | `Tag` (+ frekuensi pada Document dan Chunk) |
| judul/deskripsi/tag (kata kunci) | `DisasterType` (Banjir, Kebakaran, Pohon Tumbang, Krisis Kesehatan, …) dan `Infrastructure` |

## Fakta dari baris tabel (berkas fisik di `data/documents/`)
Setiap baris tabel = satu chunk atomik `kolom: nilai | kolom: nilai`. `kb.metadata.extract_facts` mengisi properti chunk:
`kota, kecamatan, kelurahan, inundation_cm` (genangan, otomatis cm), `damage_status` (rusak berat/sedang/ringan, terendam, …), `loss_value`;
serta membentuk `Location` berjenjang dan `ABOUT_LOCATION`. Katalog metadata sendiri **tidak** memuat nilai genangan/kerusakan — nilai itu baru ada setelah berkas data dimuat.
