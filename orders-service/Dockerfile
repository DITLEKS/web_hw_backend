FROM python:3.12-slim
WORKDIR /app
ENV PYTHONPATH=/app
COPY orders-service/requirements.txt .
COPY .wheels /wheels/
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY shared/ ./shared/
COPY orders-service/app/ ./app/
EXPOSE 3002
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3002"]