"""Temporary script to fix remaining flake8 errors."""
import re
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))


def fix_f541_by_line(filepath, line_numbers):
    """Remove f-prefix from f-strings without placeholders at given 1-based line numbers."""
    txt = open(filepath, encoding='utf-8').read()
    lines = txt.split('\n')
    for ln in line_numbers:
        idx = ln - 1
        if idx < len(lines):
            line = lines[idx]
            # Replace print(f" or logging.info(f" with print(" or logging.info("
            line = re.sub(r'(print|logging\.info)\(f"', r'\1("', line, count=1)
            lines[idx] = line
    open(filepath, 'w', encoding='utf-8').write('\n'.join(lines))
    print(f"  Fixed F541 in {filepath} at lines {line_numbers}")


def fix_exception():
    """Fix all errors in src/exception.py."""
    filepath = 'src/exception.py'
    txt = open(filepath, encoding='utf-8').read()

    # Remove unused import: from src.logger import logging
    txt = txt.replace('from src.logger import logging\n', '')

    # Fix E231: missing whitespace after ':'
    txt = txt.replace('error_detail:sys', 'error_detail: sys')

    # Fix E302: need 2 blank lines before top-level def/class
    # After removing the import, we need: import sys\n\n\ndef error_message_detail
    txt = re.sub(
        r'(import sys\n)\n?(def error_message_detail)',
        r'\1\n\n\2',
        txt
    )
    # Before class CustomException
    txt = re.sub(
        r'(    return error_message\n)\n?(class CustomException)',
        r'\1\n\n\2',
        txt
    )

    open(filepath, 'w', encoding='utf-8').write(txt)
    print(f"  Fixed all errors in {filepath}")


# --- main.py ---
fix_f541_by_line('main.py', [49])

# --- model_evaluation.py ---
fix_f541_by_line('src/components/model_evaluation.py', [327, 337, 342])

# --- common.py ---
fix_f541_by_line('src/utils/common.py', [319])

# --- exception.py ---
fix_exception()

print("\nAll fixes applied!")
