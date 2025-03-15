#!/bin/bash

# export env variables from .env file
# cd into app directory
cd app
# export env variables
export $(grep -v '^#' .env | xargs -0)
# cd back to root directory
cd ..

# Check if we want to run in production mode
if [ "$1" == "prod" ] || [ "$1" == "production" ]; then
    echo "Starting server in production mode with Gunicorn..."
    gunicorn --bind 0.0.0.0:3001 --workers 4 run:app
else
    echo "Starting server in development mode..."
    python run.py
fi