# Package Distribution Guide

This guide explains how to build and distribute the Churn Risk Platform as a Python package.

## Table of Contents

1. [Building the Package](#building-the-package)
2. [Installing Locally](#installing-locally)
3. [Publishing to PyPI](#publishing-to-pypi)
4. [Creating Releases](#creating-releases)
5. [Version Management](#version-management)

---

## Building the Package

### Prerequisites

Install build tools:

```bash
pip install --upgrade build twine
```

### Build Source and Wheel Distributions

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build package
python -m build
```

This creates:
- `dist/churn_risk_platform-0.1.0.tar.gz` (source distribution)
- `dist/churn_risk_platform-0.1.0-py3-none-any.whl` (wheel distribution)

### Verify Package Contents

```bash
# List wheel contents
unzip -l dist/churn_risk_platform-0.1.0-py3-none-any.whl

# Extract and inspect
tar -xzf dist/churn_risk_platform-0.1.0.tar.gz
cd churn_risk_platform-0.1.0
```

---

## Installing Locally

### From Source Directory

```bash
# Editable install (for development)
pip install -e .

# With optional dependencies
pip install -e ".[dev]"
pip install -e ".[notebook]"
pip install -e ".[dev,notebook]"
```

### From Built Package

```bash
# Install wheel
pip install dist/churn_risk_platform-0.1.0-py3-none-any.whl

# Install from source tarball
pip install dist/churn_risk_platform-0.1.0.tar.gz
```

### Verify Installation

```bash
# Check installed package
pip show churn-risk-platform

# Test CLI commands (configured in pyproject.toml)
churn-train --help
churn-serve --help

# Import in Python
python -c "from src.pipeline.train_pipeline import TrainingPipeline; print('Import successful')"
```

---

## Publishing to PyPI

### Test PyPI (Recommended First)

1. **Register on Test PyPI**: https://test.pypi.org/account/register/

2. **Configure credentials** (`~/.pypirc`):
   ```ini
   [testpypi]
   username = __token__
   password = pypi-YOUR_TEST_PYPI_TOKEN
   ```

3. **Upload to Test PyPI**:
   ```bash
   twine upload --repository testpypi dist/*
   ```

4. **Test installation**:
   ```bash
   pip install --index-url https://test.pypi.org/simple/ churn-risk-platform
   ```

### Production PyPI

1. **Register on PyPI**: https://pypi.org/account/register/

2. **Configure credentials** (`~/.pypirc`):
   ```ini
   [pypi]
   username = __token__
   password = pypi-YOUR_PYPI_TOKEN
   ```

3. **Upload to PyPI**:
   ```bash
   # Check package first
   twine check dist/*
   
   # Upload
   twine upload dist/*
   ```

4. **Verify on PyPI**: https://pypi.org/project/churn-risk-platform/

### Install from PyPI

```bash
pip install churn-risk-platform

# With extras
pip install churn-risk-platform[dev]
```

---

## Creating Releases

### GitHub Release Process

1. **Update version** in `pyproject.toml`:
   ```toml
   version = "0.2.0"
   ```

2. **Update CHANGELOG.md**:
   ```markdown
   ## [0.2.0] - 2026-03-01
   
   ### Added
   - New feature X
   - New feature Y
   
   ### Fixed
   - Bug Z
   ```

3. **Commit changes**:
   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "chore: Bump version to 0.2.0"
   git push
   ```

4. **Create Git tag**:
   ```bash
   git tag -a v0.2.0 -m "Release v0.2.0"
   git push origin v0.2.0
   ```

5. **Create GitHub Release**:
   - Go to https://github.com/Krayirhan/churn-risk-platform/releases
   - Click "Draft a new release"
   - Choose tag: `v0.2.0`
   - Release title: `v0.2.0 - Feature Name`
   - Description: Copy from CHANGELOG.md
   - Attach assets: `dist/churn_risk_platform-0.2.0.tar.gz` and `.whl`
   - Publish release

### Automated Release with GitHub Actions

Create `.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install build tools
        run: pip install build twine
      
      - name: Build package
        run: python -m build
      
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
        run: twine upload dist/*
      
      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/*
          body_path: CHANGELOG.md
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## Version Management

### Semantic Versioning

Follow [SemVer](https://semver.org/):
- **MAJOR** (1.0.0): Breaking changes
- **MINOR** (0.1.0): New features, backward compatible
- **PATCH** (0.0.1): Bug fixes

### Version Update Checklist

- [ ] Update `version` in `pyproject.toml`
- [ ] Update CHANGELOG.md with new version section
- [ ] Update README.md if needed (badges, features)
- [ ] Update API documentation if endpoints changed
- [ ] Run full test suite: `pytest`
- [ ] Build and verify package: `python -m build && twine check dist/*`
- [ ] Commit changes: `git commit -m "chore: Bump version to X.Y.Z"`
- [ ] Create tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
- [ ] Push: `git push && git push --tags`

### Version Automation (bump2version)

Install:
```bash
pip install bump2version
```

Create `.bumpversion.cfg`:
```ini
[bumpversion]
current_version = 0.1.0
commit = True
tag = True
tag_name = v{new_version}

[bumpversion:file:pyproject.toml]
search = version = "{current_version}"
replace = version = "{new_version}"

[bumpversion:file:src/__init__.py]
search = __version__ = "{current_version}"
replace = __version__ = "{new_version}"
```

Usage:
```bash
# Increment patch (0.1.0 → 0.1.1)
bump2version patch

# Increment minor (0.1.0 → 0.2.0)
bump2version minor

# Increment major (0.1.0 → 1.0.0)
bump2version major
```

---

## Package Quality Checks

### Pre-publish Checklist

- [ ] All tests pass: `pytest`
- [ ] Linting passes: `make lint`
- [ ] Code formatted: `make format`
- [ ] Documentation up to date
- [ ] CHANGELOG.md updated
- [ ] Version number correct
- [ ] License file included
- [ ] README.md comprehensive
- [ ] Package builds successfully: `python -m build`
- [ ] Twine check passes: `twine check dist/*`
- [ ] Local install works: `pip install dist/*.whl`

### Package Metadata Validation

```bash
# Check package description renders correctly
python setup.py check --restructuredtext --strict

# Validate package metadata
twine check dist/*

# Test package installation
pip install dist/*.whl
python -c "import src; print('Success')"
pip uninstall -y churn-risk-platform
```

---

## Distribution Best Practices

### Security

- Use API tokens instead of passwords for PyPI
- Store tokens in environment variables or CI secrets
- Never commit tokens to git
- Rotate tokens periodically
- Use trusted publishing (GitHub Actions → PyPI)

### Dependencies

- Pin versions in `requirements.txt` for reproducibility
- Use version ranges in `pyproject.toml` for flexibility
- Test with minimum and maximum dependency versions
- Document known incompatibilities

### Testing

- Test package installation on clean environments
- Test on multiple Python versions (3.10, 3.11)
- Test on multiple OS (Windows, Linux, macOS)
- Include example usage in README

### Documentation

- Include comprehensive README
- Provide quick start guide
- Document all CLI commands
- Include API reference
- Add troubleshooting section
- Keep CHANGELOG up to date

---

## Troubleshooting

### Issue: "Package not found after install"

**Solution**: Ensure `src` directory structure:
```
src/
├── __init__.py  # Must exist!
├── components/
├── pipeline/
└── utils/
```

### Issue: "Metadata validation failed"

**Solution**: Run `twine check dist/*` and fix reported issues in `pyproject.toml`

### Issue: "Dependencies not installed"

**Solution**: Verify `dependencies` list in `pyproject.toml` and test with:
```bash
pip install -e ".[dev]"
```

### Issue: "CLI commands not available"

**Solution**: Check `[project.scripts]` in `pyproject.toml` and reinstall package

---

## Resources

- **Python Packaging Guide**: https://packaging.python.org/
- **PyPI Help**: https://pypi.org/help/
- **PEP 621 (Project Metadata)**: https://peps.python.org/pep-0621/
- **Setuptools Documentation**: https://setuptools.pypa.io/
- **Build Documentation**: https://build.pypa.io/

---

## Support

For packaging issues:
- GitHub Issues: https://github.com/Krayirhan/churn-risk-platform/issues
- Python Packaging Discourse: https://discuss.python.org/c/packaging/
