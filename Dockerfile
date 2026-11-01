FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY prompts ./prompts
COPY data ./data

RUN useradd --create-home --uid 1000 botuser \
    && chown -R botuser:botuser /app
USER botuser

CMD ["python", "-m", "alina_bot"]
