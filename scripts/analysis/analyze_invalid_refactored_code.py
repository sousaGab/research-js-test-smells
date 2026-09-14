#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyzes experiments to find invalid refactored code
(no JavaScript methods, or prose without comment markers)
"""

import sqlite3
from llm_refactor.core.paths import RESEARCH_DB
import re
from pathlib import Path

# Locate the database
db_path = RESEARCH_DB

if not db_path.exists():
    print(f"❌ Database not found at: {db_path}")
    exit(1)

print(f"📊 Analyzing database: {db_path}\n")

# Connect to the database
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

def has_javascript_function(code):
    """Checks whether the code contains any JavaScript function or method"""
    if not code or code.strip() == '':
        return False
    
    # JavaScript function patterns
    patterns = [
        r'function\s+\w+\s*\(',  # function name()
        r'function\s*\(',  # function ()
        r'\w+\s*:\s*function\s*\(',  # name: function()
        r'\w+\s*\([^)]*\)\s*{',  # name() { (arrow or method)
        r'=>\s*{',  # arrow function
        r'const\s+\w+\s*=\s*\(',  # const name = (
        r'let\s+\w+\s*=\s*\(',  # let name = (
        r'var\s+\w+\s*=\s*\(',  # var name = (
        r'class\s+\w+',  # class Name
        r'\w+\s*\([^)]*\)\s*\{',  # method
        r'async\s+function',  # async function
        r'async\s+\w+\s*\(',  # async name()
    ]
    
    for pattern in patterns:
        if re.search(pattern, code, re.MULTILINE):
            return True
    
    return False

def has_uncommented_text(code):
    """Checks for text that looks like uncommented prose or explanation"""
    if not code or code.strip() == '':
        return False
    
    # Strip line comments
    temp = re.sub(r'//.*$', '', code, flags=re.MULTILINE)
    # Strip block comments
    temp = re.sub(r'/\*.*?\*/', '', temp, flags=re.DOTALL)
    # Remove strings
    temp = re.sub(r'"[^"]*"', '', temp)
    temp = re.sub(r"'[^']*'", '', temp)
    temp = re.sub(r'`[^`]*`', '', temp)
    
    # Look for lines that resemble explanatory prose
    lines = temp.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check for word sequences without code syntax
        # Long space-separated lines are probably prose
        words = line.split()
        if len(words) > 10 and not any(char in line for char in ['{', '}', '(', ')', ';', '=']):
            return True
        
        # Lines starting with a capitalized word followed by a sentence
        if re.match(r'^[A-Z][a-z]+\s+[a-z]+\s+[a-z]+', line):
            # But not TypeScript/JSDoc
            if not line.startswith('import') and not line.startswith('export') and not line.startswith('const') and not line.startswith('let'):
                return True
    
    return False

def analyze_code(code, code_type='refactored_code'):
    """Analyzes a code snippet and returns the issues found"""
    issues = []
    
    if not code or code.strip() == '':
        issues.append('empty')
        return issues
    
    if not has_javascript_function(code):
        issues.append('no_function')
    
    if has_uncommented_text(code):
        issues.append('uncommented_text')
    
    # Very short content is probably not valid code
    if len(code.strip()) < 20:
        issues.append('too_short')
    
    # Check for LLM error messages or response text
    llm_phrases = [
        'I apologize',
        'I cannot',
        'I am not able',
        'I do not have',
        'Here is',
        'Here are',
        'Based on',
        'The refactored',
        'This refactoring',
        'Note that',
        'Please note',
        'Sorry',
    ]
    
    for phrase in llm_phrases:
        if phrase.lower() in code.lower():
            issues.append('llm_response_text')
            break
    
    return issues

# Query all experiments
query = """
SELECT 
    e.id,
    e.experiment_date,
    e.ai_tool,
    e.ai_model_version,
    e.prompting_approach,
    e.refactored_code,
    e.refactored_method,
    e.original_code,
    e.original_method,
    e.refactoring_completed,
    e.smell_removed,
    bsd.smell_type,
    r.name as repository,
    f.path as file_path
