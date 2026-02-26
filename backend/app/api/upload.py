from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
import shutil
import os
from app.services.parser import process_document
from app.services.indexer import get_or_create_index

router = APIRouter()
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

processing_status = {}

def parse_and_index(file_path: str, filename: str):
    processing_status[filename] = "processing"
    print(f"Starting background processing for {file_path}")
    try:
        docs = process_document(file_path)
        if docs:
            get_or_create_index(documents=docs)
        processing_status[filename] = "completed"
    except Exception as e:
        processing_status[filename] = "failed"
        print(f"Error processing {file_path}: {e}")
    print(f"Finished processing {file_path}")

@router.get("/status/{filename}")
async def get_status(filename: str):
    status = processing_status.get(filename, "not_found")
    return {"filename": filename, "status": status}

@router.post("/")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    MAX_SIZE = 10 * 1024 * 1024
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")

    parts = file.filename.rsplit(".", 1)
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="File must have an extension.")
        
    file_extension = parts[-1].lower()
    allowed_extensions = ["pdf", "md", "txt", "zip"]
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="File type not supported. Please upload PDF, MD, TXT, or ZIP.")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    processing_status[file.filename] = "pending"
    background_tasks.add_task(parse_and_index, file_path, file.filename)

    return {"message": f"Successfully uploaded {file.filename}. Processing will begin shortly."}
