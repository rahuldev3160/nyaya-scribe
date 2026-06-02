"""
06_chunk_notes.py
Extract text from 'notes' PDFs that are status='indexed' and split into
~500-word chunks. Chunks are stored in document_chunks and the source doc
status is updated to 'chunked'.
Idempotent — skips docs that already have chunks.
"""

import sqlite3
import re
from pathlib import Path

import pdfplumber

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_PATH = Path(__file__).parent.parent.parent / "data" / "upsc.db"
EXAM_ID = "upsc_eco_opt"
TARGET_WORDS = 500
MIN_WORDS = 400
MAX_WORDS = 600


# ---------------------------------------------------------------------------
# Text splitting helpers
# ---------------------------------------------------------------------------

def split_into_chunks(pages_text: list[tuple[int, str]]) -> list[dict]:
    """
    Given a list of (page_number, text) tuples (1-indexed), split the combined
    text into chunks of TARGET_WORDS words, splitting on paragraph boundaries
    (double newlines).  Returns a list of chunk dicts with keys:
        chunk_index, chunk_text, page_start, page_end, word_count
    """
    # Build a flat list of (word, page_num) pairs, preserving paragraph breaks
    # as sentinel tokens so we can later reconstruct boundaries.
    #
    # Strategy:
    #  1. Walk page by page; track current page number per paragraph.
    #  2. Collect paragraphs as (text, page_num) entries.
    #  3. Greedily group paragraphs into chunks near TARGET_WORDS.

    paragraphs: list[dict] = []  # {text, page_num, words}

    for page_num, text in pages_text:
        if not text:
            continue
        # Split on one or more blank lines
        raw_paras = re.split(r"\n\s*\n", text.strip())
        for para in raw_paras:
            para = para.strip()
            if not para:
                continue
            words = para.split()
            if not words:
                continue
            paragraphs.append({"text": para, "page_num": page_num, "words": len(words)})

    if not paragraphs:
        return []

    chunks: list[dict] = []
    chunk_index = 0

    i = 0
    while i < len(paragraphs):
        # Start a new chunk
        chunk_paras: list[dict] = []
        word_count = 0
        page_start = paragraphs[i]["page_num"]
        page_end = paragraphs[i]["page_num"]

        while i < len(paragraphs):
            para = paragraphs[i]
            new_count = word_count + para["words"]

            if word_count == 0:
                # Always take the first paragraph even if it's > MAX_WORDS
                chunk_paras.append(para)
                word_count = new_count
                page_end = para["page_num"]
                i += 1
            elif new_count <= MAX_WORDS:
                # Fits within max — keep adding
                chunk_paras.append(para)
                word_count = new_count
                page_end = para["page_num"]
                i += 1
            else:
                # Adding this paragraph would exceed MAX_WORDS
                if word_count >= MIN_WORDS:
                    # Current chunk is already big enough — flush it
                    break
                else:
                    # Under MIN_WORDS: absorb one more paragraph to avoid tiny chunks
                    chunk_paras.append(para)
                    word_count = new_count
                    page_end = para["page_num"]
                    i += 1
                    break

        chunk_text = "\n\n".join(p["text"] for p in chunk_paras)
        chunks.append(
            {
                "chunk_index": chunk_index,
                "chunk_text": chunk_text,
                "page_start": page_start,
                "page_end": page_end,
                "word_count": word_count,
            }
        )
        chunk_index += 1

    return chunks


# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------

def extract_pages(file_path: str) -> list[tuple[int, str]]:
    """Return [(page_num, text), ...] for each page (1-indexed)."""
    pages = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                pages.append((i, text))
    except Exception as e:
        print(f"  [ERROR] pdfplumber failed to open {file_path}: {e}")
    return pages


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Fetch all eligible docs: status='indexed', doc_type='notes'
    cur.execute(
        """
        SELECT doc_id, exam_id, paper_id, topic_id, filename, file_path
        FROM source_documents
        WHERE exam_id = ? AND status = 'indexed' AND doc_type = 'notes'
        ORDER BY filename
        """,
        (EXAM_ID,),
    )
    docs = cur.fetchall()
    print(f"Found {len(docs)} notes docs with status='indexed'\n")

    total_docs_chunked = 0
    total_chunks_created = 0
    total_words = 0

    for doc_id, exam_id, paper_id, topic_id, filename, file_path in docs:
        try:
            # Idempotency: skip if already has chunks
            cur.execute(
                "SELECT COUNT(*) FROM document_chunks WHERE doc_id = ?", (doc_id,)
            )
            existing = cur.fetchone()[0]
            if existing > 0:
                print(f"  [SKIP] {filename} — already has {existing} chunks")
                continue

            print(f"  Processing: {filename} ...", end="", flush=True)

            pages = extract_pages(file_path)
            if not pages:
                print(f" [WARN] No pages extracted — skipping")
                continue

            chunks = split_into_chunks(pages)
            if not chunks:
                print(f" [WARN] No chunks produced — skipping")
                continue

            # Insert all chunks
            rows = []
            for chunk in chunks:
                chunk_id = f"{doc_id}_c{chunk['chunk_index']:04d}"
                rows.append(
                    (
                        chunk_id,
                        doc_id,
                        exam_id,
                        paper_id,
                        topic_id,
                        chunk["chunk_index"],
                        chunk["chunk_text"],
                        chunk["page_start"],
                        chunk["page_end"],
                        chunk["word_count"],
                    )
                )

            cur.executemany(
                """
                INSERT OR IGNORE INTO document_chunks
                    (chunk_id, doc_id, exam_id, paper_id, topic_id,
                     chunk_index, chunk_text, page_start, page_end, word_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

            # Update source_documents status to 'chunked'
            cur.execute(
                "UPDATE source_documents SET status = 'chunked' WHERE doc_id = ?",
                (doc_id,),
            )
            conn.commit()

            doc_words = sum(c["word_count"] for c in chunks)
            print(f" {len(chunks)} chunks, {doc_words} words")

            total_docs_chunked += 1
            total_chunks_created += len(chunks)
            total_words += doc_words

        except Exception as e:
            print(f"\n  [ERROR] {filename}: {e}")
            conn.rollback()

    conn.close()

    # Final summary
    print("\n" + "=" * 50)
    print("Chunking complete")
    print(f"  Docs chunked   : {total_docs_chunked}")
    print(f"  Total chunks   : {total_chunks_created}")
    if total_chunks_created > 0:
        avg = total_words // total_chunks_created
        print(f"  Avg chunk size : {avg} words")
    print("=" * 50)


if __name__ == "__main__":
    main()
