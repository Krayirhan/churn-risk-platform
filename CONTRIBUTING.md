# Contributing to Churn Risk Platform

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards other contributors

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/Krayirhan/churn-risk-platform/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version)
   - Relevant logs or screenshots

### Suggesting Enhancements

1. Open an issue with the "enhancement" label
2. Describe the feature and its benefits
3. Provide examples of how it would work
4. Discuss implementation approach

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Run tests**: `pytest`
5. **Run linting**: `flake8 src/ app.py main.py`
6. **Format code**: `black src/ tests/ app.py main.py`
7. **Commit changes**: `git commit -m 'Add amazing feature'`
8. **Push to branch**: `git push origin feature/amazing-feature`
9. **Open Pull Request**

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/churn-risk-platform.git
cd churn-risk-platform

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest

# Run linting
make lint
```

## Code Style

- Follow PEP 8 style guide
- Use meaningful variable names
- Add docstrings to functions and classes
- Keep functions focused and small
- Maximum line length: 120 characters

### Example

```python
def calculate_churn_probability(customer_data: dict) -> float:
    """
    Calculate churn probability for a customer.
    
    Args:
        customer_data: Dictionary with customer features
        
    Returns:
        Probability of churn (0.0 to 1.0)
        
    Raises:
        ValueError: If required features are missing
    """
    # Implementation
    pass
```

## Testing Guidelines

- Write tests for new features
- Maintain test coverage above 80%
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)

```python
def test_model_prediction_returns_valid_probability():
    # Arrange
    model = load_model()
    customer = {"tenure": 12, ...}
    
    # Act
    result = model.predict(customer)
    
    # Assert
    assert 0.0 <= result <= 1.0
```

## Documentation

- Update README.md for user-facing changes
- Add docstrings for new functions/classes
- Update API.md for endpoint changes
- Update CHANGELOG.md with your changes

## Commit Messages

Follow conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Test additions or changes
- `chore`: Build process or auxiliary tool changes

Example:
```
feat(api): Add batch prediction endpoint

- Add /predict/batch endpoint for multiple customers
- Implement request batching up to 1000 records
- Add batch prediction tests

Closes #42
```

## Review Process

1. All PRs require at least one review
2. CI checks must pass (lint, test, build)
3. Code coverage should not decrease
4. Documentation must be updated
5. Changelog must be updated

## Questions?

Feel free to open an issue with the "question" label or reach out via GitHub Discussions.

Thank you for contributing! 🎉
