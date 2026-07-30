from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI()

# DATA

tasks = [
    {"id": 1, "title": "Learn FastAPI", "done": False},
    {"id": 2, "title": "Build a CRUD API", "done": False},
    {"id": 3, "title": "Submit assignment", "done": False}
]
next_id = 4


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
    return tasks

@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task

    raise HTTPException(
        status_code=404, 
        detail=f"Task with id {task_id} not found"
    )


# STAGE 3: CREATE


@app.post("/tasks", status_code=201)
def create_task(task_data: TaskCreate):
    title = task_data.title
    if not title or title.strip() == "":
        raise HTTPException(
            status_code=400, 
            detail="Title is required and cannot be empty"
        )
    
    global next_id
    new_task = {
        "id": next_id,
        "title": title,
        "done": False
    }
    tasks.append(new_task)
    next_id += 1
    return new_task


# STAGE 4: UPDATE


@app.put("/tasks/{task_id}")
def update_task(task_id: int, task_data: TaskUpdate):

    task = None
    for t in tasks:
        if t["id"] == task_id:
            task = t
            break
    
    if task is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found"
        )
    
    if task_data.title is not None:
        task["title"] = task_data.title
    
    if task_data.done is not None:
        task["done"] = task_data.done
    
    return task


# STAGE 4: DELETE



@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    global tasks
    
    for i, task in enumerate(tasks):
        if task["id"] == task_id:
            tasks.pop(i)
            return
    
    raise HTTPException(
        status_code=404,
        detail=f"Task {task_id} not found"
    )


# START THE SERVER


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)