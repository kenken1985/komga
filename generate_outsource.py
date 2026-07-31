#!/usr/bin/env python3
"""
generate_outsource.py - Generate outsource.md with goal statements, file contents, and project structure

Prompt:
Run generate_outsource.py and grab all the relevant files that 
contain all the function call that is need to aceieve the goal with the following goal:
<Insert goal statement here>

"""

import argparse
import os
import sys

def generate_tree(start_path, file_set, ignore_dirs=None):
    """Generate a tree-like string showing only files in file_set and their parent directories."""
    if ignore_dirs is None:
        ignore_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', '.venv', 'venv', '.mypy_cache'}

    file_set = set(os.path.abspath(f) for f in file_set)
    start_path = os.path.abspath(start_path)

    lines = []
    for root, dirs, files in os.walk(start_path):
        dirs[:] = sorted([d for d in dirs if d not in ignore_dirs])
        files = sorted(files)

        included = []
        for f in files:
            full = os.path.abspath(os.path.join(root, f))
            if full in file_set:
                included.append(f)

        if not included:
            continue

        rel_root = os.path.relpath(root, start_path)
        if rel_root == '.':
            lines.append('.')
        else:
            lines.append(rel_root)

        indent = '  ' * (rel_root.count(os.sep) + 1) if rel_root != '.' else ''
        for f in included:
            lines.append(f"{indent}{f}")

    return '\n'.join(lines)


def generate_outsource(goals, files, output_file='outsource.md', base_path='.'):
    """Generate outsource.md with goal statements, file contents, and project structure."""
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write('# Outsource Specification\n\n')
        
        out.write('## Goal Statement\n\n')
        for i, goal in enumerate(goals, 1):
            out.write(f"{i}. {goal}\n")
        out.write('\n')
        
        out.write('## Relevant File\n\n')
        for file_path in files:
            out.write(f'### File: {file_path}\n\n')
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                out.write(content)
            except Exception as e:
                out.write(f'[Error reading file: {e}]\n')
            out.write('\n')
        
        out.write('## Project Structure\n\n')
        tree = generate_tree(base_path, files)
        out.write('```\n')
        out.write(tree)
        out.write('\n```\n')
    
    print(f"Generated {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Generate outsource.md from goal statements and file references')
    parser.add_argument('-g', '--goal', action='append', required=True, help='Goal statement (can be repeated)')
    parser.add_argument('-f', '--file', action='append', required=True, help='File path to include (can be repeated)')
    parser.add_argument('-o', '--output', default='outsource.md', help='Output file path (default: outsource.md)')
    parser.add_argument('-p', '--path', default='.', help='Base path for project structure (default: current directory)')
    args = parser.parse_args()
    
    generate_outsource(args.goal, args.file, args.output, args.path)


if __name__ == '__main__':
    main()
