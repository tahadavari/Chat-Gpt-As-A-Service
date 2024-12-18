import os

import redis
from celery import Celery
from openai import OpenAI

openai_api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(
    api_key=openai_api_key,
)

redis_host = os.getenv('REDIS_HOST', 'redis')
redis_port = int(os.getenv('REDIS_PORT', '6379'))
redis_db = int(os.getenv('REDIS_DB', '0'))
r = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)

celery_app = Celery(
    'tasks',
    broker=f'redis://{redis_host}:{redis_port}/{redis_db}',
    backend=f'redis://{redis_host}:{redis_port}/{redis_db}'
)


@celery_app.task(name='tasks.process_task')
def process_task(task_id, prompt):
    r.set(f"status:{task_id}", "running")
    try:
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="chatgpt-4o-latest",
        )
        result_text = response.choices[0].message.content

        r.set(f"result:{task_id}", result_text, ex=900)
        r.set(f"status:{task_id}", "done")
    except Exception as e:
        r.set(f"status:{task_id}", "failed")
        r.set(f"error:{task_id}", str(e))
