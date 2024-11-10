import os
import uuid

import redis
from celery import Celery
from fastapi import FastAPI, HTTPException, Header, Depends
# from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

app = FastAPI()

redis_host = os.getenv('REDIS_HOST', 'redis')
redis_port = int(os.getenv('REDIS_PORT', '6379'))
redis_db = int(os.getenv('REDIS_DB', '0'))
r = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)

celery_app = Celery(
    'tasks',
    broker=f'redis://{redis_host}:{redis_port}/{redis_db}',
    backend=f'redis://{redis_host}:{redis_port}/{redis_db}'
)

API_TOKEN = os.getenv('API_TOKEN', 'token')


class PromptRequest(BaseModel):
    prompt: str


def get_token_header(x_token: str = Header(...)):
    if x_token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


# app.state.submitted_tasks = 0
# app.state.successful_tasks = 0
# app.state.failed_tasks = 0


@app.post("/submit", dependencies=[Depends(get_token_header)])
async def submit_prompt(request: PromptRequest):
    task_id = str(uuid.uuid4())
    r.set(f"prompt:{task_id}", request.prompt , ex=300)
    r.set(f"status:{task_id}", "pending", ex=300)
    celery_app.send_task('tasks.process_task', args=[task_id, request.prompt])
    # app.state.submitted_tasks += 1
    return {"task_id": task_id}


@app.get("/status/{task_id}", dependencies=[Depends(get_token_header)])
async def get_status(task_id: str):
    status = r.get(f"status:{task_id}")
    error = r.get(f"error:{task_id}")
    if status:
        return {"status": status, "error": error}
    else:
        raise HTTPException(status_code=404, detail="Task not found")


@app.get("/result/{task_id}", dependencies=[Depends(get_token_header)])
async def get_result(task_id: str):
    result = r.get(f"result:{task_id}")
    if result:
        r.delete(f"result:{task_id}")
        r.delete(f"prompt:{task_id}")
        r.delete(f"status:{task_id}")
        return {"result": result}
    else:
        raise HTTPException(status_code=404, detail="Result not found")


# Instrumentator().instrument(app).expose(app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
