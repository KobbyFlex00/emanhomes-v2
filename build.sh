#!/usr/bin/env bash
set -o errexit

python -m pip install -r requirements.txt
python manage.py collectstatic --noinput --upload-unhashed-files
python manage.py migrate --noinput
