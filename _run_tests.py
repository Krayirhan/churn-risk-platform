import subprocess
r = subprocess.run(
    ['python', '-m', 'pytest', 'tests/', '--tb=short', '-q'],
    capture_output=True, text=True, cwd='D:\\churn-risk-platform'
)
lines = r.stdout.strip().split('\n')
for line in lines[-10:]:
    print(line)
print('EXIT:', r.returncode)
