#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyzes experiments that consumed more than 4000 tokens
"""

import sqlite3
from llm_refactor.core.paths import RESEARCH_DB
from pathlib import Path

# Locate the database
db_path = RESEARCH_DB

if not db_path.exists():
    print(f"❌ Database not found at: {db_path}")
    exit(1)

print(f"📊 Analyzing database: {db_path}\n")

# Connect to the database
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row  # Access columns by name
cursor = conn.cursor()

# Query: experiments with more than 4000 tokens
query = """
SELECT 
    e.id,
    e.experiment_date,
    e.ai_tool,
    e.ai_model_version,
    e.prompting_approach,
    e.tokens_used,
    e.execution_time_seconds,
    e.llm_latency_seconds,
    e.smell_removed,
    e.refactoring_completed,
    e.tests_still_passing,
    bsd.smell_type,
    r.name as repository,
    f.path as file_path
FROM experiments e
LEFT JOIN baseline_smell_detections bsd ON e.baseline_smell_id = bsd.id
LEFT JOIN files f ON e.file_id = f.id
LEFT JOIN repositories r ON f.repository_id = r.id
WHERE e.tokens_used > 4000
ORDER BY e.tokens_used DESC
"""

cursor.execute(query)
results = cursor.fetchall()

if not results:
    print("✅ No experiment found with more than 4000 tokens.")
else:
    print(f"🔍 Found {len(results)} experiments with more than 4000 tokens:\n")
    print("=" * 120)
    
    total_tokens = 0
    
    for row in results:
        total_tokens += row['tokens_used'] if row['tokens_used'] else 0
        
        print(f"\n🔹 Experiment #{row['id']}")
        print(f"   📅 Date: {row['experiment_date']}")
        print(f"   🤖 Model: {row['ai_tool']} / {row['ai_model_version']}")
        print(f"   📝 Approach: {row['prompting_approach']}")
        print(f"   🪙 Tokens: {row['tokens_used']:,}")
        print(f"   ⏱️  Total time: {row['execution_time_seconds']:.2f}s" if row['execution_time_seconds'] else "   ⏱️  Total time: N/A")
        print(f"   ⚡ LLM latency: {row['llm_latency_seconds']:.2f}s" if row['llm_latency_seconds'] else "   ⚡ LLM latency: N/A")
        print(f"   🧪 Smell type: {row['smell_type']}")
        print(f"   📁 Repository: {row['repository']}")
        print(f"   📄 File: {row['file_path']}")
        print(f"   ✅ Smell removed: {'Yes' if row['smell_removed'] else 'No' if row['smell_removed'] is not None else 'N/A'}")
        print(f"   ✅ Refactoring completed: {'Yes' if row['refactoring_completed'] else 'No' if row['refactoring_completed'] is not None else 'N/A'}")
        print(f"   ✅ Tests passing: {'Yes' if row['tests_still_passing'] else 'No' if row['tests_still_passing'] is not None else 'N/A'}")
        print("-" * 120)
    
    print(f"\n📊 STATISTICS:")
    print(f"   • Total experiments: {len(results)}")
    print(f"   • Total tokens: {total_tokens:,}")
    print(f"   • Average tokens: {total_tokens / len(results):,.0f}")
    print(f"   • Maximum tokens: {max(row['tokens_used'] for row in results):,}")
    print(f"   • Minimum tokens above 4000: {min(row['tokens_used'] for row in results):,}")

# Statistics per model
print(f"\n📊 TOKENS BY MODEL:")
cursor.execute("""
SELECT 
    ai_tool,
    ai_model_version,
    COUNT(*) as count,
    SUM(tokens_used) as total_tokens,
    AVG(tokens_used) as avg_tokens,
    MAX(tokens_used) as max_tokens
FROM experiments
WHERE tokens_used > 4000
GROUP BY ai_tool, ai_model_version
ORDER BY total_tokens DESC
""")

model_stats = cursor.fetchall()
for row in model_stats:
    print(f"   • {row['ai_tool']} / {row['ai_model_version']}: {row['count']} experiments, {row['total_tokens']:,} tokens (avg: {row['avg_tokens']:,.0f}, max: {row['max_tokens']:,})")

# Statistics per smell type
print(f"\n📊 TOKENS BY SMELL TYPE:")
cursor.execute("""
SELECT 
    bsd.smell_type,
    COUNT(*) as count,
    SUM(e.tokens_used) as total_tokens,
    AVG(e.tokens_used) as avg_tokens,
    MAX(e.tokens_used) as max_tokens
FROM experiments e
LEFT JOIN baseline_smell_detections bsd ON e.baseline_smell_id = bsd.id
WHERE e.tokens_used > 4000
GROUP BY bsd.smell_type
ORDER BY total_tokens DESC
""")

smell_stats = cursor.fetchall()
for row in smell_stats:
    print(f"   • {row['smell_type']}: {row['count']} experiments, {row['total_tokens']:,} tokens (avg: {row['avg_tokens']:,.0f}, max: {row['max_tokens']:,})")

conn.close()
print("\n✅ Analysis complete!")
