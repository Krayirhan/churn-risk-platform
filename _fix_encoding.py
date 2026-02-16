"""Fix double-encoded UTF-8 (mojibake) in source files."""
import pathlib
import re

def fix_mojibake(text):
    """Fix text that was double-encoded (UTF-8 read as Latin-1, then written as UTF-8)."""
    try:
        # Encode as Latin-1 to get original UTF-8 bytes, then decode as UTF-8
        fixed = text.encode('latin-1').decode('utf-8')
        return fixed
    except (UnicodeDecodeError, UnicodeEncodeError):
        # If full file conversion fails, try line by line
        lines = text.split('\n')
        fixed_lines = []
        for line in lines:
            try:
                fixed_lines.append(line.encode('latin-1').decode('utf-8'))
            except (UnicodeDecodeError, UnicodeEncodeError):
                fixed_lines.append(line)
        return '\n'.join(fixed_lines)


files = list(pathlib.Path('src').rglob('*.py')) + [pathlib.Path('app.py'), pathlib.Path('main.py')]
fixed_count = 0

for f in files:
    raw = f.read_bytes()
    txt = raw.decode('utf-8')

    # Check if there are mojibake patterns (common Turkish double-encoded chars)
    # Ã¼ = ü, Ã¶ = ö, Ã§ = ç, ÅŸ = ş, Ä± = ı, Ä° = İ, ÄŸ = ğ
    if any(pat in txt for pat in ['Ã¼', 'Ã¶', 'Ã§', 'ÅŸ', 'Ä±', 'ÄŸ', 'Ã¼k', 'Ã–']):
        fixed = fix_mojibake(txt)
        f.write_bytes(fixed.encode('utf-8'))
        fixed_count += 1
        print(f"  Fixed: {f}")

print(f"\nFixed {fixed_count} files with mojibake")
