# Contributing to Trade-Claw 🚀

First off, thank you for considering contributing to Trade-Claw! We're excited to have you on board.

This document provides guidelines and instructions for contributing to the project.

---

## 📋 Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help each other grow

---

## 🐛 Reporting Bugs

Found a bug? Great! Here's how to report it:

### Before Submitting a Bug Report

- Check if the bug has already been reported in [Issues](https://github.com/misteraufumwegen/Trade-Claw/issues)
- Check the documentation and README
- Try to reproduce it with the latest code on `master`

### Submitting a Bug Report

Create an issue with:

```markdown
**Title:** [BUG] Brief description

**Description:**
- What did you expect to happen?
- What actually happened?
- Steps to reproduce:
  1. Step 1
  2. Step 2
  3. ...

**Environment:**
- OS: (Windows/macOS/Linux)
- Python version: (e.g., 3.11.5)
- Trade-Claw version: (git commit hash)
- Broker: (Alpaca/OANDA)

**Additional context:**
(Any other relevant info)
```

---

## 💡 Suggesting Enhancements

Have an idea? We'd love to hear it!

### Submitting a Feature Request

Create an issue with:

```markdown
**Title:** [FEATURE] Brief description

**Description:**
- What problem does this solve?
- How should it work?
- Why is this important for Trade-Claw?

**Additional context:**
(Sketches, examples, or references)
```

---

## 🔧 Setting Up Your Development Environment

### Prerequisites

- Python 3.11+
- Git
- Optional: a broker sandbox/paper-trading account (Alpaca, OANDA, Hyperliquid
  testnet, or anything CCXT supports). Trade-Claw also ships a Mock broker that
  needs no external account.

### Local Setup

1. **Fork the repository**
   ```bash
   git clone https://github.com/YOUR-USERNAME/Trade-Claw.git
   cd Trade-Claw
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Set up Python environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your sandbox/paper trading credentials
   ```

5. **Start the app**
   ```bash
   # Windows: double-click start-app.bat
   # macOS: double-click start-app.command (first time: chmod +x)
   # Any platform:
   python launcher.py
   ```

6. **Run tests**
   ```bash
   pytest tests/ -v
   ```

---

## 📝 Making Changes

### Code Style

- Follow PEP 8
- Use type hints (Python 3.11+ syntax)
- Write docstrings for functions and classes
- Maximum line length: 100 characters

### Commit Messages

Use clear, descriptive commit messages:

```
[FEATURE] Add correlation analysis endpoint

- Implement flexible asset correlation calculation
- Support dynamic asset selection
- Add REST endpoint POST /api/correlation/analyze
- Include 15+ tests for edge cases

Closes #42
```

Format:
```
[TYPE] Brief description

- What was changed
- Why it was changed
- Any breaking changes

Closes #ISSUE_NUMBER (if applicable)
```

Types: `[FEATURE]`, `[BUG]`, `[DOCS]`, `[TEST]`, `[REFACTOR]`, `[PERF]`, `[SECURITY]`

### Testing

All code should have tests:

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_grader.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

**Coverage target: 80%+**

---

## 📤 Submitting a Pull Request

### Before Submitting

1. Update tests for new functionality
2. Update documentation (README, docstrings)
3. Run `pytest` locally — all tests must pass
4. Run `black` for code formatting (optional but recommended)

### Submitting Your PR

1. **Push your branch**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a Pull Request** on GitHub with:
   - **Title:** Follows commit message format
   - **Description:** Explains what changed and why
   - **Links:** Reference related issues (`Closes #42`)

   ```markdown
   ## Description
   This PR adds flexible correlation analysis for multi-asset trading.

   ## Changes
   - New `CorrelationEngine` class for dynamic asset analysis
   - REST endpoint: `POST /api/correlation/analyze`
   - 25+ unit tests
   - Updated docs in `docs/design/COMPONENTS.md`

   ## Testing
   - All 168 tests passing ✅
   - New correlation tests: 25/25 passing
   - Manual testing on Alpaca Paper account

   Closes #42
   ```

3. **Wait for review** — maintainers will review your code

### PR Review Process

- Code review for quality, tests, and documentation
- Automated tests must pass
- At least one approval from a maintainer
- Address review comments (be responsive!)

---

## 🚀 What Gets Merged?

We accept PRs that:

✅ **Bug Fixes**
- Fixes real issues with the bot
- Includes test cases
- Well-documented

✅ **Features**
- Aligns with Trade-Claw's vision (automated, intelligent, risk-aware trading)
- Improves user experience or functionality
- Includes tests (minimum 80% coverage)
- Documented (README, docstrings, design docs)

✅ **Improvements**
- Performance optimizations
- Security hardening
- Documentation improvements
- Test coverage increases

❌ **Won't Merge**
- Trivial whitespace changes without substance
- Unrelated style changes to the entire codebase
- Code that disables or breaks risk controls
- Undocumented features with no tests

---

## 🔐 Security

Found a security vulnerability?

**Do NOT open a public issue.** Instead, email: `deniz@simsir.ch`

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

We'll acknowledge within 48 hours and work on a fix.

---

## 📚 Documentation

Good documentation is essential. Help us improve it!

### Documentation Types

1. **Code Comments** — Explain *why*, not *what*
2. **Docstrings** — Module, class, function documentation
3. **README.md** — Getting started, quick reference
4. **docs/AUTOPILOT_SETUP.md** — TradingView webhook + autopilot setup
5. **docs/CUSTOM_BROKERS.md** — Plugin-based broker registration
6. **docs/design/DESIGN_SYSTEM.md** — UI design tokens (source of truth for `frontend/styles.css`)

### Updating Docs

When submitting a PR with code changes, also update:
- Docstrings in the code
- README if you changed user-facing behavior
- Relevant design docs if you changed architecture

---

## 🎯 Project Priorities

In order of importance:

1. **Security & Risk Management** — Never compromise
2. **Code Quality** — Tests, documentation, clarity
3. **Features** — New capabilities that help users
4. **Performance** — Optimize after it works correctly
5. **Polish** — UI/UX improvements

---

## 📧 Questions?

- Open a GitHub Discussion for questions
- Check existing Issues for similar topics
- Read the docs in `/docs/design/`

---

## 🙏 Thank You!

Every contribution makes Trade-Claw better for everyone. We appreciate your time and effort!

**Happy coding! 🚀**

---

**Questions or need help?** Open an issue and we'll guide you!
