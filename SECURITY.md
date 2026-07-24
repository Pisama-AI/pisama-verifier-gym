# Security Policy

## Reporting a Vulnerability

Please do not open a public issue for security problems. Email
security@pisama.ai with a description, a reproducer if possible, and the
affected version or commit.

We acknowledge security reports within 2 business days and aim to ship a fix or
mitigation within 7 business days for high-severity issues.

## What Counts

- A packaged artifact that accidentally includes private conversation text,
  credentials, or non-redistributable data.
- A parser or CLI issue that can overwrite unexpected files or execute code from
  crafted input.
- Dependency vulnerabilities that affect the package runtime surface.

Only the latest release line is supported.
