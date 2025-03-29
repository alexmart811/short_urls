#!/bin/bash

cd src

celery -A redis_folder.tasks worker --loglevel=INFO