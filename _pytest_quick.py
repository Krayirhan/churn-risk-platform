import subprocess
r = subprocess.run(
    ['python', '-m', 'pytest', 'tests/', '-q', '--tb=line'],
    capture_output=True, text=True, cwd='D:\\churn-risk-platform', timeout=120
)
lines = r.stdout.strip().split('\n')
for line in lines[-5:]:
    print(line)
print(f"\nExit: {r.returncode}")
