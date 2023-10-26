#!/usr/bin/env python3

import re
import sys
import os

def break_phrases(text):
    # Clean up previous runs
    text = re.sub(r'^(.{0,72})◀', r'\1', text, flags=re.MULTILINE)

    # Break on sentence boundaries (hard limits)
    text = re.sub(r'(.{20,}?)([.?!][”"]?|[:;]) ', r'\1\2\n', text)

    # Break on conjunctions
    text = re.sub(r'(.{20,}?) (or|and|but|such as|for example,?|e(\. ?)?g\.?|i(\. ?)?e\.?) ', r'\1\n\2 ', text)

    # Break on clause boundaries (soft limits)
    text = re.sub(r'(.{20,}?)(,[”"]?) ', r'\1\2\n', text)

    # Remove emty spaces and tabs at the end of lines
    text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)

    return text

def process_file(input_file):
    try:
        print(f"Processing: {input_file}")
        with open(input_file, 'r') as file:
            text = file.read()

        processed_text = break_phrases(text)

        with open(input_file, 'w') as file:
            file.write(processed_text)

    except Exception as e:
        print(f"Error processing: {input_file}")
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
