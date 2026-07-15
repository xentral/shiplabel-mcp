# Contributing

Thanks for helping improve shiplabel-mcp.

## Dev setup

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
python -m pytest        # transport is mocked — no live carrier calls
ruff check .
```

## Adding or fixing a carrier

Carriers are declarative JSON specs in `src/shiplabel/carriers/`. Adding one is a
spec file, not code — see the walkthrough in
[`src/shiplabel/README.md`](src/shiplabel/README.md#add-a-carrier-declarative)
and `dhl.json` as a complete reference. Add a test in
`src/shiplabel/tests/test_carriers.py` (mock the transport; assert the outgoing
payload and the normalized result). Fields you couldn't verify against a live
lane should be marked `# VERIFY` in the spec.

## Pull requests

- Keep changes focused; one carrier / one fix per PR where possible.
- `ruff check .` and `pytest` must pass (CI runs both on 3.11 and 3.12).
- Never commit credentials or real labels.

## Scope

Modern REST/JSON carrier APIs fit the declarative engine. Carriers requiring
computed security (e.g. SOAP WSSE digests) or binary label post-processing are
intentionally out of scope for now.
