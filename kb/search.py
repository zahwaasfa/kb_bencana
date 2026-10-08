"""Query graf Data Bencana & Kerusakan Infrastruktur: pertanyaan serupa (full-text), jawaban+sumber, ekspansi 1-2 hop, penelusuran topik. Tanpa LLM."""
from __future__ import annotations
from .db import DB
from .text import lucene_query, overlap
from .chunker import lead

SIMILAR_Q = """
CALL db.index.fulltext.queryNodes('question_text_ft', $q) YIELD node AS q, score
WITH q, score ORDER BY score DESC LIMIT $limit
MATCH (q)-[:ANSWERED_BY]->(a:Answer)
RETURN q.question_id AS question_id, q.text AS question, a.text AS answer, q.status AS status, score"""

ANSWER_SOURCES = """
MATCH (q:Question {question_id:$qid})-[:ANSWERED_BY]->(a:Answer)-[:CITES]->(c:Chunk)
MATCH (d:Document {doc_id:c.doc_id})
RETURN d.doc_id AS doc_id, d.title AS title, d.document_url AS url, c.chunk_id AS chunk_id,
       c.breadcrumb AS breadcrumb, c.page_number AS page, c.text AS text
ORDER BY d.doc_id, c.chunk_id LIMIT $limit"""

CHUNK_FT = """
CALL db.index.fulltext.queryNodes('chunk_text_ft', $q) YIELD node AS c, score
WITH c, score ORDER BY score DESC LIMIT $limit
MATCH (d:Document {doc_id:c.doc_id})
OPTIONAL MATCH (c)-[:SUB_CHUNK_OF]->(p:Chunk)
RETURN c.chunk_id AS chunk_id, c.text AS text, c.level AS level, c.is_leaf AS is_leaf, c.breadcrumb AS breadcrumb,
       c.page_number AS page, d.doc_id AS doc_id, d.title AS title, d.document_url AS url,
       p.chunk_id AS parent_id, p.text AS parent_text, score"""

CONTEXT = """
MATCH (c:Chunk {chunk_id:$cid})
OPTIONAL MATCH (c)-[:SUB_CHUNK_OF*1..6]->(anc:Chunk)
OPTIONAL MATCH (c)<-[:SUB_CHUNK_OF]-(kid:Chunk)
OPTIONAL MATCH (c)-[:NEXT_CHUNK]->(nx:Chunk)
OPTIONAL MATCH (c)-[ref:REFERENCES_CHUNK]->(rc:Chunk)
WITH c, collect(DISTINCT anc.chunk_id) AS ancestors, collect(DISTINCT kid.chunk_id)[..10] AS children, nx.chunk_id AS next_id,
     collect(DISTINCT {chunk_id:rc.chunk_id, doc_id:rc.doc_id, similarity:ref.similarity, type:ref.type})[..5] AS refs
RETURN ancestors, children, next_id, refs"""

DOC_ENTITIES = """
MATCH (d:Document) WHERE d.doc_id IN $ids
OPTIONAL MATCH (d)-[:PUBLISHED_BY]->(o:Organization)
OPTIONAL MATCH (d)-[:IN_CATEGORY]->(cat:Category)
OPTIONAL MATCH (d)-[:IN_SUB_CATEGORY]->(sub:SubCategory)
OPTIONAL MATCH (d)-[:TAGGED_WITH]->(t:Tag)
OPTIONAL MATCH (d)-[:COVERS_DISASTER]->(dt:DisasterType)
OPTIONAL MATCH (d)-[:AFFECTS_INFRASTRUCTURE]->(inf:Infrastructure)
OPTIONAL MATCH (d)-[:LOCATED_IN]->(l:Location)
OPTIONAL MATCH (d)-[:FOR_YEAR]->(y:Year)
OPTIONAL MATCH (d)-[:USES_REFERENCE]->(r:Reference)
RETURN d.doc_id AS doc_id, d.title AS title, o.name AS instansi, cat.name AS category, sub.name AS subcategory, y.value AS year,
       collect(DISTINCT t.name)[..8] AS tags, collect(DISTINCT dt.name) AS disasters, collect(DISTINCT inf.name) AS infrastructure,
       collect(DISTINCT l.name)[..6] AS locations, collect(DISTINCT r.title)[..4] AS sources"""

RELATED_DOCS = """
MATCH (d:Document {doc_id:$id})-[:TAGGED_WITH|COVERS_DISASTER|AFFECTS_INFRASTRUCTURE|IN_SUB_CATEGORY|LOCATED_IN|FOR_YEAR]->(x)
      <-[:TAGGED_WITH|COVERS_DISASTER|AFFECTS_INFRASTRUCTURE|IN_SUB_CATEGORY|LOCATED_IN|FOR_YEAR]-(o:Document)
WHERE o <> d
WITH o, collect(DISTINCT coalesce(x.name, x.value)) AS shared, count(DISTINCT x) AS n
RETURN o.doc_id AS doc_id, o.title AS title, shared[..5] AS shared, n ORDER BY n DESC LIMIT $limit"""

