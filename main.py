"""
FastAPI entrypoint for Railway deployment
"""
from fastapi import FastAPI
from api.main import app

# Re-export the app from api.main
# This allows Railway to use: uvicorn main:app

