#!/usr/bin/env bash
set -o errexit

echo "Installing backend dependencies..."
pip install -r Backend/requirements.txt

echo "Installing frontend dependencies..."
cd Frontend
npm install

echo "Building React frontend..."
npm run build
cd ..

echo "Build complete."
