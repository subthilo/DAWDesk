import sys, re

def fuzzy_patch(file_path, diff_content):
    with open(file_path, 'r') as f:
        original_lines = f.read().splitlines()
        
    chunks = re.split(r'\[diff_block_start\]', diff_content)
    if len(chunks) < 2: return
    
    current_lines = list(original_lines)
    
    for chunk in chunks[1:]:
        chunk = chunk.split('[diff_block_end]')[0].strip()
        lines = chunk.splitlines()
        
        # Parse hunks
        hunk = []
        for line in lines:
            if line.startswith('@@'): continue
            hunk.append(line)
            
        # We find the sequence of unchanged and - lines in current_lines, and replace with unchanged and + lines
        search_seq = []
        replace_seq = []
        for line in hunk:
            if line.startswith('-'):
                search_seq.append(line[1:])
            elif line.startswith('+'):
                replace_seq.append(line[1:])
            else:
                search_seq.append(line[1:])
                replace_seq.append(line[1:])
                
        # Find search_seq in current_lines
        match_idx = -1
        for i in range(len(current_lines) - len(search_seq) + 1):
            match = True
            for j in range(len(search_seq)):
                if current_lines[i+j].strip() != search_seq[j].strip():
                    match = False
                    break
            if match:
                match_idx = i
                break
                
        if match_idx >= 0:
            current_lines = current_lines[:match_idx] + replace_seq + current_lines[match_idx + len(search_seq):]
            print(f"Patched a hunk in {file_path}")
        else:
            print(f"Failed to find hunk in {file_path}")
            
    with open(file_path, 'w') as f:
        f.write('\n'.join(current_lines) + '\n')

with open('diffs.txt', 'r') as f:
    text = f.read()

parts = text.split("The following changes were made by the USER to: ")
for part in parts[1:]:
    file_path = part.split('. If relevant')[0].strip()
    print("Patching", file_path)
    fuzzy_patch(file_path, part)
