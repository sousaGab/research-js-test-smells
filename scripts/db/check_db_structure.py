#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Checks the database structure
"""

import sqlite3
from llm_refactor.core.paths import REPO_ROOT
from pathlib import Path

# Locate the database
db_path = REPO_ROOT / "smell-selector-ui" / "research.db"

if not db_path.exists():
    print(f"Database not found at: {db_path}")
    exit(1)

print(f"Banco de dados: {db_path}\n")

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Listar todas as tabelas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("Tables in the database:")
for table in tables:
    print(f"  - {table[0]}")

conn.close()
