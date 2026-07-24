# Contributing to pisama-verifier-gym

Thanks for improving `pisama-verifier-gym`. This package is for auditable
verifier artifacts and small reproducible metric code.

## Development Setup

```bash
git clone https://github.com/Pisama-AI/pisama.git
cd pisama/packages/pisama-verifier-gym
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

## Guidelines

- Use real, redistributable, sanitized artifacts only.
- Do not include raw conversation text unless the source license explicitly
  allows redistribution.
- Keep metric code dependency-free unless there is a strong reason.
- Add tests for every metric or data-loading change.
- Keep public metrics reproducible from files committed with the package.

## Pull Request Checklist

- [ ] `ruff check src tests`
- [ ] `mypy src/pisama_verifier_gym`
- [ ] `pytest -q`
- [ ] `python -m build`
- [ ] New artifacts document provenance, license, and sanitization.

By submitting a pull request, you agree that your contribution is licensed under
MIT, the same license as this package.
