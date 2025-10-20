FROM python:3.11-slim
WORKDIR /app

# ✅ Ensure requirements are copied before anything else
COPY server/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# ✅ Copy the full project AFTER installing dependencies
COPY . /app

ENV PORT=8080
EXPOSE 8080
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8080"]
