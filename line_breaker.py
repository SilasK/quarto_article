#!/usr/bin/env python3
"""
Backward compatibility wrapper for line_breaker.py
Redirects to the new linebreaker package structure.
"""


import re


def mask_citations_and_numbers(text):
    """Replace citations and decimal numbers with placeholders.

    Returns:
        tuple: (masked_text, citation_map, number_map)
    """
    # Mask citations
    citation_pattern = r"\[@[^\]]+\]"
    citations = re.findall(citation_pattern, text)
    citation_map = {}
    for i, citation in enumerate(citations):
        placeholder = f"__CITATION_{i}__"
        citation_map[placeholder] = citation
        text = text.replace(citation, placeholder, 1)

    # Mask decimal numbers
    number_pattern = r"\d+\.\d+"
    numbers = re.findall(number_pattern, text)
    number_map = {}
    for i, number in enumerate(numbers):
        placeholder = f"__N_{i}__"
        number_map[placeholder] = number
        text = text.replace(number, placeholder, 1)

    return text, citation_map, number_map


def handle_parentheses_and_footnotes(text, short_threshold=40):
    """Handle parentheses and footnotes intelligently:

    - Short parentheses/footnotes (<= threshold): protect from breaking inside
    - Long parentheses/footnotes (> threshold): break before them, then allow breaks inside

    Returns: (processed_text, restoration_map)
    """
    # Patterns for parentheses and footnotes
    paren_pattern = r"\([^)]+\)"
    footnote_pattern = r"\[\^[^\]]+\]"

    combined_map = {}

    # Find all parentheses
    for match in re.finditer(paren_pattern, text):
        content = match.group()
        if len(content) <= short_threshold:
            # Short: mask it to prevent breaks inside
            placeholder = f"__PAREN_{len(combined_map)}__"
            combined_map[placeholder] = content
            text = text.replace(content, placeholder, 1)
        else:
            # Long: add line break before if preceded by text
            # This ensures long parentheses get their own line
            before_pos = match.start()
            if before_pos > 20 and text[before_pos - 1] == " ":
                # Insert newline before the opening paren
                text = text[:before_pos] + "\n" + text[before_pos:]

    # Find all footnotes - treat similarly
    for match in re.finditer(footnote_pattern, text):
        content = match.group()
        if len(content) <= short_threshold:
            placeholder = f"__FOOTNOTE_{len(combined_map)}__"
            combined_map[placeholder] = content
            text = text.replace(content, placeholder, 1)
        else:
            # Long footnotes also get their own line
            before_pos = match.start()
            if before_pos > 20 and text[before_pos - 1] == " ":
                text = text[:before_pos] + "\n" + text[before_pos:]

    return text, combined_map


def restore_protected_content(text, combined_map):
    """Restore masked parentheses and footnotes."""
    for placeholder, content in combined_map.items():
        text = text.replace(placeholder, content)
    return text


def restore_masked_content(text, citation_map, number_map):
    """Restore citations and numbers from placeholders."""
    for placeholder, citation in citation_map.items():
        text = text.replace(placeholder, citation)
    for placeholder, number in number_map.items():
        text = text.replace(placeholder, number)
    return text


def format_segment(segment, citation_map, number_map):
    """Apply soft breaks (conjunctions, commas, and/or) to a segment."""
    # Mask content before applying soft breaks
    segment, cit_map, num_map = mask_citations_and_numbers(segment)
    segment, paren_map = handle_parentheses_and_footnotes(segment)

    # Break on conjunctions after 20 characters (but NOT on "i.e." or "e.g." - those are abbreviations)
    # Only break on "but", "such as", "for example"
    segment = re.sub(
        r"(.{20,}?) (but|such as|for example) (?=.{20})",
        r"\1\n\2 ",
        segment,
    )

    # Break on commas after 40 characters if the second part is 20 chars or longer
    # Allow breaking before i.e./e.g. but not in other cases with abbreviations
    segment = re.sub(
        r'(.{40,}?)(,[""]?) +(?=(?:i\.e\.|e\.g\.)|(?!etc\.|vs\.))(?=.{20})',
        r"\1\2\n",
        segment,
    )

    # Break on and/or after 40 characters if the second part is 20 chars or longer
    segment = re.sub(r"(.{40,}?)\s+(and|or)\s+(?=.{20})", r"\1\n\2 ", segment)

    # Restore content
    segment = restore_protected_content(segment, paren_map)
    segment = restore_masked_content(segment, cit_map, num_map)

    # As a last resort, split after closing parentheses in very long segments
    # This happens AFTER comma breaks, so enumerations like "(1) text, (2) text"
    # break on commas first, then parentheses if needed
    if len(segment.strip()) > 100:
        parts = split_on_parentheses_end(segment, min_length=100)
        if len(parts) > 1:
            segment = "\n".join(parts)

    return segment


