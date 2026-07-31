# Outsource Specification

## Goal Statement

1. Add a button to UI In the series page in between Update and PUSH toKindle button that move the series from current location to ライトノベル library when pressed if it itself is not ライトノベル library or 漫画 library or 小説家になろう library. It check if folder already exists in ライトノベル library if so it move all the file in it, otherwise it move the whole folder

## Relevant File

### File: generate_outsource.py

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

### File: docker-compose.yml

version: '3.8'
services:
  komga:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: komga_test
    image: komga-kindle:latest
    ports:
      - "25601:25600"
    volumes:
      - ./config:/config
      - ./libraries:/libraries
      - ./cache:/cache
    environment:
      - KOMGA_CONFIGDIR=/config
      - SPRING_PROFILES_ACTIVE=docker
      - AUTOMANGA_URL="http://192.168.29.100:8758"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:25600/actuator/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

### File: komga_custom/trigger_update.py

import os
import sys
import json
import requests
from urllib.parse import urljoin

def trigger_update(series_name, library_id):
    """
    Trigger a manual update for a series via the Automaga API
    
    Args:
        series_name (str): Name of the series to update
        library_id (str): ID of the library to determine media type
    """
    # Get AUTOMANGA_URL from environment variable
    AUTOMANGA_URL = os.environ.get('AUTOMANGA_URL')
    if not AUTOMANGA_URL:
        print("Error: AUTOMANGA_URL environment variable not found")
        return False

    # Determine media type based on library ID
    if library_id == "0FK57Y46H30NY":
        media_type = "MANGA"
    elif library_id == "0FK584ET13AGD":
        media_type = "NOVEL"
    else:
        print(f"Warning: Unknown library ID {library_id}")
        return False

    # Prepare the API endpoint
    api_endpoint = urljoin(AUTOMANGA_URL, "/api/trigger/manual-update")

    # Prepare the payload
    payload = {
        "series_name": series_name,
        "mode": "nyaa+dlraw",
        "media_type": media_type,
        "add_new_series": "None",
        "options": {
            "dry_run": False
        }
    }

    try:
        # Make the API request
        response = requests.post(
            api_endpoint,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        # Check if request was successful
        if response.status_code == 200:
            print(f"Successfully triggered update for series '{series_name}' in library '{library_id}'")
            return True
        else:
            print(f"Failed to trigger update. Status code: {response.status_code}, Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python trigger_update.py <series_name> <library_id>")
        sys.exit(1)
    
    series_name = sys.argv[1]
    library_id = sys.argv[2]
    
    success = trigger_update(series_name, library_id)
    sys.exit(0 if success else 1)
## Project Structure

```
.
docker-compose.yml
generate_outsource.py
komga_custom
  trigger_update.py
```
