import subprocess

# Run flake8
r1 = subprocess.run(
    ['python', '-m', 'flake8', 'src/', 'app.py', 'main.py',
     '--max-line-length=120', '--extend-ignore=E501,W503,E203',
     '--statistics', '--count'],
    capture_output=True, text=True, cwd='D:\\churn-risk-platform'
)
print("=== FLAKE8 ===")
print(r1.stdout.strip() if r1.stdout.strip() else "0 errors")
print(f"Exit: {r1.returncode}")

# Run tests
r2 = subprocess.run(
    ['python', '-m', 'pytest', 'tests/', '--tb=short', '-q'],
    capture_output=True, text=True, cwd='D:\\churn-risk-platform'
)
print("\n=== PYTEST ===")
lines = r2.stdout.strip().split('\n')
for line in lines[-5:]:
    print(line)
print(f"Exit: {r2.returncode}")
