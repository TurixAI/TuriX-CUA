# Contributing to TuriX Computer Use Agent

Thank you for your interest in contributing to TuriX! This project is a computer automation agent that uses AI to interact with the desktop environment through accessibility APIs and computer vision.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Contributing Workflow](#contributing-workflow)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Issues and Bug Reports](#issues-and-bug-reports)

## Getting Started

### Prerequisites

- macOS 15 or Windows 11 recommended
- Python 3.12+
- Git
- Accessibility permissions enabled for your terminal/IDE

### Development Setup

1. **Fork the repository** on GitHub
2. **Clone your fork locally:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/TuriX-CUA.git
   cd TuriX-CUA
   ```

3. **Set up the upstream remote:**
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/TuriX-CUA.git
   ```

4. **Create a virtual environment:**
   ```bash
   conda activate turix_env python=3.12
   conda activate turix_env
   ```

5. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

6. **Enable accessibility permissions:**
   - Go to System Preferences → Security & Privacy → Privacy → Accessibility
   - Add your terminal application and Python interpreter

## Project Structure

```
src/
├── agent/                  # Core AI agent functionality
│   ├── service.py         # Main agent orchestration
│   ├── prompts.py         # System prompts and message handling
│   ├── output_schemas.py  # Pydantic schemas for structured output
│   ├── structured_llm.py  # LLM integration and response parsing
│   ├── views.py           # Data models and views
│   └── message_manager/   # Message history management
├── controller/            # Action execution and registry
│   ├── service.py         # Controller orchestration
│   ├── views.py           # Controller data models
│   └── registry/          # Action registry system
├── mac/                   # macOS-specific functionality
│   ├── actions.py         # Low-level macOS actions (click, type, scroll)
│   ├── element.py         # UI element representation
│   └── tree.py            # UI tree building and screenshot annotation
└── utils.py               # Utility functions
```

## Contributing Workflow

### 1. Fork and Clone

```bash
# Fork the repo on GitHub, then:
git clone https://github.com/YOUR_USERNAME/TuriX-CUA.git
cd TuriX-CUA
git remote add upstream https://github.com/ORIGINAL_OWNER/TuriX-CUA.git
```

### 2. Create a Feature Branch

```bash
# Update your main branch
git checkout main
git pull upstream main

# Create a new feature branch
git checkout -b feature/your-feature-name
# or for bug fixes:
git checkout -b fix/issue-description
```

### 3. Make Your Changes

- Write your code following the [style guidelines](#code-style-guidelines)
- Update documentation as needed
- Test your changes thoroughly on macOS or windows

### 4. Commit Your Changes

```bash
# Stage your changes
git add .

# Commit with a descriptive message
git commit -m "feat: add new action for handling dropdown menus

- Implement dropdown detection in element.py
- Add select_dropdown_option action in actions.py
- Update action registry with new dropdown action
- Add tests for dropdown functionality

Closes #123"
```

### 5. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Then create a pull request on GitHub
```

### 6. Keep Your Branch Updated

```bash
# Fetch latest changes from upstream
git fetch upstream

# Rebase your branch on the latest main
git rebase upstream/main

# Force push if needed (only for feature branches)
git push --force-with-lease origin feature/your-feature-name
```

## Code Style Guidelines

### Python Code Style

- Follow PEP 8 style guidelines
- Use type hints for all function parameters and return values
- Use descriptive variable and function names
- Keep functions focused and single-purpose
- Maximum line length: 88 characters (Black formatter standard)

### Imports

```python
# Standard library imports first
import asyncio
import logging
from typing import List, Optional

# Third-party imports
from pydantic import BaseModel
from langchain_core.messages import BaseMessage

# Local imports last
from src.mac.element import MacElementNode
from src.agent.views import ActionResult
```

### Documentation

- Add docstrings to all public functions and classes
- Use Google-style docstrings
- Include type information in docstrings
- Document complex algorithms and business logic

```python
async def scroll_to_element(element: MacElementNode, direction: str = "down") -> bool:
    """Scroll to make an element visible on screen.
    
    Args:
        element: The MacElementNode to scroll to
        direction: Direction to scroll ("up" or "down")
        
    Returns:
        True if scrolling was successful, False otherwise
        
    Raises:
        ValueError: If direction is not "up" or "down"
    """
```

### Error Handling

- Use specific exception types
- Provide meaningful error messages
- Log errors appropriately
- Handle edge cases gracefully

```python
try:
    result = await action_executor.execute(action)
except ActionExecutionError as e:
    logger.error(f"Failed to execute action {action.type}: {e}")
    return ActionResult(success=False, error=str(e))
```

## Testing

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=src

# Run specific test file
python -m pytest tests/test_actions.py

# Run tests with verbose output
python -m pytest -v
```

### Writing Tests

- Write unit tests for all new functions
- Use pytest fixtures for common test setup
- Mock external dependencies (UI elements, system calls)
- Test edge cases and error conditions

```python
import pytest
from unittest.mock import Mock, patch
from src.mac.actions import click_element

@pytest.fixture
def mock_element():
    element = Mock()
    element.position = (100, 200)
    element.size = (50, 30)
    return element

async def test_click_element_success(mock_element):
    """Test successful element clicking."""
    with patch('src.mac.actions._click_at_position') as mock_click:
        mock_click.return_value = True
        result = await click_element(mock_element)
        assert result is True
        mock_click.assert_called_once_with(125, 215)  # center of element
```

## Pull Request Process

### Before Submitting

1. **Test thoroughly:** Ensure your changes work on macOS or Windows
2. **Update documentation:** Include relevant documentation updates
3. **Check code style:** Run linting tools
4. **Rebase on main:** Ensure your branch is up to date

### Pull Request Template

When creating a pull request, include:

- **Description:** Clear description of what the PR does
- **Motivation:** Why this change is needed
- **Testing:** How you tested the changes
- **Screenshots:** For UI-related changes
- **Breaking changes:** Any breaking changes and migration notes

### Review Process

1. Automated checks must pass
2. At least one maintainer review required
3. All feedback must be addressed
4. Final approval from a maintainer

## Issues and Bug Reports

### Reporting Bugs

When reporting bugs, please include:

- macOS version or Windows version
- Python version
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs or error messages
- Screenshots if applicable

### Feature Requests

For feature requests:

- Describe the use case
- Explain why this would be valuable
- Provide examples of how it would work
- Consider implementation complexity

### Issue Labels

- `bug`: Something isn't working
- `enhancement`: New feature or request
- `documentation`: Improvements to documentation
- `good first issue`: Good for newcomers
- `help wanted`: Extra attention is needed

## Getting Help

- **Documentation:** Check the README and code comments
- **Issues:** Search existing issues for similar problems
- **Discussions:** Use GitHub Discussions for questions
- **Code Review:** Don't hesitate to ask for feedback

## Code of Conduct

This project follows a code of conduct. Please be respectful and constructive in all interactions.

---

Thank you for contributing to TuriX! Your contributions help make conputer automation more accessible and powerful for everyone.