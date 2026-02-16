"""Debug and fix encoding in predict_pipeline.py"""
import pathlib

f = pathlib.Path('D:/churn-risk-platform/src/pipeline/predict_pipeline.py')
raw = f.read_bytes()

# Find the problematic area around "classify_risk" return statements
idx = raw.find(b'return "D')
if idx >= 0:
    snippet = raw[idx:idx+30]
    print(f"Bytes around 'return D...': {snippet}")
    print(f"Hex: {snippet.hex()}")

    # Check if it's double-encoded
    # Correct UTF-8 for "Düşük": 44 c3 bc c5 9f c3 bc 6b
    # Double-encoded: 44 c3 83 c2 bc c3 85 c5 b8 c3 83 c2 bc 6b
    if b'\xc3\x83' in snippet or b'\xc2\xbc' in snippet:
        print("TRIPLE-ENCODED detected! Fixing...")
        txt = raw.decode('utf-8')
        # Decode one level of encoding
        fixed = txt.encode('latin-1').decode('utf-8')
        # Check if still has issues
        if 'Ã' in fixed or 'Å' in fixed:
            print("Still mojibake after first pass, trying second pass...")
            fixed = fixed.encode('latin-1').decode('utf-8')
        f.write_bytes(fixed.encode('utf-8'))
        print("Fixed!")
    elif b'\xc3\xbc' in snippet:
        print("Correct UTF-8 encoding detected")
    else:
        print("Unknown encoding pattern")

# Also check Yüksek
idx2 = raw.find(b'return "Y')
if idx2 >= 0:
    snippet2 = raw[idx2:idx2+30]
    print(f"\nBytes around 'return Y...': {snippet2}")
    print(f"Hex: {snippet2.hex()}")
