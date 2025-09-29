#!/bin/bash

# Start postgres database container
echo "Starting database..."
docker compose up -d db

# Wait for the database to start
until docker exec wgs_db pg_isready -U wgs_user; do
  sleep 1
done
echo "Database is ready"