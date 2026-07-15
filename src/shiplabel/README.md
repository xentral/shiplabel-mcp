# shiplabel

Carrier-agnostic shipping-label service. Build one `CanonicalShipmentRequest`,
hand it to `create_label()`, get back a normalized `CanonicalLabelResult`
(tracking number + base64 label) — regardless of carrier.

**Carriers are data, not code.** Each carrier is a declarative spec (endpoints,
auth scheme, a payload template, response paths). One generic engine executes any
spec. The specs are bundled with this package under `shiplabel/carriers/*.json`.
Adding a carrier is a JSON file — no code change. To add or override a carrier
without editing the package, point `SHIPLABEL_CARRIERS_DIR` at a directory of
extra `*.json` specs (they win on a code clash).

## Use it as a library

```python
from decimal import Decimal
from shiplabel import CanonicalShipmentRequest, CarrierSelection, Party, Parcel, create_label

req = CanonicalShipmentRequest(
    carrier=CarrierSelection(code="dhl", product="V01PAK"),
    sender=Party(name="Muster GmbH", street="Musterstr.", house_number="1",
                 postal_code="10115", city="Berlin", country="DE"),
    recipient=Party(name="Erika Beispiel", street="Beispielweg", house_number="2",
                    postal_code="80331", city="München", country="DE"),
    parcels=[Parcel(id="p1", weight_kg=Decimal("1.5"))],
)
config = {"dhl_api_key": "...", "dhl_api_secret": "...", "dhl_username": "...",
          "dhl_password": "...", "dhl_accountnumber": "...", "dhl_sandbox": True}
result = create_label(config, req)
print(result.parcels[0].tracking_number)  # + result.parcels[0].label.data (base64)
```

The engine is credential-agnostic: `config` is a plain dict, so an embedding
caller (an agent, this backend) provides credentials however it likes.

## Carriers & their config keys

Each carrier reads a small set of keys from `config` (or, from the CLI, a
profile / `SHIPLABEL_<KEY>` env var). `--sandbox` flips the `<carrier>_sandbox`
key where a sandbox exists.

| Carrier | `carrier.product` example | Required `config` keys |
|---|---|---|
| `dhl` | `V01PAK` | `dhl_api_key`, `dhl_api_secret`, `dhl_username`, `dhl_password`, `dhl_accountnumber` (`dhl_sandbox`) |
| `dpd` | `Classic` | `dpd_partner_name`, `dpd_partner_token`, `dpd_cloud_user_id`, `dpd_user_token` |
| `ups` | `11` (UPS Standard) | `ups_client_id`, `ups_client_secret`, `ups_account_number` (`ups_sandbox`) |
| `fedex` | `FEDEX_INTERNATIONAL_PRIORITY` | `fedex_client_id`, `fedex_client_secret`, `fedex_account_number`, `fedex_service` (`fedex_sandbox`) |
| `gls` | `flex` | `gls_username`, `gls_password`, `gls_customer_id`, `gls_contact_id` |
| `sendcloud` | Sendcloud method id | `sendcloud_public_key`, `sendcloud_secret_key`, `sendcloud_method_id` |
| `shipcloud` | `dhl_standard` | `shipcloud_api_key`, `shipcloud_carrier` (`shipcloud_affiliate_id`) |
| `dhl_return` | receiver id | `dhl_return_api_key`, `dhl_return_username`, `dhl_return_password`, `dhl_return_receiver_id` (`dhl_return_sandbox`) |

### Env-sourced credentials (`source: "env"`)

A `config_keys` entry can be marked `source: "env"` to declare that its value is
read from the environment (an app-level credential), never a per-shipment field.
`env` is either a variable name or a `{prod, sandbox}` map picked by the carrier's
sandbox flag; an inline value the caller passes still wins. This is a generic
mechanism (any carrier can use it), resolved once in the engine — not per-carrier
code.

DHL uses it for its developer-app credential (from developer.dhl.com): you supply
your GKP login + billing number as normal config, while
`dhl_api_key`/`dhl_api_secret` come from `DHL_API_CLIENT_ID`/`DHL_API_CLIENT_SECRET`
(prod) or `DHL_API_CLIENT_ID_SANDBOX`/`DHL_API_CLIENT_SECRET_SANDBOX` (sandbox).

The exact config keys, supported services and output formats per carrier are
also queryable at runtime via `describe` (`shiplabel.describe("dhl")`).

**Regional coverage:** `sendcloud` is a multi-carrier aggregator — it reaches
PostNL (NL), Swiss Post (CH), Österreichische Post (AT), DPD, DHL and more
through one modern REST integration, selected by the Sendcloud method id.

Fields marked in the specs with `# VERIFY` (e.g. DHL's ISO map coverage, FedEx's
default service type) should be confirmed against the carrier's live API before
production; they are faithful to the documented shape but not yet run against
every lane.

## Use it from the command line

```bash
python -m shiplabel carriers                          # list available carriers
python -m shiplabel create --from req.json \          # request JSON (or '-' = stdin)
    --profile dhl-sandbox --out label.pdf             # writes label, prints tracking
echo '{...}' | python -m shiplabel create --carrier dhl --profile dhl-live --json
```

`req.json` is a `CanonicalShipmentRequest` as JSON — the same shape an agent
builds.

### Credential profiles

`--profile <name>` reads `[profiles.<name>]` from a TOML file (`--config` path,
else `$SHIPLABEL_CONFIG`, else `~/.config/shiplabel/carriers.toml`).
`SHIPLABEL_<KEY>` env vars override individual keys.

```toml
# ~/.config/shiplabel/carriers.toml
[profiles.dhl-sandbox]
dhl_api_key = "..."
dhl_username = "..."
dhl_sandbox = true
```

## Add a carrier (declarative)

Add a `<code>.json` spec in `shiplabel/carriers/` (or in a directory pointed to
by `SHIPLABEL_CARRIERS_DIR`, to avoid editing the package). A spec has five
parts — `transport` (URLs, endpoint, method, query), `auth` (scheme + which
config keys hold the credentials), `capabilities` (which canonical services the
carrier supports), `request` (the payload template), and `response` (where
tracking + label sit). See `carriers/dhl.json` for a full example, including
customs and cash-on-delivery.

The `request` template maps the canonical model onto the carrier body with three
constructs:

- `{{ expr }}` — a Jinja expression. A leaf that is *only* an expression keeps
  its native type, so `"{{ (parcel.weight_kg * 1000) | int }}"` yields `1500`,
  not `"1500"`.
- `$for: "item in iterable"` + `$body` — fan out one canonical parcel (or
  customs item) into N carrier objects.
- `$if: "<expr>"` on a dict — drop the key when falsy; with `$value` it becomes
  a conditional scalar.

Value lookups (e.g. ISO-3166 alpha-2 → alpha-3) use `value_maps` + the injected
`vmap('name', key)` helper. A requested service not in `capabilities` raises
`UnsupportedServiceError` — a paid service is never silently dropped.

### Scope of the declarative model

A spec describes structure and static maps; it cannot run an algorithm. Every
current carrier is a modern REST/JSON API that fits. Carriers needing computed
security (e.g. a SOAP WSSE password digest) or binary post-processing are out of
scope for now and intentionally not carried as code.

## Test

```bash
python -m pytest shiplabel/tests -q   # mocks the transport; no live carrier calls
```
