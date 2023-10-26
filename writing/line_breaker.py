#!/usr/bin/env python3

import re
import sys
import os

import re

def break_phrases(text):
    # Split the text into lines
    lines = text.split('\n')
    
    comment_pattern = r'^[#%]'
    
    # Process each line, excluding comment lines
    processed_lines = []
    for line in lines:
        if not re.match(comment_pattern, line):
            
            # Break on sentence boundaries (hard limits) and remove trailing spaces and tabs
            line = re.sub(r'(.{20,}?)([.?!][”"]?|[:;]) +', r'\1\2\n', line)
            
            # Break on conjunctions and remove trailing spaces and tabs
            line = re.sub(r'(.{20,}?) (or|and|but|such as|for example,?|e(\. ?)?g\.?|i(\. ?)?e\.?) ', r'\1\n\2 ', line)
            
            # Break on clause boundaries (soft limits) and remove trailing spaces and tabs
            line = re.sub(r'(.{20,}?)(,[”"]?) +', r'\1\2\n', line)
        
        processed_lines.append(line)
    
    return '\n'.join(processed_lines)


def process_file(input_file):
    try:
        print(f"Processing: {input_file}")
        with open(input_file, 'r') as file:
            text = file.read()

        processed_text = break_phrases(text)

        with open(input_file, 'w') as file:
            file.write(processed_text)

    except Exception as e:
        print(f"💔 Error processing: {input_file}")
        print(e)

if len(sys.argv) < 2:
    print("Usage: python script.py input_file.txt or directory")
    sys.exit(1)

for arg in sys.argv[1:]:
    if os.path.isfile(arg):
        process_file(arg)
    elif os.path.isdir(arg):
        for root, dirs, files in os.walk(arg):
            for file in files:
                if file.endswith((".md", ".qmd", ".tex", ".txt")):  # Process specified file extensions
                    file_path = os.path.join(root, file)
                    process_file(file_path)

print("🌟 Processing completed.")
