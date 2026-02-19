FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

RUN addgroup --system app \
    && adduser --system --ingroup app app

COPY --chown=app:app . .

USER app

CMD [ "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000" ]
