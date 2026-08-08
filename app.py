from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set!")

app = FastAPI()

# Pydantic models for request validation
class TaskCreate(BaseModel):
    title: str

class TaskUpdate(BaseModel):
    title: str = None
    done: bool = None

def get_db_connection():
    """Create and return a connection to PostgreSQL."""
    return psycopg2.connect(DATABASE_URL)

def init_database():
    """Create tasks table if it doesn't exist, and seed 3 example tasks if empty."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            done BOOLEAN DEFAULT FALSE
        )
    """)
    conn.commit()

    # Check if table is empty
    cursor.execute("SELECT COUNT(*) as count FROM tasks")
    row_count = cursor.fetchone()[0]

    # Seed only if empty
    if row_count == 0:
        cursor.execute("INSERT INTO tasks (title, done) VALUES (%s, %s)", ("Learn FastAPI", False))
        cursor.execute("INSERT INTO tasks (title, done) VALUES (%s, %s)", ("Build a CRUD API", False))
        cursor.execute("INSERT INTO tasks (title, done) VALUES (%s, %s)", ("Submit assignment", True))
        conn.commit()
        print("✅ Database seeded with 3 example tasks!")
    else:
        print(f"📊 Database already has {row_count} tasks. Skipping seeding.")

    cursor.close()
    conn.close()

# Initialize database on startup
init_database()

# Public endpoints
@app.get("/")
def hello():
    return {"message": "Hello Bhai!"}

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

# CRUD endpoints
@app.get("/tasks")
def get_tasks():
    """Return all tasks from the database."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT id, title, done FROM tasks")
    tasks = cursor.fetchall()
    cursor.close()
    conn.close()
    return tasks

@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    """Return a single task by ID. Returns 404 if not found."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT id, title, done FROM tasks WHERE id = %s", (task_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")
    return row

@app.post("/tasks", status_code=201)
def create_task(task_data: TaskCreate):
    """Create a new task. Validates that title is not empty."""
    title = task_data.title
    if not title or title.strip() == "":
        raise HTTPException(status_code=400, detail="Title is required and cannot be empty")

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id, title, done",
        (title, False)
    )
    new_task = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    return new_task

@app.put("/tasks/{task_id}")
def update_task(task_id: int, task_data: TaskUpdate):
    """Update a task. Supports partial updates (title, done, or both)."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Check if task exists
    cursor.execute("SELECT id FROM tasks WHERE id = %s", (task_id,))
    if cursor.fetchone() is None:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Build dynamic update query
    updates = []
    values = []

    if task_data.title is not None:
        if task_data.title.strip() == "":
            cursor.close()
            conn.close()
            raise HTTPException(status_code=400, detail="Title cannot be empty")
        updates.append("title = %s")
        values.append(task_data.title)

    if task_data.done is not None:
        updates.append("done = %s")
        values.append(task_data.done)

    if not updates:
        cursor.execute("SELECT id, title, done FROM tasks WHERE id = %s", (task_id,))
        task = cursor.fetchone()
        cursor.close()
        conn.close()
        return task

    values.append(task_id)
    query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = %s RETURNING id, title, done"
    cursor.execute(query, values)
    updated_task = cursor.fetchone()

    conn.commit()
    cursor.close()
    conn.close()
    return updated_task

@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    """Delete a task by ID. Returns 204 No Content on success."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))

    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    conn.commit()
    cursor.close()
    conn.close()
    return

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)