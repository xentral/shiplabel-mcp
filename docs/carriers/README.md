# Carrier setup

Every carrier needs your **own** account with that carrier. This page points you
to where to register and which credentials to set. Config keys map to env vars as
`SHIPLABEL_<KEY>` (uppercase), e.g. `dhl_username` → `SHIPLABEL_DHL_USERNAME`.
See [`../../.env.example`](../../.env.example) for the full list.

Run `describe_carrier <code>` (MCP) or `shiplabel carriers` (CLI) to see the exact
keys a carrier expects at runtime. For how credentials and options reach a carrier
in general (env vars, TOML profiles, inline config, sandbox flags), see the
**[configuration guide](../configuration.md)**.

| Carrier | Where to register | Notes |
|---|---|---|
| **DHL** | [developer.dhl.com](https://developer.dhl.com) + DHL Geschäftskundenportal | Full guide: [`dhl.md`](dhl.md). Sandbox self-serve; production needs a GKP business contract. |
| **DHL Return** | DHL returns API | Uses an API key + receiver id; sandbox available. |
| **DPD** | Your DPD sales contact | Guide: [`dpd.md`](dpd.md). Partner name/token + cloud user id/token. |
| **UPS** | [developer.ups.com](https://developer.ups.com) | Guide: [`ups.md`](ups.md). OAuth client credentials + account number; sandbox available. |
| **FedEx** | [developer.fedex.com](https://developer.fedex.com) | OAuth client credentials + account number; sandbox available. |
| **GLS** | Your GLS sales contact | Guide: [`gls.md`](gls.md). Username/password + customer/contact id. |
| **Sendcloud** | [sendcloud.com](https://www.sendcloud.com) | Guide: [`sendcloud.md`](sendcloud.md). Self-serve API public/secret key + a shipping-method id. Aggregates PostNL, Swiss Post, Österr. Post, DPD, DHL and more. |
| **Shipcloud** | [shipcloud.io](https://www.shipcloud.io) | Self-serve API key + carrier. Spec shipped; not yet exercised in tests — verify against your account. |

**Easiest to start with:** the aggregators **Sendcloud** and **Shipcloud** give
self-serve API keys without a per-carrier business contract. The direct carriers
(DHL, DPD, UPS, FedEx, GLS) each require a business/shipping account with that
carrier.
