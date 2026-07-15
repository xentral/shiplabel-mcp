# Sendcloud (Public API v2)

Sendcloud is a **multi-carrier aggregator** — one integration reaches PostNL,
DPD, DHL, Swiss Post, Österreichische Post and more. This is usually the
**easiest carrier to start with**: the API keys are self-serve, no per-carrier
business contract needed to begin.

## Get access

1. Sign up at **[sendcloud.com](https://www.sendcloud.com)**.
2. In the Sendcloud panel, create an **API key** → you get a **public key** and a
   **secret key**.
3. Pick a **shipping method** in Sendcloud; its numeric **method id** is your
   `carrier.product`.

## Configure

```bash
export SHIPLABEL_SENDCLOUD_PUBLIC_KEY="your-public-key"
export SHIPLABEL_SENDCLOUD_SECRET_KEY="your-secret-key"
export SHIPLABEL_SENDCLOUD_METHOD_ID="8"      # the shipping-method id you chose
# optional: a specific Sendcloud sender address id
#export SHIPLABEL_SENDCLOUD_SENDER_ID="12345"
```

Run `describe_carrier sendcloud` for the authoritative, current key list.

## Example request

`carrier.product` is the Sendcloud shipping-method id:

```json
{
  "carrier": { "code": "sendcloud", "product": "8" },
  "sender":    { "name": "Muster GmbH", "street": "Musterstr.", "house_number": "1",
                 "postal_code": "10115", "city": "Berlin", "country": "DE" },
  "recipient": { "name": "Jan Jansen", "street": "Dorpsstraat", "house_number": "5",
                 "postal_code": "1011AB", "city": "Amsterdam", "country": "NL" },
  "parcels": [ { "id": "p1", "weight_kg": 1.2 } ],
  "references": { "delivery_note": "ORDER-100245" }
}
```

## Create a label

```bash
shiplabel create --carrier sendcloud --from request.json --out label.pdf
```

Or the `create_label` MCP tool with the JSON above as `request`.

## Notes

- Supported service: **insurance** (`services.insurance`).
- Because Sendcloud fronts many carriers, the reachable destinations depend on
  the shipping method you pick in the Sendcloud panel.
