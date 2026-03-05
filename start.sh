#!/bin/bash

# Exit on error
set -e

echo "========================================="
echo "🚀 Starting Vehicle Management System"
echo "========================================="

# Print environment info
echo "Python version: $(python --version)"
echo "Current directory: $(pwd)"
echo "DATABASE_URL exists: $(if [ -n "$DATABASE_URL" ]; then echo "✅ Yes"; else echo "❌ No"; fi)"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p /opt/render/project/src/staticfiles
mkdir -p /opt/render/project/src/media
mkdir -p /opt/render/project/src/logs

# Run migrations
echo "📦 Running database migrations..."
python manage.py migrate --noinput

# Check if migrations were successful
if [ $? -eq 0 ]; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Migrations failed"
    exit 1
fi

# Collect static files
echo "🎨 Collecting static files..."
python manage.py collectstatic --noinput

echo "========================================="
echo "✅ Starting Gunicorn server..."
echo "========================================="

# Start the application
exec gunicorn data.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 4 \
    --threads 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -python manage.py runserver_plus --cert-file cert.crt 9000