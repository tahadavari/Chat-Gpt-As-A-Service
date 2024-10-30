FROM python:3.12


WORKDIR /app


COPY requirements.txt .
COPY main.py .
COPY tasks.py .


RUN pip install --no-cache-dir -r requirements.txt


CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
