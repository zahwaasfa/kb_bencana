"""FastAPI KB Data Bencana & Kerusakan Infrastruktur: GET /kb/health, POST /kb/query -> jawaban + sitasi dari graf Neo4j."""
from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from kb import rag, search
from kb.config import S
from kb.db import DB

state: dict = {}


def get_db() -> DB:
    if "db" not in state:
        state["db"] = DB()
    return state["db"]


@asynccontextmanager
async def lifespan(app):
    yield
    if "db" in state:
        state["db"].close()

app = FastAPI(title="ARCANA Bencana & Infrastruktur KB API", version="1.0.0", lifespan=lifespan)


class QueryReq(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(5, ge=1, le=15)
    include_graph: bool = True


class Citation(BaseModel):
    doc_id: str
    title: str
    chunk_id: str
    breadcrumb: str | None = None
    page: int | None = None
    url: str | None = None
    snippet: str = ""
    score: float = 0.0


class QueryResp(BaseModel):
    answer: str
    source: str
    matched_question: dict | None = None
    citations: list[Citation]
    entities: list[dict] = []
    related_documents: list[dict] = []
    answer_mode: str = "extractive"
    extractive_answer: str | None = None
    graph: dict = {"nodes": [], "edges": []}


@app.get("/kb/health")
def health():
    try:
        db = get_db()
        counts = {r["l"]: r["n"] for r in db.read("MATCH (n) UNWIND labels(n) AS l RETURN l, count(*) AS n")}
        try:
            apoc = db.read("RETURN apoc.version() AS v")[0]["v"]
        except Exception:  # noqa: BLE001
            apoc = None
        idx = [r["name"] for r in db.read("SHOW INDEXES YIELD name, state WHERE state = 'ONLINE' RETURN name")]
        return {"status": "ok", "neo4j": "connected", "apoc": apoc, "llm": f"groq:{S.groq_model}" if rag.available() else "nonaktif", "nodes": counts, "indexes_online": idx}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(503, f"neo4j tidak tersedia: {e}")


def _graph(cites: list[dict], ents: list[dict]) -> dict:
    nodes, edges = {}, []

    def n(i, label, kind):
        nodes.setdefault(i, {"id": i, "label": str(label)[:60], "type": kind})

    def e(a, b, rel):
        edges.append({"source": a, "target": b, "rel": rel})
    for c in cites:
        n(c["chunk_id"], (c.get("breadcrumb") or c["chunk_id"]).split(" > ")[-1], "Chunk")
        n(c["doc_id"], c["title"], "Document"); e(c["doc_id"], c["chunk_id"], "CONTAINS_CHUNK")
    for x in ents:
        if x["doc_id"] not in nodes:
            continue
        spec = (("instansi", "Organization", "PUBLISHED_BY"), ("category", "Category", "IN_CATEGORY"), ("subcategory", "SubCategory", "IN_SUB_CATEGORY"), ("year", "Year", "FOR_YEAR"))
        for key, kind, rel in spec:
            if x.get(key):
                n(f"{kind}:{x[key]}", x[key], kind); e(x["doc_id"], f"{kind}:{x[key]}", rel)
        for key, kind, rel in (("tags", "Tag", "TAGGED_WITH"), ("disasters", "DisasterType", "COVERS_DISASTER"),
                               ("infrastructure", "Infrastructure", "AFFECTS_INFRASTRUCTURE"), ("locations", "Location", "LOCATED_IN"), ("sources", "Reference", "USES_REFERENCE")):
            for v in x.get(key) or []:
                n(f"{kind}:{v}", v, kind); e(x["doc_id"], f"{kind}:{v}", rel)
    return {"nodes": list(nodes.values()), "edges": edges}


@app.post("/kb/query", response_model=QueryResp)
def query(req: QueryReq):
    try:
        db = get_db()
        res = search.answer(db, req.question, req.top_k)
        ids = list(dict.fromkeys(c["doc_id"] for c in res["citations"]))
        ents = search.doc_entities(db, ids) if ids else []
        rel = search.related_docs(db, ids[0], 5) if ids else []
        res.update(answer_mode="extractive", extractive_answer=None)
        llm_text = rag.synthesize(req.question, res["citations"], ents, res["answer"] if res["source"] == "seed_qa" else "") if res["source"] != "none" else None
        if llm_text:
            res.update(extractive_answer=res["answer"], answer=llm_text, answer_mode="llm")
        res.update(entities=ents, related_documents=rel, graph=_graph(res["citations"], ents) if req.include_graph else {"nodes": [], "edges": []})
        return res
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(503, f"gagal query graf: {e}")


@app.get("/")
def root():
    return {"service": "ARCANA KB API", "docs": "/docs", "health": "/kb/health"}
