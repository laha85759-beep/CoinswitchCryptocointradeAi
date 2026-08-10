FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app

# Default command can be overridden by Render startCommand or Docker run command
CMD ["/bin/sh", "-c", "python cs_bot_v2/run_forever.py"]
