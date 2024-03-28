# Stage 1: Build
FROM python:3.11.8-slim-bullseye as builder

RUN apt-get update && apt-get install -y gcc libpq-dev tzdata && apt clean && rm -rf /var/cache/apt/*

ENV TZ 'Europe/Warsaw'
ENV PYTHONIOENCODING utf-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime

RUN pip install --upgrade pip setuptools wheel

COPY ../app/requirements /tmp/requirements

RUN pip install --no-cache-dir -r /tmp/requirements/dev.txt
RUN playwright install

# Copy project code.
COPY ../app /src
COPY ../scripts /src/scripts

ENV PATH="$PATH:/src/scripts"

RUN useradd -m -d /src -s /bin/bash app && chown -R app:app /src/* && chmod +x /src/scripts/*

# Stage 2: Runtime
FROM python:3.11.8-bullseye

RUN useradd -m -d /src -s /bin/bash app
ENV PATH="$PATH:/src/scripts"

COPY --from=builder /src /src
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

COPY ../scripts/celery-worker-start.sh /start-celeryworker
RUN sed -i 's/\r$//g' /start-celeryworker
RUN chmod +x /start-celeryworker

COPY ../scripts/celery-beat-start.sh /start-celerybeat
RUN sed -i 's/\r$//g' /start-celerybeat
RUN chmod +x /start-celerybeat

COPY ../scripts/celery-flower-start.sh /start-flower
RUN sed -i 's/\r$//g' /start-flower
RUN chmod +x /start-flower

COPY ../scripts/start-dev.sh /start-app
RUN sed -i 's/\r$//g' /start-app
RUN chmod +x /start-app

WORKDIR /src

USER app

CMD ["/start-app"]
