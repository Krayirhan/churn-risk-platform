import subprocess
r = subprocess.run(
    ['python', '-m', 'pytest',
     'tests/unit/test_predict_pipeline.py::TestClassifyRisk',
     '-v', '--tb=long'],
    capture_output=True, text=True, cwd='D:\\churn-risk-platform'
)
print(r.stdout[-2000:])
if r.stderr:
    print('STDERR:', r.stderr[-500:])
