# Security policy

## Reporting a vulnerability

Please report security issues privately to **security@xentral.com** rather than
opening a public issue. We'll acknowledge receipt and keep you updated on a fix.

## Handling credentials

This project never ships carrier credentials and should never contain any:

- Keep credentials in your `.env` / environment or a private secret store. `.env`,
  `*.env` (except `.env.example`) and `carriers.toml` are git-ignored.
- The engine accepts credentials inline per call too — do not log the `config`
  object.
- Generated labels (`*.pdf`, `*.zpl`, `*.png`) may contain address data and are
  git-ignored by default.