def split_on_sentence_punctuation(text):
    """Split text on sentence-ending punctuation (. ? !).

    Avoids breaking on common abbreviations by checking:
    - At least 20 chars before punctuation
    - Not an abbreviation (vs., Dr., etc., e.g., i.e., Prof., M., Mrs., Mr., Ph.D., etc.)
    - At least 20 chars after punctuation

    Also masks parentheses content to avoid counting characters inside them.
    """
    # Mask parentheses first to avoid counting their content
    masked_text, paren_map = handle_parentheses_and_footnotes(text)

    # Common abbreviations that should NOT trigger sentence breaks
    abbreviations = [
        "vs",  # versus
        "dr",  # Doctor
        "med",  # medical
        "prof",  # Professor
        "mr",  # Mister
        "mrs",  # Missus
        "ms",  # Miss/Ms
        "jr",  # Junior
        "sr",  # Senior
        "etc",  # et cetera
        "vol",  # volume
        "no",  # number
        "pp",  # pages
        "fig",  # figure
        "ph\\.d",  # PhD (escaped period)
        "m\\.d",  # Medical Doctor (escaped period)
        "e\\.g",  # for example (escaped period)
        "i\\.e",  # that is (escaped period)
        "et\\sal",  # et al (with space)
        "et\\s_al\\._",  # et _al._ (italicized markdown)
    ]

    # Build negative lookbehind pattern from abbreviations list
    # (?<!pattern1)(?<!pattern2)... means "not preceded by pattern1 or pattern2..."
    lookbehind = "".join(f"(?<!{abbr})" for abbr in abbreviations)

    # Pattern: split on . ? ! but NOT on common abbreviations
    # At least 20 chars before, punctuation, space, at least 20 chars after
    pattern = rf'(.{{20,}}?{lookbehind}[.?!][""]?) +(?=.{{20,}})'
    segments = re.split(pattern, masked_text, flags=re.IGNORECASE)

    # Reconstruct sentences
    sentences = []
    i = 0
    while i < len(segments):
        if i + 1 < len(segments) and segments[i + 1]:
            # Combine text with its punctuation
            sentences.append(segments[i] + segments[i + 1])
            i += 2
        elif segments[i].strip():
            sentences.append(segments[i])
            i += 1
        else:
            i += 1

    # Restore parentheses in all sentences
    restored = [restore_protected_content(s, paren_map) for s in sentences]
    return restored if restored else [text]


def split_on_colons(text, min_length=80):
    """Split text on colons/semicolons if text is longer than min_length.

    Masks parentheses to avoid counting their content.
    Colons and semicolons stay on the first line.
    """
    if len(text.strip()) <= min_length:
        return [text]

    # Mask parentheses first
    masked_text, paren_map = handle_parentheses_and_footnotes(text)

    # Try to split on : or ; if both parts would be at least 20 chars
    # The punctuation stays on the first line
    segments = re.split(r"(.{20,}?[:;]) +(?=.{20,})", masked_text)

    if len(segments) <= 1:
        return [text]

    # Reconstruct parts
    parts = []
    for j in range(0, len(segments), 2):
        if j + 1 < len(segments):
            parts.append(segments[j] + segments[j + 1])
        elif segments[j].strip():
            parts.append(segments[j])

    # Restore parentheses
    restored = [restore_protected_content(p, paren_map) for p in parts]
    return restored


def split_on_em_dashes(text, min_length=80):
    """Split text on em dashes if text is longer than min_length.

    Masks parentheses to avoid counting their content.
    Em dash goes to the new line (before it).
    """
    if len(text.strip()) <= min_length:
        return [text]

    # Mask parentheses first
    masked_text, paren_map = handle_parentheses_and_footnotes(text)

    # Split BEFORE em dash (—) if both parts would be at least 20 chars
    # The pattern captures: (text before), then splits on space + em dash
    # Em dash will start the new line
    segments = re.split(r"(.{20,}?) +(?=— .{20,})", masked_text)

    # Filter out empty segments and reconstruct
    parts = [s for s in segments if s.strip()]

    if len(parts) <= 1:
        return [text]

    # Restore parentheses
    restored = [restore_protected_content(p, paren_map) for p in parts]
    return restored if restored else [text]


def split_on_parentheses_end(text, min_length=80):
    """Split very long sentences after closing parentheses if not broken before.

    This is a fallback for when a sentence is too long and hasn't been split yet.
    Excludes enumeration markers like (1), (2), etc.
    """
    if len(text.strip()) <= min_length:
        return [text]

    # Try to split after ) if both parts would be at least 20 chars
    # But NOT after enumeration markers like (1), (2), etc.
    # Use negative lookbehind to avoid splitting after single-digit or letter in parens
    segments = re.split(r"(.{20,}?(?<!\(\d)\)(?!\))) +(?=.{20,})", text)

    if len(segments) <= 1:
        return [text]

    # Reconstruct parts
    parts = []
    for j in range(0, len(segments), 2):
        if j + 1 < len(segments):
            parts.append(segments[j] + segments[j + 1])
        elif segments[j].strip():
            parts.append(segments[j])

    return parts if parts else [text]


