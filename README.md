# shiplabel-mcp

**Carrier-agnostic shipping labels as a self-hostable [MCP](https://modelcontextprotocol.io) server.**
Build one shipment request, get a tracking number and a print-ready label back —
the same way for **DHL, DPD, UPS, FedEx, GLS, Sendcloud, Shipcloud** and DHL
Return. Run it yourself, connect it to Claude (or any MCP client), and create
labels straight from a chat, a script, or your own agent.

Carrier-direct: **no account with anyone is required to run this** — you bring
your own account with the carrier(s) you ship with.

> Built and open-sourced by [Xentral](https://xentral.com), the ERP for growing
> product businesses. This server is fully standalone and needs no Xentral account.
>
> **Don't want to self-host?** The same engine is available ready-to-use, fully
> hosted, as the **Carrier Kit** in Xentral AgentOS — no server to run, no setup:
> **[agent.xentral.com/en/starter-kits](https://agent.xentral.com/en/starter-kits)**.

---

## Try it in 2 minutes

Looking around needs no carrier account — `list_carriers` and `describe_carrier`
work out of the box:

```bash
pip install shiplabel-mcp        # or: uv pip install shiplabel-mcp
shiplabel carriers               # lists every carrier, no credentials needed
```

**Your first real label — the fastest path is Sendcloud** (self-serve API key, no
per-carrier contract). Grab a public/secret key and a shipping-method id from the
[Sendcloud panel](https://www.sendcloud.com), then:

```bash
export SHIPLABEL_SENDCLOUD_PUBLIC_KEY="..."
export SHIPLABEL_SENDCLOUD_SECRET_KEY="..."
export SHIPLABEL_SENDCLOUD_METHOD_ID="8"      # a shipping method from your panel
shiplabel create --carrier sendcloud --from examples/sendcloud_request.json --out label.pdf
```

Prefer DHL? The [DHL sandbox](docs/carriers/dhl.md) needs no production contract.
Full setup for every carrier: [per-carrier guides](docs/carriers/) ·
[configuration](docs/configuration.md).

---

## How it works

Carriers are **data, not code.** One generic engine executes a declarative JSON
spec per carrier (endpoints, auth, a payload template, response paths). You build
a single *canonical shipment request* (address + parcel + options); the engine
maps it onto the carrier's API and normalizes the response to `tracking number +
base64 label`. Adding or tweaking a carrier is a JSON file, not a code change.

## Supported carriers

| Carrier | Sandbox | What you need (your own account) |
|---|---|---|
| `dhl` — DHL Paket (DE) | ✅ | developer.dhl.com app + DHL business/GKP contract — see the note below |
| `dhl_return` — DHL Return (DE) | ✅ | DHL returns API key + receiver id |
| `dpd` | — | DPD business account (partner + cloud credentials) |
| `ups` | ✅ | UPS developer app + account number |
| `fedex` | ✅ | FedEx developer app + account number |
| `gls` | — | GLS business account |
| `sendcloud` | — | Sendcloud account (self-serve API key; aggregates PostNL, Swiss Post, Österr. Post, DPD, DHL…) |
| `shipcloud` | — | Shipcloud account (self-serve API key) — spec shipped, not yet exercised in tests |

**Bring your own carrier account.** Every production carrier API requires a
business/shipping account *with that carrier*. This project provides the
integration; it does not include and cannot provide carrier credentials. The
easiest self-serve entry points are the aggregators **Sendcloud** and
**Shipcloud**.

### Per-carrier setup & examples

Each guide has a concrete example: where to register, the exact env config, an
example request, and the command to create a label.

- **[DHL](docs/carriers/dhl.md)** — includes a free sandbox quickstart
- **[GLS](docs/carriers/gls.md)**
- **[UPS](docs/carriers/ups.md)** — has a sandbox
- **[Sendcloud](docs/carriers/sendcloud.md)** — self-serve keys, easiest to start
- **[DPD](docs/carriers/dpd.md)**
- FedEx, Shipcloud and DHL Return follow the same pattern — run
  `describe_carrier <code>` for their keys and see the configuration guide below.

**→ [Configuration guide](docs/configuration.md)** — how credentials and options
reach any carrier (env vars, TOML profiles, inline config, sandbox flags, adding
your own carrier). Same mechanism for all of them.

> ### ⚠️ DHL needs your own credentials
> This repo ships **no** DHL keys. To use DHL you need:
> 1. your own app on **[developer.dhl.com](https://developer.dhl.com)** (client id +
>    secret) — free to register; sandbox works immediately;
> 2. for **production**, additionally a **DHL business-customer contract**
>    (Post & DHL Geschäftskundenportal, "GKP") with a customer/billing number.
>    You don't get this "out of the box" — you register with DHL as a business
>    customer.
>
> **To try it out, the sandbox is enough** (public DHL test login, see
> [`docs/carriers/dhl.md`](docs/carriers/dhl.md)). Without a GKP contract you
> cannot create real (production) labels — that's a DHL requirement, not a limit
> of this tool.

## Quickstart

### Option A — Docker

```bash
git clone https://github.com/xentral/shiplabel-mcp.git
cd shiplabel-mcp
cp .env.example .env        # fill in the carrier(s) you use
docker compose up           # HTTP MCP server on http://127.0.0.1:8000/mcp
```

### Option B — local (Python 3.11+)

```bash
pip install shiplabel-mcp          # or: uv pip install shiplabel-mcp
cp .env.example .env               # and export/source it, or set env vars directly
shiplabel-mcp                      # stdio server (for Claude Desktop / Claude Code)
shiplabel-mcp --http               # or streamable HTTP on 127.0.0.1:8000
```

## Connect it to an MCP client

The server exposes three tools: **`list_carriers`**, **`describe_carrier`**,
**`create_label`**.

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "shiplabel": {
      "command": "shiplabel-mcp",
      "env": {
        "DHL_API_CLIENT_ID_SANDBOX": "your-dev-app-id",
        "DHL_API_CLIENT_SECRET_SANDBOX": "your-dev-app-secret",
        "SHIPLABEL_DHL_USERNAME": "your-gkp-user",
        "SHIPLABEL_DHL_PASSWORD": "your-gkp-password",
        "SHIPLABEL_DHL_ACCOUNTNUMBER": "your-billing-number",
        "SHIPLABEL_DHL_SANDBOX": "true"
      }
    }
  }
}
```

### Claude Code

```bash
claude mcp add shiplabel \
  -e SHIPLABEL_DHL_SANDBOX=true \
  -e SHIPLABEL_DHL_USERNAME=... \
  -- shiplabel-mcp
```

### HTTP mode

Start with `shiplabel-mcp --http` and point your client at
`http://127.0.0.1:8000/mcp` (streamable HTTP transport).

Then just ask: *"list the shipping carriers"*, *"describe what dhl needs"*,
*"create a DHL label from Muster GmbH, Bonn to Erika Beispiel, Bonn, 1.5 kg."*

## Use it as a library or CLI

The MCP server is a thin wrapper over the `shiplabel` Python package, which you
can also use directly:

```python
from decimal import Decimal
from shiplabel import CanonicalShipmentRequest, CarrierSelection, Party, Parcel, create_label

req = CanonicalShipmentRequest(
    carrier=CarrierSelection(code="dhl", product="V01PAK"),
    sender=Party(name="Muster GmbH", street="Sträßchensweg", house_number="10",
                 postal_code="53113", city="Bonn", country="DE"),
    recipient=Party(name="Erika Beispiel", street="Kurt-Schumacher-Str.", house_number="20",
                    postal_code="53113", city="Bonn", country="DE"),
    parcels=[Parcel(id="p1", weight_kg=Decimal("1.5"))],
)
config = {"dhl_username": "...", "dhl_password": "...", "dhl_accountnumber": "...",
          "dhl_api_key": "...", "dhl_api_secret": "...", "dhl_sandbox": True}
result = create_label(config, req)
print(result.parcels[0].tracking_number)  # + result.parcels[0].label.data (base64 PDF)
```

```bash
shiplabel carriers                                  # list carriers
echo '{...}' | shiplabel create --carrier dhl --out label.pdf   # canonical request on stdin
```

See [`src/shiplabel/README.md`](src/shiplabel/README.md) for the full library /
CLI reference and the canonical request shape.

## Configuration

Copy [`.env.example`](.env.example) and set only the carriers you use.

- `SHIPLABEL_<KEY>` → the lowercase carrier config key `<key>`
  (e.g. `SHIPLABEL_DHL_USERNAME` → `dhl_username`).
- DHL developer-app credentials are read from `DHL_API_CLIENT_ID[_SANDBOX]` /
  `DHL_API_CLIENT_SECRET[_SANDBOX]`.
- `SHIPLABEL_CARRIERS_DIR` — a directory of extra `*.json` specs to add or
  override carriers without forking.

Credentials can always also be passed inline per call (the MCP `create_label`
`config` argument, or the library `config` dict) — inline wins over env.

See the **[configuration guide](docs/configuration.md)** for TOML profiles,
source precedence, sandbox flags, and the full canonical request shape.

## Add a carrier

Drop a `<code>.json` spec into `src/shiplabel/carriers/` (or a
`SHIPLABEL_CARRIERS_DIR`). A spec has five parts — `transport`, `auth`,
`capabilities`, `request` (a Jinja payload template), `response`. See
[`src/shiplabel/README.md`](src/shiplabel/README.md#add-a-carrier-declarative)
and `dhl.json` for a complete example. Modern REST/JSON carrier APIs fit the
declarative model; carriers needing computed security (e.g. SOAP WSSE) are out
of scope.

## Security

- **Never commit credentials.** `.env`, `*.env` (except `.env.example`) and
  `carriers.toml` are git-ignored.
- Labels are returned as base64 blobs; the CLI writes them to disk only where you
  ask. Generated `*.pdf`/`*.zpl`/`*.png` are git-ignored.
- Report vulnerabilities per [`SECURITY.md`](SECURITY.md).

## Development

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
python -m pytest        # transport is mocked — no live carrier calls
ruff check .
```

## License

[MIT](LICENSE) © Xentral ERP Software GmbH.
