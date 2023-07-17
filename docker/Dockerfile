# FROM python:3.11 doesn't works with aioredis, see: https://github.com/aio-libs/aioredis-py/issues/1409
#FROM python:3.10.9-slim-buster
FROM python:3.11-slim-buster

RUN apt-get update && \
    apt-get install -y gcc libpq-dev && \
    apt clean && \
    rm -rf /var/cache/apt/*

ENV TZ 'Europe/Warsaw'
ENV PYTHONIOENCODING utf-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN echo $TZ > /etc/timezone && apt-get update && \
    apt-get install -y tzdata && \
    rm /etc/localtime && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

RUN pip install --upgrade pip setuptools wheel

COPY ../app/requirements /tmp/requirements

RUN pip install --no-cache-dir -r /tmp/requirements/dev.txt

#EXPOSE 8000

# STOPSIGNAL SIGINT

# Copy project code.
COPY ../app /src
#COPY ./scripts /src/scripts

ENV PATH "$PATH:/src/scripts"

RUN useradd -m -d /src -s /bin/bash app \
    && chown -R app:app /src/* && chmod +x /src/scripts/*

WORKDIR /src

USER app

CMD ["./scripts/start-dev.sh"]
#CMD ["uvicorn", "--host", "0.0.0.0", "--reload", "--reload-dir", "/app", "app:app"]
