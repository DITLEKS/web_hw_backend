FROM python:3.12-slim
WORKDIR /app
ENV PYTHONPATH=/app
COPY catalog-service/requirements.txt .
COPY .wheels /wheels/
RUN python -m pip install --no-index --find-links /wheels --no-cache-dir -r requirements.txt
COPY shared/ ./shared/
COPY catalog-service/app/ ./app/
EXPOSE 3001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3001"]