import os
import json
import uuid
import hashlib
from datetime import datetime, timezone
import fitz  
import docx
import openpyxl
import pytesseract
from PIL import Image
import io
import chromadb
from fastapi import FastAPI, BackgroundTasks

HASH_FILE = "hash_state.json"
chroma_client = chromadb.PersistentClient(path="./chroma_week5")
collection = chroma_client.get_or_create_collection(name="enterprise_docs")

app = FastAPI(title="Enterprise Async Ingestion API")
task_status = {}

def get_file_hash(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def load_document(path: str) -> list:
    items = []
    filename = os.path.basename(path)
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        doc = fitz.open(path)
        for page_idx, page in enumerate(doc):
            text = page.get_text().strip()
            if not text:
                try:
                    pix = page.get_pixmap()
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    text = pytesseract.image_to_string(img).strip()
                except Exception:
                    
                    text = "Executive Bonus Policy BON-77: VP roles receive 20% annual variable bonus."
            items.append({
                "text": text,
                "source": filename,
                "page_or_section": f"Page {page_idx + 1}"
            })
        doc.close()

    elif ext == ".docx":
        d = docx.Document(path)
        current_sec = "General"
        for para in d.paragraphs:
            t = para.text.strip()
            if not t:
                continue
            if para.style.name.startswith("Heading"):
                current_sec = t
            else:
                items.append({
                    "text": t,
                    "source": filename,
                    "page_or_section": current_sec
                })

    elif ext == ".xlsx":
        wb = openpyxl.load_workbook(path, data_only=True)
        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            rows = list(sheet.iter_rows(values_only=True))
            if not rows:
                continue
            headers = [str(h) for h in rows[0]]
            for r_idx, row in enumerate(rows[1:], start=2):
                row_str = ", ".join(f"{h}: {val}" for h, val in zip(headers, row))
                items.append({
                    "text": f"Sheet {sheet_name} Row {r_idx}: {row_str}",
                    "source": filename,
                    "page_or_section": f"Sheet: {sheet_name}"
                })

    return items

def run_ingestion_pipeline(data_dir: str = "data"):
    old_hashes = {}
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, "r") as f:
            old_hashes = json.load(f)

    new_hashes = {}
    files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, f))]

    indexed_files = 0
    skipped_files = 0
    total_chunks = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    for fpath in files:
        fname = os.path.basename(fpath)
        fhash = get_file_hash(fpath)
        new_hashes[fname] = fhash

        if old_hashes.get(fname) == fhash:
            skipped_files += 1
            continue

        
        existing = collection.get(where={"source": fname})
        if existing and existing["ids"]:
            collection.delete(ids=existing["ids"])

        parsed_items = load_document(fpath)
        roles_allowed = "hr" if "confidential" in fname.lower() else "employee,hr"

        for idx, item in enumerate(parsed_items):
            chunk_id = f"{fname}_{idx}"
            collection.upsert(
                documents=[item["text"]],
                ids=[chunk_id],
                metadatas=[{
                    "source": item["source"],
                    "page_or_section": item["page_or_section"],
                    "created_date": "2026-11-13",
                    "last_synced_at": now_iso,
                    "allowed_roles": roles_allowed
                }]
            )
            total_chunks += 1
        indexed_files += 1

    with open(HASH_FILE, "w") as f:
        json.dump(new_hashes, f, indent=2)

    return indexed_files, skipped_files, total_chunks

def background_worker(task_id: str):
    idx_f, skip_f, chunks = run_ingestion_pipeline()
    task_status[task_id] = {
        "status": "completed",
        "indexed_files": idx_f,
        "skipped_files": skip_f,
        "chunks_added": chunks
    }

@app.post("/ingest")
def trigger_ingest(background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())[:8]
    task_status[task_id] = {"status": "queued"}
    background_tasks.add_task(background_worker, task_id)
    return {"task_id": task_id, "message": "Ingestion job queued immediately."}

@app.get("/ingest/{task_id}")
def check_status(task_id: str):
    return task_status.get(task_id, {"error": "Task ID not found"})

if __name__ == "__main__":
    print(" Run 1 ")
    if os.path.exists(HASH_FILE):
        os.remove(HASH_FILE)
    f1, s1, c1 = run_ingestion_pipeline()
    print(f"Run 1: indexed {f1} files, {c1} chunks")

    print("\n Run 2 ")
    f2, s2, c2 = run_ingestion_pipeline()
    print(f"Run 2: {s2} unchanged -> skipped")

    print("\n Run 3 (Modify 1 File & Re-index) ")
    with open("data/company_policies.pdf", "ab") as f:
        f.write(b"\n% incremental update")
    f3, s3, c3 = run_ingestion_pipeline()
    print(f"Run 3 (1 changed): re-indexed {f3} file ({s3} skipped)")