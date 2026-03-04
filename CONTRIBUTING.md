# Contributing to Solace Browser

> "Absorb what is useful, discard what is useless, add what is specifically your own." — Bruce Lee

Thank you for your interest in Solace Browser. This project uses the Functional Source License (FSL) — you can read, use, and learn from the code, but competing products are not permitted under the license terms.

## How to Contribute

### Reporting Bugs

1. Check [existing issues](https://github.com/phuctruong/solace-browser/issues) first
2. Use the bug report template
3. Include: OS, Python version, browser version, steps to reproduce
4. Attach screenshots or error logs if applicable

### Suggesting Features

1. Open a [Feature Request](https://github.com/phuctruong/solace-browser/issues/new) issue
2. Describe the use case, not just the solution
3. Community votes determine priority — approved features ship in the next release

### Submitting Recipes

Recipes are JSON automation scripts that replay browser workflows:

1. Fork the repo
2. Create your recipe in `recipes/`
3. Include a Prime Mermaid triplet in `primewiki/` if targeting a new platform
4. Submit a pull request with evidence (test output showing the recipe works)

### Code Contributions

We welcome pull requests for:
- Bug fixes
- Recipe improvements
- Documentation
- Test coverage
- Accessibility improvements

### Development Setup

```bash
git clone https://github.com/phuctruong/solace-browser.git
cd solace-browser
pip install -e ".[dev]"
playwright install chromium
python solace_browser_server.py --head --port 9222
```

### Running Tests

```bash
pytest tests/ -v
```

## Code Standards

- **Python**: Follow PEP 8, use type hints
- **No fallbacks**: `except Exception: pass` is banned (see Fallback Ban doctrine)
- **Evidence**: Every recipe execution must produce an evidence bundle
- **OAuth3**: All actions must pass the 4-gate scope cascade
- **Tests**: Every public method needs a corresponding test

## License

By contributing, you agree that your contributions will be licensed under the project's [Functional Source License](LICENSE).

---

*"Be water, my friend."* — Bruce Lee
