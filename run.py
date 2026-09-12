#!/usr/bin/env python
"""
Quick Start Launcher for AgileFlow
Automatically applies migrations, seeds sample mock data, and starts the server.
"""
import os
import sys
import subprocess

def main():
    print("=" * 60)
    print("🚀 Starting AgileFlow (Project Pulse)...")
    print("=" * 60)

    # 1. Apply database migrations
    print("1/3 Applying database migrations...")
    subprocess.run([sys.executable, "manage.py", "migrate"], check=True)

    # 2. Seed sample mock data
    print("2/3 Seeding initial sample data...")
    subprocess.run([sys.executable, "manage.py", "seed_backlog"], check=True)

    # 3. Start development server
    print("3/3 Starting development server at http://127.0.0.1:8000/")
    print("=" * 60)
    print("Open your browser at: http://127.0.0.1:8000/")
    print("Press CTRL+C to stop the server.")
    print("=" * 60)
    subprocess.run([sys.executable, "manage.py", "runserver"])

if __name__ == '__main__':
    main()
