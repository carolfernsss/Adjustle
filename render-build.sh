#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -e

echo "=== Building React Frontend ==="
cd Frontend
npm install
npm run build
cd ..

echo "=== Installing Python Backend Dependencies ==="
cd Backend
pip install -r requirements.txt
cd ..

echo "=== Build Complete ==="
