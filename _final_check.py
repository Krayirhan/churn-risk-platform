"""Final comprehensive check: flake8 + pytest"""
import subprocess

print("=" * 70)
print("FLAKE8 CHECK (excluding whitespace W291,W293,W391)")
print("=" * 70)
r1 = subprocess.run(
    ['python', '-m', 'flake8', 'src/', 'app.py', 'main.py',
     '--max-line-length=120',
     '--extend-ignore=E501,W503,E203,W291,W293,W391',
     '--statistics', '--count'],
    capture_output=True, text=True, cwd='D:\\churn-risk-platform'
)
if r1.stdout.strip():
    print(r1.stdout)
else:
    print("✓ 0 errors")
print(f"Exit code: {r1.returncode}\n")

print("=" * 70)
print("PYTEST CHECK")
print("=" * 70)
r2 = subprocess.run(
    ['python', '-m', 'pytest', 'tests/', '--tb=short', '-q'],
    capture_output=True, text=True, cwd='D:\\churn-risk-platform'
)
lines = r2.stdout.strip().split('\n')
for line in lines[-3:]:
    print(line)
print(f"Exit code: {r2.returncode}\n")

if r1.returncode == 0 and r2.returncode == 0:
    print("✅ ALL CHECKS PASSED - Ready to push!")
else:
    print("❌ Some checks failed - needs fixes")
