FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app

# Install supervisor to run both web + worker in one container
RUN apt-get update \
	&& apt-get install -y --no-install-recommends supervisor \
	&& rm -rf /var/lib/apt/lists/*

# Copy supervisord config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Default: run supervisord which will start both the web app and the worker
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
