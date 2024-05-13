#!/bin/bash

set -o errexit
set -o nounset

cd app
celery -A src.tasks.celery_app worker --loglevel=info --concurrency=1
