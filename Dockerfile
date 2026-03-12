FROM python:3.11-slim

RUN apt-get update && apt-get install -y tor bash \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN python3 -m venv /app/venv

ENV PATH="/app/venv/bin:$PATH"

ENV PYTHONPATH="/app/src:/app"
ENV PATH="/app/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY torrc /etc/tor/torrc

RUN chmod +x /app/start.sh

RUN chown -R debian-tor:debian-tor /app

EXPOSE 5000

USER debian-tor

CMD ["/app/start.sh"]