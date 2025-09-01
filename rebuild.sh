#!/bin/bash

# This script automates the process of rebuilding the application while preserving the database.
# It backs up the PostgreSQL data, tears down the environment, rebuilds the services,
# and then restores the data.

set -e # Exit immediately if a command exits with a non-zero status.

echo "### Stopping services..."
docker compose stop

echo "### Backing up database..."
docker run --rm -v nodes-monitor_postgres_data:/data -v /tmp:/backup ubuntu tar cvf /backup/postgres_backup.tar /data

echo "### Tearing down environment..."
docker compose down -v

echo "### Rebuilding and starting services..."
docker compose up --build -d

echo "### Stopping db service for data restoration..."
docker compose stop db

echo "### Restoring database..."
docker run --rm -v nodes-monitor_postgres_data:/data -v /tmp:/backup ubuntu tar xvf /backup/postgres_backup.tar -C /

echo "### Cleaning up backup file..."
echo 'Luftcia125@@' | sudo -S rm /tmp/postgres_backup.tar

echo "### Starting db service..."
docker compose up -d db
echo "### Waiting for db to be healthy..."
while [ -z "$(docker compose ps -q db | xargs docker inspect -f '{{.State.Health.Status}}' | grep 'healthy')" ]; do
    sleep 1
done
echo "### Starting other services..."
docker compose up -d

echo "### Rebuild complete. Your data has been preserved."
