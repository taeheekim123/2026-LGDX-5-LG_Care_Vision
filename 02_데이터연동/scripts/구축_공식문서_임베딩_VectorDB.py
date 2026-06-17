from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parents[1]
DB_PATH = PROJECT_DIR / "02_데이터연동" / "db" / "careshot_ar_mock.db"
SCHEMA_PATH = PROJECT_DIR / "02_데이터연동" / "db" / "schema.sql"
MOCK_DIR = PROJECT_DIR / "02_데이터연동" / "mock_data"
VECTOR_DIR = PROJECT_DIR / "02_데이터연동" / "vector_index"
RAG_DIR = PROJECT_DIR / "03_AI로직" / "rag"
OUTPUT_DIR = PROJECT_DIR / "06_산출물"
OFFICIAL_SOURCE_PREFIXES = (
    "https://www.lg.com/in/",
    "https://gscs-manual.lge.com/",
)

sys.path.insert(0, str(RAG_DIR))

from careshot_embedding_model import DEFAULT_CONFIG, embed_text, embedding_norm  # noqa: E402


def read_json(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def build_embedding_text(chunk: dict) -> str:
    parts = [
        chunk.get("product_type"),
        chunk.get("model_name"),
        chunk.get("series"),
        chunk.get("procedure_type"),
        chunk.get("chunk_title"),
        chunk.get("chunk_text"),
        chunk.get("source_section"),
        chunk.get("source_type"),
    ]
    return " ".join(str(part) for part in parts if part)


def load_chunks(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return conn.execute(
        """
        SELECT *
        FROM official_document_chunks
        WHERE chunk_text IS NOT NULL
          AND TRIM(chunk_text) != ''
          AND (
            source_url LIKE 'https://www.lg.com/in/%'
            OR source_url LIKE 'https://gscs-manual.lge.com/%'
          )
        ORDER BY chunk_id ASC
        """
    ).fetchall()


def upsert_embeddings(conn: sqlite3.Connection, rows: list[sqlite3.Row]) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    model = DEFAULT_CONFIG
    vector_records = []
    status_counter: Counter[str] = Counter()
    product_counter: Counter[str] = Counter()
    procedure_counter: Counter[str] = Counter()

    conn.execute(
        "DELETE FROM official_document_embeddings WHERE embedding_model = ?",
        (model.model_name,),
    )

    for row in rows:
        chunk = dict(row)
        vector = embed_text(build_embedding_text(chunk), model)
        status = "embedded" if vector else "empty_text"
        status_counter[status] += 1
        product_counter[chunk.get("product_type") or "unknown"] += 1
        procedure_counter[chunk.get("procedure_type") or "unknown"] += 1

        if status != "embedded":
            continue

        payload = {
            "embedding_id": f"EMB_{chunk['chunk_id']}",
            "chunk_id": chunk["chunk_id"],
            "embedding_model": model.model_name,
            "embedding_dimension": model.dimension,
            "embedding_vector": vector,
            "embedding_norm": embedding_norm(vector),
            "embedding_status": status,
            "indexed_at": now,
            "product_type": chunk.get("product_type"),
            "model_name": chunk.get("model_name"),
            "procedure_type": chunk.get("procedure_type"),
            "source_url": chunk.get("source_url"),
        }
        vector_records.append(payload)
        conn.execute(
            """
            INSERT INTO official_document_embeddings (
              embedding_id, chunk_id, embedding_model, embedding_dimension,
              embedding_vector_json, embedding_norm, embedding_status, indexed_at, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chunk_id) DO UPDATE SET
              embedding_model = excluded.embedding_model,
              embedding_dimension = excluded.embedding_dimension,
              embedding_vector_json = excluded.embedding_vector_json,
              embedding_norm = excluded.embedding_norm,
              embedding_status = excluded.embedding_status,
              indexed_at = excluded.indexed_at,
              raw_json = excluded.raw_json
            """,
            (
                payload["embedding_id"],
                payload["chunk_id"],
                payload["embedding_model"],
                payload["embedding_dimension"],
                json.dumps(vector, ensure_ascii=False, sort_keys=True),
                payload["embedding_norm"],
                payload["embedding_status"],
                payload["indexed_at"],
                json.dumps(payload, ensure_ascii=False),
            ),
        )

    conn.execute(
        """
        UPDATE official_document_chunks
        SET embedding_status = 'embedded'
        WHERE chunk_id IN (
          SELECT chunk_id
          FROM official_document_embeddings
          WHERE embedding_model = ?
            AND embedding_status = 'embedded'
        )
        """,
        (model.model_name,),
    )
    conn.commit()

    VECTOR_DIR.mkdir(parents=True, exist_ok=True)
    index_path = VECTOR_DIR / "official_document_embeddings.jsonl"
    with index_path.open("w", encoding="utf-8") as handle:
        for record in vector_records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    manifest = {
        "created_at": now,
        "embedding_model": model.model_name,
        "embedding_dimension": model.dimension,
        "language_scope": model.language_scope,
        "cost_profile": model.cost_profile,
        "source_table": "official_document_chunks",
        "embedding_table": "official_document_embeddings",
        "vector_index_file": str(index_path.relative_to(PROJECT_DIR)),
        "total_candidate_chunks": len(rows),
        "embedded_chunks": len(vector_records),
        "status_counts": dict(status_counter),
        "product_type_counts": dict(product_counter),
        "top_procedure_type_counts": dict(procedure_counter.most_common(20)),
    }
    write_json(VECTOR_DIR / "official_document_embeddings_manifest.json", manifest)
    return manifest


def update_chunk_json_status() -> int:
    chunks_path = MOCK_DIR / "official_document_chunks.json"
    chunks = read_json(chunks_path)
    updated = 0
    for chunk in chunks:
        if str(chunk.get("source_url") or "").startswith(OFFICIAL_SOURCE_PREFIXES):
            chunk["embedding_status"] = "embedded"
            chunk["embedding_model"] = DEFAULT_CONFIG.model_name
            updated += 1
    write_json(chunks_path, chunks)
    return updated


def write_report(summary: dict) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUT_DIR / "Embedding_VectorDB_검증리포트_2026-06-04.md"
    report = f"""# Embedding/Vector DB 구축 검증 리포트

작성일: 2026-06-04

## 1. 결론

6번 Embedding/Vector DB 구축 작업을 수행했다. LG India 공식자료 RAG chunk를 로컬 embedding 모델로 벡터화하고, SQLite `official_document_embeddings` 테이블과 JSONL vector index 파일에 저장했다.

## 2. Embedding 모델 선정

| 항목 | 값 |
|---|---|
| 모델명 | `{summary['embedding_model']}` |
| 차원 | {summary['embedding_dimension']} |
| 방식 | 단어/바이그램/문자 n-gram 기반 deterministic hashing embedding |
| API 비용 | 없음 |
| 선정 이유 | 개발 단계에서 외부 API 비용 없이 재현 가능하고, 영어/힌디어 혼합 VOC와 LG 공식자료의 키워드/절차 유사도를 안정적으로 비교하기 위함 |

운영 단계에서는 같은 테이블 구조를 유지한 채 OpenAI embeddings 또는 다국어 sentence-transformer 계열로 교체할 수 있다.

## 3. 저장 구조

| 항목 | 값 |
|---|---|
| 원본 테이블 | `official_document_chunks` |
| Embedding 테이블 | `official_document_embeddings` |
| Vector index 파일 | `{summary['vector_index_file']}` |
| chunk 상태 컬럼 | `official_document_chunks.embedding_status` |

## 4. 구축 수량

| 항목 | 수량 |
|---|---:|
| 후보 chunk | {summary['total_candidate_chunks']} |
| embedded chunk | {summary['embedded_chunks']} |
| embedding_status=embedded | {summary['status_counts'].get('embedded', 0)} |

## 5. 제품군 분포

| product_type | chunk 수 |
|---|---:|
"""
    for product_type, count in sorted(summary["product_type_counts"].items()):
        report += f"| {product_type} | {count} |\n"

    report += "\n## 6. 절차 타입 상위 분포\n\n| procedure_type | chunk 수 |\n|---|---:|\n"
    for procedure_type, count in summary["top_procedure_type_counts"].items():
        report += f"| {procedure_type} | {count} |\n"

    report += """
## 7. 검증 기준

- `official_document_embeddings` 테이블이 생성되어야 한다.
- 모든 공식자료 chunk가 `chunk_id` 기준으로 embedding vector와 연결되어야 한다.
- `official_document_chunks.embedding_status`가 `embedded`로 갱신되어야 한다.
- RAGService v2에서 이 embedding을 이용해 vector similarity search를 수행할 수 있어야 한다.
"""
    report_path.write_text(report, encoding="utf-8")
    return report_path


def main() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        ensure_schema(conn)
        rows = load_chunks(conn)
        summary = upsert_embeddings(conn, rows)
    summary["json_chunks_updated"] = update_chunk_json_status()
    report_path = write_report(summary)
    print(json.dumps({**summary, "report_path": str(report_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
