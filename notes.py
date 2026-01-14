import os
import shutil
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import mysql.connector
from mysql.connector import Error
import hashlib
from datetime import datetime

app = FastAPI(title="CS Study Hub API")

# CORS - Allow Flutter app to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# File Upload Directory
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/files", StaticFiles(directory=UPLOAD_DIR), name="files")

# Database Configuration
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "09042003",  # YOUR PASSWORD
    "database": "cs_study_hub"
}

def get_db():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

class LoginRequest(BaseModel):
    uccms_number: str
    password: str

class RegisterRequest(BaseModel):
    uccms_number: str
    full_name: str
    password: str

@app.post("/login")
def login(req: LoginRequest):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        hashed_pw = hash_password(req.password)
        cursor.execute("SELECT * FROM users WHERE uccms_number = %s AND password_hash = %s", (req.uccms_number, hashed_pw))
        user = cursor.fetchone()
        if not user: return {"status": "failed", "message": "Invalid credentials"}
        return {"status": "success", "user_id": user['id'], "uccms": user['uccms_number'], "name": user['full_name'], "role": user['role']}
    finally:
        cursor.close()
        conn.close()

@app.post("/register")
def register(req: RegisterRequest):
    conn = get_db()
    cursor = conn.cursor()
    try:
        hashed_pw = hash_password(req.password)
        cursor.execute("INSERT INTO users (uccms_number, full_name, password_hash, role, account_status) VALUES (%s, %s, %s, 'student', 'approved')", 
                       (req.uccms_number, req.full_name, hashed_pw))
        conn.commit()
        return {"status": "success", "message": "Registered successfully!"}
    except Error as e:
        return {"status": "error", "detail": str(e)}
    finally:
        cursor.close()
        conn.close()

@app.post("/upload-note")
async def upload_note(file: UploadFile = File(...), title: str = Form(...), subject: str = Form(...), semester: int = Form(...), category: str = Form(...), user_id: int = Form(...), description: Optional[str] = Form(None), tags: Optional[str] = Form(None)):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        with open(file_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO notes (title, subject, semester, category, file_path, file_size, file_type, description, tags, uploaded_by, upload_status) 
                          VALUES (%s, %s, %s, %s, %s, 0, 'pdf', %s, %s, %s, 'approved')""", 
                       (title, subject, semester, category, file_path, description, tags, user_id))
        conn.commit()
        return {"status": "success", "message": "Uploaded!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.get("/notes")
def get_notes():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""SELECT n.*, u.full_name as uploader_name FROM notes n 
                          JOIN users u ON n.uploaded_by = u.id 
                          WHERE n.upload_status = 'approved' ORDER BY n.upload_date DESC""")
        return {"status": "success", "notes": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()

@app.get("/search")
def search_notes(q: str):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        search_term = f"%{q}%"
        cursor.execute("""SELECT n.*, u.full_name as uploader_name FROM notes n 
                          JOIN users u ON n.uploaded_by = u.id 
                          WHERE n.upload_status = 'approved' AND (n.title LIKE %s OR n.subject LIKE %s)""", 
                       (search_term, search_term))
        return {"status": "success", "results": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()

@app.delete("/delete-note/{note_id}")
def delete_note(note_id: int, user_id: int):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT file_path FROM notes WHERE id = %s AND uploaded_by = %s", (note_id, user_id))
        note = cursor.fetchone()
        if not note: raise HTTPException(status_code=403, detail="Not your note!")
        
        if os.path.exists(note['file_path']): os.remove(note['file_path'])
        
        cursor.execute("DELETE FROM notes WHERE id = %s", (note_id,))
        conn.commit()
        return {"status": "success"}
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)