def format_line(line):
    """Format a single line with intelligent line breaks."""
    # Step 1: Mask citations and numbers to avoid interference
    masked_line, citation_map, number_map = mask_citations_and_numbers(line)

    # Step 2: Break on sentence-ending punctuation (hard limits: . ? !)
    sentences = split_on_sentence_punctuation(masked_line)

    # Step 3: Further split long sentences on colons/semicolons
    final_sentences = []
    for sentence in sentences:
        parts = split_on_colons(sentence, min_length=80)
        final_sentences.extend(parts)

    # Step 3.5: Split on em dashes
    sentences_with_emdash = []
    for sentence in final_sentences:
        parts = split_on_em_dashes(sentence, min_length=80)
        sentences_with_emdash.extend(parts)
    final_sentences = sentences_with_emdash

    # Step 4: Restore citations and numbers
    restored_sentences = []
    for sentence in final_sentences:
        restored = restore_masked_content(sentence, citation_map, number_map)
        restored_sentences.append(restored)

    # Step 5: Apply soft breaks to each sentence if there are 3+ sentences
    # or if individual sentences are long enough
    processed_sentences = []
    for sentence in restored_sentences:
        # Apply soft breaks if there are multiple sentences or sentence is long
        if len(restored_sentences) >= 3 or len(sentence.strip()) > 60:
            sentence = format_segment(sentence, citation_map, number_map)
        processed_sentences.append(sentence)

    # Join with newlines, ensuring sentence boundaries create breaks
    result = []
    for i, sentence in enumerate(processed_sentences):
        if i < len(processed_sentences) - 1:
            # Add newline after sentence (except the last one)
            result.append(sentence.rstrip() + "\n")
        else:
            result.append(sentence)

    return "".join(result)


def break_text(text):
    """Process entire text, handling YAML headers, code blocks, and Quarto blocks."""
    # Split the text into lines
    lines = text.split("\n")

    special_line_pattern = (
        r"^(?:[#%,-]| {2,})"  # headers,comments or lines starting with two spaces
    )
    enumeration_pattern = r"^\d+\."  # enumeration lines (1., 2., etc.)
    code_block_pattern = r"^```"
    quarto_block_pattern = r"^:{3,4}"  # Quarto blocks with ::: or ::::

    # Process each line, excluding comment lines
    processed_lines = []
    after_yaml_header = 0

    # do not process yaml header
    if lines[0].strip() == "---":
        processed_lines.append(lines[0])
        after_yaml_header = 1
        for l in lines[after_yaml_header:]:
            processed_lines.append(l)
            after_yaml_header += 1
            if l.strip() == "---":
                break

    if after_yaml_header >= len(lines):
        raise Exception("Did not found closing '---' for yaml header")

    in_code_block = False
    in_quarto_block = False

    for line in lines[after_yaml_header:]:
        if re.match(code_block_pattern, line):
            # Toggle code block state
            in_code_block = not in_code_block

        if re.match(quarto_block_pattern, line):
            # Toggle Quarto block state
            in_quarto_block = not in_quarto_block

        if in_code_block or in_quarto_block:
            processed_lines.append(line)
            continue

        if re.match(special_line_pattern, line):
            processed_lines.append(line)
            continue

        if re.match(enumeration_pattern, line):
            processed_lines.append(line)
            continue

        processed_lines.append(format_line(line))

    if in_code_block:
        raise Exception("💔 Warning: Unclosed code block detected.")

    if in_quarto_block:
        raise Exception("💔 Warning: Unclosed Quarto block detected.")

    return "\n".join(processed_lines)


def process_file(input_file):
    """Process a file and write the formatted text back."""
    print(f"Processing: {input_file}")
    with open(input_file, "r") as file:
        text = file.read()

    processed_text = break_text(text)

    with open(input_file, "w") as file:
        file.write(processed_text)


import sys
from pathlib import Path


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m linebreaker.cli input_file.md or directory")
        sys.exit(1)

    for arg in sys.argv[1:]:
        path = Path(arg)

        if path.is_file():
            try:
                process_file(str(path))
            except Exception as e:
                print(f"💔 Error processing: {path}")
                print(e)
        elif path.is_dir():
            # Recursively find all matching files
            for file_path in path.rglob("*"):
                if file_path.suffix in {".md", ".qmd", ".tex", ".txt"}:
                    try:
                        process_file(str(file_path))
                    except Exception as e:
                        print(f"💔 Error processing: {file_path}")
                        print(e)
        else:
            print(f"❌ Not found: {path}")

    print("🌟 Processing completed.")


if __name__ == "__main__":
    main()