EXPAND_2HOP = """
MATCH (e {name:$name})<-[:TAGGED_WITH|IN_CATEGORY|IN_SUB_CATEGORY|LOCATED_IN|COVERS_DISASTER|AFFECTS_INFRASTRUCTURE]-(d:Document)
OPTIONAL MATCH (d)-[:TAGGED_WITH|COVERS_DISASTER|AFFECTS_INFRASTRUCTURE|FOR_YEAR*1..1]->(n2)
RETURN d.doc_id AS doc_id, d.title AS title, collect(DISTINCT coalesce(n2.name, n2.value))[..8] AS neighbours LIMIT $limit"""

BY_TOPIC = """
MATCH (t:Tag) WHERE toLower(t.name) CONTAINS toLower($topic)
MATCH (d:Document)-[r:TAGGED_WITH]->(t)
RETURN t.name AS tag, d.doc_id AS doc_id, d.title AS title, d.year AS year, r.frequency AS frequency
ORDER BY frequency DESC LIMIT $limit"""


def similar_questions(db: DB, text: str, limit: int = 5) -> list[dict]:
    q = lucene_query(text)
    return db.read(SIMILAR_Q, q=q, limit=limit) if q else []


def answer_sources(db: DB, qid: str, limit: int = 8) -> list[dict]:
    return db.read(ANSWER_SOURCES, qid=qid, limit=limit)


def search_chunks(db: DB, text: str, top_k: int = 5) -> list[dict]:
    q = lucene_query(text)
    if not q:
        return []
    rows = db.read(CHUNK_FT, q=q, limit=max(top_k * 6, 30))
    mx = max((r["score"] for r in rows), default=1.0) or 1.0
    for r in rows:
        r["rank"] = 0.55 * r["score"] / mx + 0.45 * overlap(text, f'{r["breadcrumb"]} {r["text"]}') + (0.05 if r["is_leaf"] else 0)
    best, per_doc = [], {}
    for r in sorted(rows, key=lambda x: x["rank"], reverse=True):
        if per_doc.get(r["doc_id"], 0) >= 2:
            continue
        per_doc[r["doc_id"]] = per_doc.get(r["doc_id"], 0) + 1
        best.append(r)
        if len(best) >= top_k:
            break
    return best


def chunk_context(db: DB, cid: str) -> dict:
    r = db.read(CONTEXT, cid=cid)
    return r[0] if r else {}


def doc_entities(db: DB, ids: list[str]) -> list[dict]:
    return db.read(DOC_ENTITIES, ids=ids)


def related_docs(db: DB, doc_id: str, limit: int = 5) -> list[dict]:
    return db.read(RELATED_DOCS, id=doc_id, limit=limit)


def expand_entity(db: DB, name: str, limit: int = 10) -> list[dict]:
    return db.read(EXPAND_2HOP, name=name, limit=limit)


def by_topic(db: DB, topic: str, limit: int = 10) -> list[dict]:
    return db.read(BY_TOPIC, topic=topic, limit=limit)


def answer(db: DB, question: str, top_k: int = 5) -> dict:
    """Pipeline: pertanyaan serupa -> (jawaban seed + sitasi) | fallback chunk full-text. Hasil selalu dengan sitasi dari graf."""
    best = None
    for c in similar_questions(db, question, 5):
        sc = overlap(question, c["question"])
        if sc >= 0.35 and (best is None or sc > best[0]):
            best = (sc, c)
    cites, source, text, matched = [], "none", "", None
    if best:
        sc, c = best
        source, text, matched = "seed_qa", c["answer"], {"question_id": c["question_id"], "question": c["question"], "similarity": round(sc, 3)}
        for s in answer_sources(db, c["question_id"], top_k + 3):
            cites.append({**s, "snippet": lead(s["text"], 300), "score": round(sc, 3)})
    else:
        hits = search_chunks(db, question, top_k)
        if hits:
            source = "chunks"
            text = "\n\n".join(f'[{i}] {lead(h["text"], 450)}' for i, h in enumerate(hits[:3], 1))
            for h in hits:
                cites.append({"doc_id": h["doc_id"], "title": h["title"], "url": h["url"], "chunk_id": h["chunk_id"],
                              "breadcrumb": h["breadcrumb"], "page": h["page"], "snippet": lead(h["text"], 300), "score": round(h["rank"], 3)})
    # dedup sitasi
    seen, uniq = set(), []
    for c in cites:
        if c["chunk_id"] not in seen:
            seen.add(c["chunk_id"]); uniq.append(c)
    return {"answer": text or "Tidak ditemukan jawaban pada graf pengetahuan.", "source": source, "matched_question": matched, "citations": uniq[:top_k + 3]}
