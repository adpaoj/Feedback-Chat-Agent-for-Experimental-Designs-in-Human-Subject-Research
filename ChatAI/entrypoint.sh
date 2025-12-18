#!/bin/sh

# Initialize the database
echo "Initializing database..."
flask init-db

# Start the application
if [ "$FLASK_DEBUG" = "1" ]; then
    echo "Running in debug mode with hot reload"
    exec flask run --host=0.0.0.0 --port=5000
else
    echo "Running in production mode"
    exec gunicorn --bind 0.0.0.0:5000 run:app
fi
