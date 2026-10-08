"""LangChain + Groq (persona Analis Data Kebencanaan): sintesis jawaban berbasis konteks graf (chunk + entitas) dengan sitasi [n]. Gagal -> None (fallback ekstraktif)."""
from __future__ import annotations
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from .config import S

PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Anda adalah Analis Data Kebencanaan & Kerusakan Infrastruktur untuk BPBD Provinsi DKJ. Jawab dalam Bahasa Indonesia, "
               "ringkas, netral, dan faktual, HANYA berdasarkan KONTEKS (potongan dataset dari graf pengetahuan). "
               "Sebutkan jenis bencana, wilayah (kota/kecamatan/kelurahan), tahun, satuan, ketinggian genangan, status infrastruktur terdampak, "
               "dan nilai kerugian bila ada di konteks; jangan menghitung ulang atau memperkirakan angka yang tidak tertulis. "
               "Sisipkan sitasi [n] sesuai nomor konteks. Bila konteks hanya berupa metadata katalog (bukan nilai data), jelaskan dataset apa yang memuatnya. "
               "Jika konteks tidak memadai, katakan tidak ditemukan dan sarankan dataset yang relevan. Jangan mengarang angka, lokasi, atau penyebab bencana."),
    ("human", "PERTANYAAN: {question}\n\nKONTEKS (potongan dataset dari graf):\n{context}\n\nENTITAS TERKAIT:\n{entities}\n\n"
              "JAWABAN SEED TERVALIDASI (jika ada): {seed}\n\nJawaban:"),
])
_chain = None


def available() -> bool:
    return bool(S.use_llm and S.groq_api_key)


def get_chain(llm=None):
    global _chain
    if llm is not None:
        return PROMPT | llm | StrOutputParser()
    if _chain is None:
        from langchain_groq import ChatGroq
        _chain = PROMPT | ChatGroq(api_key=S.groq_api_key, model=S.groq_model, temperature=0.1, max_tokens=1200, timeout=45, max_retries=2) | StrOutputParser()
    return _chain


def synthesize(question: str, citations: list[dict], entities: list[dict], seed: str = "", llm=None) -> str | None:
    if not citations or (llm is None and not available()):
        return None
    ctx = "\n\n".join(f'[{i}] ({c["title"]} > {(c.get("breadcrumb") or "").split(" > ")[-1]}) {c["snippet"]}' for i, c in enumerate(citations, 1))
    ent = "\n".join(f'- {e["title"]}: kategori={e.get("category")}/{e.get("subcategory")}; tahun={e.get("year")}; bencana={", ".join(e.get("disasters") or []) or "-"}; infrastruktur={", ".join(e.get("infrastructure") or []) or "-"}; wilayah={", ".join(e.get("locations") or [])}' for e in entities[:4]) or "-"
    try:
        out = get_chain(llm).invoke({"question": question, "context": ctx, "entities": ent, "seed": seed or "-"}).strip()
        return out or None
    except Exception as e:  # noqa: BLE001
        print(f"[warn] Groq gagal, fallback ekstraktif: {e}")
        return None
