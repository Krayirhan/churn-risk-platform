import subprocess
r = subprocess.run(
    ['python', '-m', 'flake8', 'src/', 'app.py', 'main.py',
     '--max-line-length=120',
     '--extend-ignore=E501,W503,E203,W291,W293,W391'],
    capture_output=True, text=True, cwd='D:\\churn-risk-platform'
)
print(r.stdout)
print(f"Exit: {r.returncode}")
