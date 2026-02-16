import subprocess
r = subprocess.run(
    ['python', '-m', 'pytest',
     'tests/unit/test_predict_pipeline.py::TestClassifyRisk',
     '-v', '--tb=short'],
    capture_output=True, text=True, cwd='D:\\churn-risk-platform'
)
print(r.stdout.strip())
print(f"Exit: {r.returncode}")