FROM experiments e
LEFT JOIN baseline_smell_detections bsd ON e.baseline_smell_id = bsd.id
LEFT JOIN files f ON e.file_id = f.id
LEFT JOIN repositories r ON f.repository_id = r.id
ORDER BY e.id ASC
"""

cursor.execute(query)
results = cursor.fetchall()

print(f"📋 Total experiments: {len(results)}\n")

# Issue categories
problematic_experiments = []

for row in results:
    # Prefer refactored_method when present
    refactored_code = row['refactored_method'] if row['refactored_method'] else row['refactored_code']
    code_type = 'refactored_method' if row['refactored_method'] else 'refactored_code'
    
    issues = analyze_code(refactored_code, code_type)
    
    if issues:
        problematic_experiments.append({
            'id': row['id'],
            'date': row['experiment_date'],
            'model': f"{row['ai_tool']} / {row['ai_model_version']}",
            'approach': row['prompting_approach'],
            'smell_type': row['smell_type'],
            'repository': row['repository'],
            'file_path': row['file_path'],
            'refactoring_completed': row['refactoring_completed'],
            'smell_removed': row['smell_removed'],
            'code_type': code_type,
            'code_length': len(refactored_code) if refactored_code else 0,
            'issues': issues,
            'code_preview': refactored_code[:200] if refactored_code else ''
        })

# Report
print("=" * 120)
print(f"🔍 EXPERIMENTS WITH PROBLEMATIC REFACTORED CODE: {len(problematic_experiments)}")
print("=" * 120)

# Group by issue type
issue_categories = {
    'empty': [],
    'no_function': [],
    'uncommented_text': [],
    'too_short': [],
    'llm_response_text': []
}

for exp in problematic_experiments:
    for issue in exp['issues']:
        issue_categories[issue].append(exp)

# Report per category
print("\n📊 SUMMARY BY ISSUE TYPE:\n")

for issue_type, exps in issue_categories.items():
    if not exps:
        continue
    
    issue_names = {
        'empty': 'Empty code',
        'no_function': 'No JavaScript function/method',
        'uncommented_text': 'Uncommented prose',
        'too_short': 'Code too short (<20 chars)',
        'llm_response_text': 'LLM response text (not code)'
    }
    
    print(f"🔸 {issue_names[issue_type]}: {len(exps)} experiments")

# Details of the most problematic experiments
print("\n" + "=" * 120)
print("📋 DETAILS OF PROBLEMATIC EXPERIMENTS")
print("=" * 120)

# Sort by number of issues, most problematic first
problematic_experiments.sort(key=lambda x: len(x['issues']), reverse=True)

for i, exp in enumerate(problematic_experiments[:50], 1):  # Show up to 50
    print(f"\n{i}. 🔹 Experiment #{exp['id']}")
    print(f"   📅 Date: {exp['date']}")
    print(f"   🤖 Model: {exp['model']}")
    print(f"   📝 Approach: {exp['approach']}")
    print(f"   🧪 Smell: {exp['smell_type']}")
    print(f"   📁 Repo: {exp['repository']} - {exp['file_path']}")
    print(f"   📊 Refactoring completed: {'Yes' if exp['refactoring_completed'] else 'No'}")
    print(f"   📊 Smell removed: {'Yes' if exp['smell_removed'] else 'No' if exp['smell_removed'] is not None else 'N/A'}")
    print(f"   ⚠️  Issues found: {', '.join(exp['issues'])}")
    print(f"   📏 Code length: {exp['code_length']} characters")
    
    if exp['code_preview']:
        preview = exp['code_preview'].replace('\n', ' ')[:150]
        print(f"   👁️  Preview: {preview}...")
    
    print("-" * 120)

# Overall statistics
print("\n" + "=" * 120)
print("📊 OVERALL STATISTICS")
print("=" * 120)

total_experiments = len(results)
problematic_count = len(problematic_experiments)
valid_count = total_experiments - problematic_count

print(f"\n✅ Experiments with valid code: {valid_count} ({valid_count/total_experiments*100:.1f}%)")
print(f"⚠️  Experiments with issues: {problematic_count} ({problematic_count/total_experiments*100:.1f}%)")

# Statistics per model
print("\n📊 ISSUES BY MODEL:")
cursor.execute("""
SELECT 
    ai_tool,
    ai_model_version,
    COUNT(*) as total
FROM experiments
GROUP BY ai_tool, ai_model_version
ORDER BY total DESC
""")

model_totals = {f"{row['ai_tool']} / {row['ai_model_version']}": row['total'] for row in cursor.fetchall()}

model_problems = {}
for exp in problematic_experiments:
    model = exp['model']
    if model not in model_problems:
        model_problems[model] = 0
    model_problems[model] += 1

for model, total in model_totals.items():
    problems = model_problems.get(model, 0)
    print(f"   • {model}: {problems}/{total} problematic ({problems/total*100:.1f}%)")

conn.close()
print("\n✅ Analysis complete!")
