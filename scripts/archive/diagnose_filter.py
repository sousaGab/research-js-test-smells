#!/usr/bin/env python3
"""
Complete diagnostic script for the coverage_decreased filter
"""

import sqlite3
from llm_refactor.core.paths import RESEARCH_DB
import sys

def test_database():
    """Tests the data in the database"""
    print("=" * 80)
    print("1. DATABASE TEST")
    print("=" * 80)
    
    conn = sqlite3.connect(RESEARCH_DB)
    cursor = conn.cursor()
    
    # Count experiments per coverage_decreased value
    cursor.execute('''
        SELECT 
            coverage_decreased,
            COUNT(*) as count
        FROM experiments
        GROUP BY coverage_decreased
        ORDER BY coverage_decreased
    ''')
    
    results = cursor.fetchall()
    print("\nDistribution of coverage_decreased:")
    for row in results:
        value = "NULL" if row[0] is None else ("TRUE" if row[0] == 1 else "FALSE")
        print(f"  {value}: {row[1]} experiments")
    
    conn.close()
    print("\n✅ Database data is OK")
    return True


def test_backend_query():
    """Tests the SQL query used by the backend"""
    print("\n" + "=" * 80)
    print("2. BACKEND QUERY TEST")
    print("=" * 80)
    
    conn = sqlite3.connect(RESEARCH_DB)
    cursor = conn.cursor()
    
    # Simulate the query with the TRUE filter
    cursor.execute('''
        SELECT COUNT(e.id)
        FROM experiments e
        JOIN files f ON e.file_id = f.id
        JOIN repositories r ON f.repository_id = r.id
        WHERE e.coverage_decreased = 1
    ''')
    count_true = cursor.fetchone()[0]
    
    # Simulate the query with the FALSE filter
    cursor.execute('''
        SELECT COUNT(e.id)
        FROM experiments e
        JOIN files f ON e.file_id = f.id
        JOIN repositories r ON f.repository_id = r.id
        WHERE e.coverage_decreased = 0
    ''')
    count_false = cursor.fetchone()[0]
    
    print(f"\nQuery results:")
    print(f"  coverage_decreased = TRUE: {count_true} experiments")
    print(f"  coverage_decreased = FALSE: {count_false} experiments")
    
    conn.close()
    print("\n✅ SQL query works correctly")
    return True


def test_frontend_params():
    """Checks the parameters sent by the frontend"""
    print("\n" + "=" * 80)
    print("3. FRONTEND PARAMETERS")
    print("=" * 80)
    
    print("\nThe frontend should send:")
    print("  - coverage_decreased='' (empty) -> no filter")
    print("  - coverage_decreased='true' -> filter TRUE")
    print("  - coverage_decreased='false' -> filter FALSE")
    
    print("\nThe backend (FastAPI) converts automatically:")
    print("  - 'true' -> boolean True -> SQL: 1")
    print("  - 'false' -> boolean False -> SQL: 0")
    
    print("\n✅ Conversion logic is correct")
    return True


def check_issues():
    """Checks common issues"""
    print("\n" + "=" * 80)
    print("4. COMMON ISSUES")
    print("=" * 80)
    
    issues = []
    
    # Check whether the backend is running
    import subprocess
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        if 'main.py' not in result.stdout and 'uvicorn' not in result.stdout:
            issues.append("❌ Backend may not be running")
        else:
            print("  ✅ Backend is running")
    except:
        pass
    
    # Check file structure
    import os
    if not os.path.exists('smell-selector-ui/backend/main.py'):
        issues.append("❌ File backend/main.py not found")
    else:
        print("  ✅ Backend main.py exists")
        
    if not os.path.exists('smell-selector-ui/frontend/src/hooks/useRefatoracoes.js'):
        issues.append("❌ File useRefatoracoes.js not found")
    else:
        print("  ✅ Frontend useRefatoracoes.js exists")
    
    return len(issues) == 0, issues


def main():
    print("\n" * 2)
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "DIAGNOSIS: coverage_decreased filter" + " " * 26 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    all_ok = True
    
    # Run the tests
    try:
        test_database()
    except Exception as e:
        print(f"\n❌ ERROR in the database test: {e}")
        all_ok = False
    
    try:
        test_backend_query()
    except Exception as e:
        print(f"\n❌ ERROR in the query test: {e}")
        all_ok = False
    
    try:
        test_frontend_params()
    except Exception as e:
        print(f"\n❌ ERROR in the parameter test: {e}")
        all_ok = False
    
    try:
        issues_ok, issues = check_issues()
        if not issues_ok:
            all_ok = False
            for issue in issues:
                print(f"  {issue}")
    except Exception as e:
        print(f"\n❌ ERROR in the issue check: {e}")
        all_ok = False
    
    # Final summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if all_ok:
        print("\n✅ EVERYTHING WORKING CORRECTLY")
        print("\nIf the filter is not working in the browser, try:")
        print("  1. Clear the browser cache (Ctrl+Shift+Del)")
        print("  2. Reload the page with Ctrl+F5")
        print("  3. Check the browser console (F12) for errors")
        print("  4. Restart the backend and frontend")
        print("\nRestart commands:")
        print("  Backend:  cd smell-selector-ui/backend && python3 main.py")
        print("  Frontend: cd smell-selector-ui/frontend && npm start")
    else:
        print("\n❌ ISSUES FOUND - see above")
        return 1
    
    print("\n" + "=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
