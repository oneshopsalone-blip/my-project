#!/bin/bash

# Exit on error
set -e

echo "🚀 Starting deployment..."

# Print Python version
python --version

# Run migrations
echo "📦 Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "🎨 Collecting static files..."
python manage.py collectstatic --noinput

# Start the application
echo "✅ Starting Gunicorn..."
exec gunicorn data.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 4 \
    --threads 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -