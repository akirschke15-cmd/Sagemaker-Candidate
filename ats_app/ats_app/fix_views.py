#!/usr/bin/env python3
"""
Quick fix script to clean up orphaned code in view files
"""
import os
import glob

def fix_view_file(filepath):
    """Remove orphaned code from the beginning of view files"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find the first 'def render_' line
    render_start = None
    for i, line in enumerate(lines):
        if line.strip().startswith('def render_'):
            render_start = i
            break

    if render_start is None:
        print(f"WARNING: No render function found in {filepath}")
        return False

    # Keep docstring and imports before render function
    # Remove any orphaned code between imports and render function
    new_lines = []
    in_imports = False
    last_import_line = 0

    for i in range(render_start):
        line = lines[i]
        # Check if it's part of docstring
        if i < 10 and ('"""' in line or "'''" in line or line.startswith('#')):
            new_lines.append(line)
        # Check if it's an import
        elif line.startswith('import ') or line.startswith('from '):
            new_lines.append(line)
            in_imports = True
            last_import_line = len(new_lines) - 1
        # Keep blank lines in imports section
        elif in_imports and line.strip() == '':
            new_lines.append(line)

    # Add blank lines after imports
    while new_lines and new_lines[-1].strip() == '':
        new_lines.pop()
    new_lines.append('\n')
    new_lines.append('\n')

    # Add the render function and everything after
    new_lines.extend(lines[render_start:])

    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    return True

# Fix all view files
view_files = glob.glob('views/*.py')
for vf in view_files:
    if vf.endswith('__init__.py') or vf.endswith('utils.py'):
        continue
    print(f"Fixing {vf}...")
    if fix_view_file(vf):
        print(f"  OK Fixed {vf}")
    else:
        print(f"  FAIL Could not fix {vf}")

print("\nDone!")
