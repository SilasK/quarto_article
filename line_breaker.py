#!/usr/bin/env python3

import re
import sys
import os


def format_line(line):
    # Break on sentence boundaries (hard limits) and remove trailing spaces and tabs
    # line = re.sub(r'(.{20,}?)([.?!][”"]?|[:;]) +', r"\1\2\n", line)

    # Break on conjunctions after 20 characters
    line = re.sub(
        r"(.{20,}?) (but|such as|for example,?|e(\. ?)?g\.?|i(\. ?)?e\.?) ",
        r"\1\n\2 ",
        line,
    )

    # Break on commas after 40 characters if the second part is 20 chars or longer
    line = re.sub(r'(.{40,}?)(,[”"]?)\s+(?=\S{20})', r"\1\2\n", line)

    # Break on conjunctions after 40 characters if the second part is 20 chars or longer
    line = re.sub(r"(.{40,}?)\s+(and|or?)\s+(?=\S{20})", r"\1\n\2 ", line)

    return line


def break_phrases(text, exclude_comments=False):
    # Split the text into lines
    lines = text.split("\n")

    comment_pattern = r"^(?:[#%,]| {2,})"  # comments or lines starting with two spaces
    code_block_pattern = r"^```"

    # Process each line, excluding comment lines
    processed_lines = []
    after_hedader = 0
    # do not process yaml header
    print("found yaml header, do not process it")
    if lines[0].strip() == "---":
        processed_lines.append(lines[0])
        after_hedader = 1
        for l in lines[after_hedader:]:
            processed_lines.append(l)
            after_hedader += 1
            if l.strip() == "---":
                break

    if after_hedader >= len(lines):
        raise Exception("Did not found closing '---' for yaml header")

    in_code_block = False

    for line in lines[after_hedader:]:
        if re.match(code_block_pattern, line):
            # Toggle code block state
            in_code_block = not in_code_block
        if re.match(comment_pattern, line) and not in_code_block:
            # Comment line, exclude if requested
            if exclude_comments:
                processed_lines.append(line)
            else:
                processed_lines.append(format_line(line))
        else:
            if in_code_block:
                # Inside a code block, don't format
                processed_lines.append(line)
            else:
                processed_lines.append(format_line(line))

    return "\n".join(processed_lines)


def process_file(input_file):
    try:
        print(f"Processing: {input_file}")
        with open(input_file, "r") as file:
            text = file.read()

        processed_text = break_phrases(text)

        with open(input_file, "w") as file:
            file.write(processed_text)

    except Exception as e:
        print(f"💔 Error processing: {input_file}")
        print(e)


if len(sys.argv) < 2:
    print("Usage: python line_breaker.py input_file.md or directory")
    sys.exit(1)

for arg in sys.argv[1:]:
    if os.path.isfile(arg):
        process_file(arg)
    elif os.path.isdir(arg):
        for root, dirs, files in os.walk(arg):
            for file in files:
                if file.endswith(
                    (".md", ".qmd", ".tex", ".txt")
                ):  # Process specified file extensions
                    file_path = os.path.join(root, file)
                    process_file(file_path)

print("🌟 Processing completed.")
