# Contributing to DDD Clone

Thank you for your interest in contributing to DDD Clone! This document provides guidelines for contributing to the project.

## Development Setup

1. Fork and clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install the package in development mode:
   ```bash
   pip install -e .
   ```

## Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) style guidelines
- Use **snake_case** for variable and function names
- Use **CamelCase** for class names
- Write docstrings for all public functions and classes
- **Do not use Chinese** in comments or print information

## Testing

- Write unit tests for all new functionality
- Ensure existing tests pass:
  ```bash
  pytest
  ```
- Run tests with coverage:
  ```bash
  pytest --cov=ddd_clone
  ```

## Pull Request Process

1. Create a feature branch from `master`
2. Make your changes with tests
3. Ensure all tests pass
4. Update documentation if needed
5. Submit a pull request with a clear description

## Reporting Issues

When reporting issues, please include:

- DDD Clone version
- Python version
- GDB version
- Steps to reproduce the issue
- Expected vs actual behavior
- Screenshots if applicable

## Code Review Guidelines

- All pull requests require review
- Reviewers should check for:
  - Code quality and style
  - Test coverage
  - Documentation updates
  - Backward compatibility
- Be respectful and constructive in reviews

## License

By contributing to this project, you agree that your contributions will be licensed under the GNU General Public License v3.0, the same license as the project.