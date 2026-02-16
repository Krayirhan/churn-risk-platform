from setuptools import find_packages, setup

setup(
    name="churn-risk-platform",
    version="0.1.0",
    author="DS Team",
    description="Telco Customer Churn Risk Platform",
    packages=find_packages(),
    install_requires=[
        "pandas",
        "numpy",
        "scikit-learn",
        "xgboost",
        "pyyaml",
        "fastapi",
        "uvicorn",
        "plotly",
        "scipy",
        "statsmodels",
        "seaborn",
        "matplotlib",
    ],
)
