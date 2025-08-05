import re

def process_outsource(input_file, output_file):
    # Read the input file
    with open(input_file, 'r') as f:
        content = f.read()

    # Extract file paths and their descriptions
    file_refs = re.findall(r'### File: (.*?)\n(.*?)(?=###|\Z)', content, re.DOTALL)
    
    # Read each referenced file and insert its content
    for path, description in file_refs:
        try:
            with open(path, 'r') as f:
                file_content = f.read()
            
            # Insert the file content after its description
            insertion_point = content.find(description) + len(description)
            content = content[:insertion_point] + f"\n```python\n{file_content}\n```\n" + content[insertion_point:]
        except FileNotFoundError:
            print(f"Warning: File not found: {path}")
            continue
    
    # Write the output file
    with open(output_file, 'w') as f:
        f.write(content)

if __name__ == "__main__":
    process_outsource("outsource.md", "outsource_source_code.md")