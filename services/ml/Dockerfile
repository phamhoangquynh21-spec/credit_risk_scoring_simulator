FROM python:3.12-slim

WORKDIR /app
# Root requirements (ML deps) + service requirements.
COPY requirements.txt ./root-requirements.txt
COPY services/ml/requirements.txt ./svc-requirements.txt
RUN pip install --no-cache-dir -r root-requirements.txt -r svc-requirements.txt

COPY src ./src
COPY services ./services
COPY models ./models
COPY data ./data

EXPOSE 8000
CMD ["uvicorn", "services.ml.main:app", "--host", "0.0.0.0", "--port", "8000"]
