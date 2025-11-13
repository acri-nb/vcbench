#!/bin/bash

# Configuration pour VCBench
# Port 8002 pour éviter les conflits avec iskyLims (8001)
# Host 0.0.0.0 pour permettre l'accès depuis l'extérieur
uvicorn api.app.main:app --reload --host 0.0.0.0 --port 8002