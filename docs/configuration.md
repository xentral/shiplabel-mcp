# Configuration guide

This explains how credentials and options reach a carrier — the same mechanism
for every carrier. Per-carrier specifics (which keys, where to register) live in
[`carriers/`](carriers/).

## The three ways to supply credentials

You can mix them; **later sources win**:

1. **Environment variables** — `SHIPLABEL_<KEY>` (uppercase). Best for a server /
   Docker deployment.
2. **A TOML profile** — named credential sets in a file. Best for the CLI when you
   juggle several accounts.
3. **Inline `config`** — passed with the call (the MCP `create_label` `config`
   argument, or the library `config` dict). Best for ad-hoc/testing. Inline wins
   over everything.

### 1. Environment variables

Every carrier config key maps to `SHIPLABEL_<KEY>` in uppercase:

| Config key | Environment variable |
|---|---|
| `dhl_username` | `SHIPLABEL_DHL_USERNAME` |
| `gls_customer_id` | `SHIPLABEL_GLS_CUSTOMER_ID` |
| `sendcloud_secret_key` | `SHIPLABEL_SENDCLOUD_SECRET_KEY` |

Booleans are written as `true` / `false`:

```bash
export SHIPLABEL_DHL_SANDBOX="true"
```

Copy [`.env.example`](../.env.example), fill in only the carriers you use, and
load it (Docker `env_file`, `source .env`, or your process manager).

### 2. TOML profiles (CLI)

Put named profiles in a TOML file — by default `~/.config/shiplabel/carriers.toml`
(override with `--config <path>` or `$SHIPLABEL_CONFIG`):

```toml
[profiles.dhl-sandbox]
dhl_username = "user-valid"
dhl_password = "SandboxPasswort2023!"
dhl_accountnumber = "33333333330102"
dhl_sandbox = true

[profiles.gls-live]
gls_username = "..."
gls_password = "..."
gls_customer_id = "..."
gls_contact_id = "..."
```

```bash
shiplabel create --profile dhl-sandbox --from request.json --out label.pdf
```

`SHIPLABEL_<KEY>` env vars still override individual keys within a profile.

### 3. Inline config

From an MCP client, pass a `config` object with `create_label`:

```json
{
  "request": { "carrier": { "code": "gls", "product": "flex" }, "sender": {}, "recipient": {}, "parcels": [] },
  "config": { "gls_username": "...", "gls_password": "...", "gls_customer_id": "...", "gls_contact_id": "..." }
}
```

From the library, pass a plain dict as the first argument to `create_label`.

## Finding the exact keys for a carrier

Don't guess — ask at runtime:

- MCP: `describe_carrier <code>` → the carrier's config keys, supported services
  and label formats.
- CLI/library: `shiplabel carriers`, or `shiplabel.describe("<code>")`.

Each per-carrier page in [`carriers/`](carriers/) lists the keys too, but
`describe` is always the authoritative, current source.

## Sandbox vs production

Carriers that have a test environment expose a `<carrier>_sandbox` flag
(`dhl_sandbox`, `ups_sandbox`, `fedex_sandbox`, `dhl_return_sandbox`). Set it
truthy to hit the sandbox:

```bash
export SHIPLABEL_UPS_SANDBOX="true"
```

Carriers without a public sandbox (GLS, DPD, Sendcloud, Shipcloud) are tested
against your live account per the carrier's guidance.

## DHL's app credentials (`source: "env"`)

DHL is special: besides your business login, it needs a **developer-app**
credential (client id + secret from developer.dhl.com). Those are read from the
environment directly — separate from the `SHIPLABEL_` prefix, and separate per
environment:

```bash
# sandbox
export DHL_API_CLIENT_ID_SANDBOX="..."
export DHL_API_CLIENT_SECRET_SANDBOX="..."
# production
export DHL_API_CLIENT_ID="..."
export DHL_API_CLIENT_SECRET="..."
```

This is the generic `source: "env"` mechanism (any carrier spec can mark a key as
env-sourced); you can still override with an inline `config` value. Full DHL
walkthrough: [`carriers/dhl.md`](carriers/dhl.md).

## The canonical request

Every carrier takes the same request shape; the engine maps it onto that
carrier's API:

```jsonc
{
  "carrier":   { "code": "dhl", "product": "V01PAK" },  // product = the carrier's service/product
  "sender":    { "name": "...", "street": "...", "house_number": "...", "postal_code": "...", "city": "...", "country": "DE" },
  "recipient": { "name": "...", "street": "...", "house_number": "...", "postal_code": "...", "city": "...", "country": "DE" },
  "parcels":   [ { "id": "p1", "weight_kg": 1.5, "dimensions_cm": { "length": 30, "width": 20, "height": 10 } } ],
  "references": { "delivery_note": "ORDER-100245" },     // maps to the carrier reference / refNo
  "services":  { "cod": { "amount": "19.90", "currency": "EUR" } },  // optional, if the carrier supports it
  "label":     { "format": "pdf" }                       // pdf/zpl/png — omit for the carrier default
}
```

- `carrier.product` picks the service/product (e.g. DHL `V01PAK`, UPS `11`,
  Sendcloud method id). See each carrier page for examples.
- `services` are only accepted if the carrier's spec declares them — a paid
  service is never silently dropped.
- Full field reference: [`../src/shiplabel/README.md`](../src/shiplabel/README.md).

## Adding or overriding a carrier

Point `SHIPLABEL_CARRIERS_DIR` at a directory of `*.json` specs to add a new
carrier or override a bundled one without forking:

```bash
export SHIPLABEL_CARRIERS_DIR="/etc/shiplabel/carriers"
```

Specs there are loaded after the bundled ones and win on a code clash. See
[adding a carrier](../src/shiplabel/README.md#add-a-carrier-declarative).
