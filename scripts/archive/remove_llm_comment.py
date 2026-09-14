#!/usr/bin/env python3
"""
Temporary script to remove the LLM instructional comment from refactored code.

Removes the line: // Your COMPLETE refactored test code here
"""

import sqlite3
from llm_refactor.core.paths import RESEARCH_DB
import re

DB_PATH = RESEARCH_DB
COMMENT_TO_REMOVE = '// Your COMPLETE refactored test code here'

def remove_instructional_comment(code):
    """Removes the instructional comment line, preserving all other lines."""
    if not code:
        return code
    
    lines = code.split('\n')
    filtered_lines = []
    
    for line in lines:
        # Drop the line that contains exactly the comment, allowing surrounding spaces
        if line.strip() == COMMENT_TO_REMOVE:
            continue
        filtered_lines.append(line)
    
    # Drop a leading empty line left behind after removing the comment
    result = '\n'.join(filtered_lines)
    
    # Collapse multiple leading empty lines
    while result.startswith('\n\n'):
        result = result[1:]
    
    return result

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Fetch every refactored code containing the comment
    cursor.execute("""
        SELECT id, refactored_code 
        FROM experiments 
        WHERE refactored_code LIKE ?
    """, (f'%{COMMENT_TO_REMOVE}%',))
    
    rows = cursor.fetchall()
    
    print(f"Found {len(rows)} records with the instructional comment")
    
    if len(rows) == 0:
        print("✅ No record needs updating")
        conn.close()
        return
    
    updated_count = 0
    
    for experiment_id, refactored_code in rows:
        # Remove the comment
        cleaned_code = remove_instructional_comment(refactored_code)
        
        # Update the database
        cursor.execute("""
            UPDATE experiments 
            SET refactored_code = ?
            WHERE id = ?
        """, (cleaned_code, experiment_id))
        
        updated_count += 1
        
        # Show a preview for the first 3
        if updated_count <= 3:
            print(f"\n--- Experiment ID {experiment_id} ---")
            print("BEFORE (first 3 lines):")
            print('\n'.join(refactored_code.split('\n')[:3]))
            print("\nAFTER (first 3 lines):")
            print('\n'.join(cleaned_code.split('\n')[:3]))
    
    # Commit the changes
    conn.commit()
    conn.close()
    
    print(f"\n✅ {updated_count} records updated successfully!")
    print(f"   Comment '{COMMENT_TO_REMOVE}' removed")

if __name__ == '__main__':
    main()
