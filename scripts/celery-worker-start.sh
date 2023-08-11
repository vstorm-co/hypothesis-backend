#!/bin/bash

set -o errexit
set -o nounset

celery -A celery worker --loglevel=info
