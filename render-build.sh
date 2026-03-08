#!/usr/bin/env bash
pip install -r Backend/requirements.txt
cd Frontend
npm install
npm run build
