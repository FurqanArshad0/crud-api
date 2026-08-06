from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import sqlite3

app = FastAPI()

# DATABASE SETUP


DATABASE_FILE = "tasks.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():  
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create table if it doesn't exist
    cursor.execute("""CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        done INTEGER DEFAULT 0
                    )""")

    # Check if table is empty
    cursor.execute("SELECT COUNT(*) as count FROM tasks")
    result = cursor.fetchone()
    row_count = result[0]
    
    # Seed only if empty
    if row_count == 0:
        cursor.execute("INSERT INTO tasks (title, done) VALUES (?, ?)", ("Learn FastAPI", 0))
        cursor.execute("INSERT INTO tasks (title, done) VALUES (?, ?)", ("Build a CRUD API", 0))
        cursor.execute("INSERT INTO tasks (title, done) VALUES (?, ?)", ("Submit assignment", 1))  # ✅ FIXED
        conn.commit()
        print("✅ Database seeded with 3 example tasks!")
    else:
        print(f"📊 Database already has {row_count} tasks. Skipping seeding.")
        
    conn.close()

# Run database initialization on startup
init_database()  


# PYDANTIC MODELS


class TaskCreate(BaseModel):
    title: str

class TaskUpdate(BaseModel):
    title: str = None
    done: bool = None

# STAGE 0: HELLO


@app.get("/")
def hello():
    return {"message": "Hello Bhai!"}


# STAGE 1: ROOT + HEALTH


@app.get("/root")
def root():
    return {
        "name": "Task API",
        "version": "1.0.0",
        "endpoints": ["/tasks"]
    }

@app.get("/health")
def health():
    return {"status": "ok"}


# STAGE 2: READ


@app.get("/tasks")
def get_tasks():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tasks")
    rows = cursor.fetchall()
    
    tasks = []
    for row in rows:
        tasks.append({
            "id": row["id"],
            "title": row["title"],
            "done": bool(row["done"])
        })
        
    conn.close()
    return tasks

@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    
    conn.close()
    
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task with id {task_id} not found"
        )
    
    return {
        "id": row["id"],
        "title": row["title"],
        "done": bool(row["done"])
    }


# STAGE 3: CREATE


@app.post("/tasks", status_code=201)
def create_task(task_data: TaskCreate):
    title = task_data.title
    if not title or title.strip() == "":
        raise HTTPException(
            status_code=400, 
            detail="Title is required and cannot be empty"
        )
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("INSERT INTO tasks (title, done) VALUES (?, ?)", (title, 0))
    new_id = cursor.lastrowid
    conn.commit()

    cursor.execute("SELECT * FROM tasks WHERE id = ?", (new_id,))
    row = cursor.fetchone()
   
    conn.close()
    
    return {
        "id": row["id"],
        "title": row["title"],
        "done": bool(row["done"])
    }


# STAGE 4: UPDATE


@app.put("/tasks/{task_id}")
def update_task(task_id: int, task_data: TaskUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    
    if row is None:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found"
        )
    
    if task_data.title is not None and task_data.title.strip() == "":
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="Title cannot be empty"
        )
        
    updates = []
    values = []
    
    if task_data.title is not None:
        updates.append("title = ?")
        values.append(task_data.title)

    if task_data.done is not None:
        updates.append("done = ?")
        values.append(1 if task_data.done else 0)

    if not updates:
        conn.close()
        return {
            "id": row["id"],
            "title": row["title"],
            "done": bool(row["done"])
        }

    query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
    values.append(task_id)
    
    cursor.execute(query, values)
    conn.commit()
    
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    updated_row = cursor.fetchone()
    
    conn.close()
    
    return {
        "id": updated_row["id"],
        "title": updated_row["title"],
        "done": bool(updated_row["done"])
    }

# STAGE 4: DELETE

@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    
    if row is None:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found"
        )
    
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

# START THE SERVER

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)