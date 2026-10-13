FROM python:3.12-slim
ARG INSTALL_MODELS=false
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HF_HOME=/models
WORKDIR /app
COPY pyproject.toml requirements.lock ./
COPY app ./app
COPY scripts ./scripts
RUN pip install --upgrade pip==26.2.1 && pip install -r requirements.lock && pip install --no-deps . && \
    if [ "$INSTALL_MODELS" = "true" ]; then pip install '.[models]'; fi && \
    useradd --uid 10001 --create-home rag && mkdir -p /models /app/data && chown -R rag:rag /models /app/data
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
