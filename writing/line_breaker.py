#! /usr/bin/env python3

import re
import sys

def break_phrases(text):
    # Clean up previous runs
    text = re.sub(r'^(.{0,72})◀', r'\1', text, flags=re.MULTILINE)

    # Break on sentence boundaries (hard limits)
    text = re.sub(r'(.{20,}?)([.?!][”"]?|[:;]) ', r'\1\2\n', text)

    # Break on conjunctions
    text = re.sub(r'(.{20,}?) (or|and|but|such as|for example,?|e(\. ?)?g\.?|i(\. ?)?e\.?) ', r'\1\n\2 ', text)

    # Break on clause boundaries (soft limits)
    text = re.sub(r'(.{20,}?)(,[”"]?) ', r'\1\2\n', text)

    return text

if len(sys.argv) != 2:
    print("Usage: python script.py input_file.txt")
    sys.exit(1)

input_file = sys.argv[1]

with open(input_file, 'r') as file:
    text = file.read()

processed_text = break_phrases(text)

with open(input_file, 'w') as file:
    file.write(processed_text)

print("Phrases broken and saved to the input file.")
