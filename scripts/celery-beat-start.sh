#!/bin/bash

set -o errexit
set -o nounset

rm -f './celerybeat.pid'

cd app
celery -A src.tasks.celery_app beat -l info --concurrency=1
