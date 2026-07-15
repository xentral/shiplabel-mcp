# GLS (ShipIT REST API)

Direct GLS integration via the GLS ShipIT REST API. You need a **GLS business
account**; GLS provisions your API user, password and customer/contact ids.

## Get access

Ask your GLS sales/onboarding contact for **ShipIT REST API** access. You'll
receive a username, password, a customer id and a contact id.

## Configure

```bash
export SHIPLABEL_GLS_USERNAME="your-gls-user"
export SHIPLABEL_GLS_PASSWORD="your-gls-password"
export SHIPLABEL_GLS_CUSTOMER_ID="your-customer-id"
export SHIPLABEL_GLS_CONTACT_ID="your-contact-id"
# optional: pin a specific GLS product/service
#export SHIPLABEL_GLS_SERVICE="flex"
```

Run `shiplabel carriers` (CLI) or the `describe_carrier gls` MCP tool to see the
authoritative, current key list.

## Example request

`examples/` shape, with `carrier.product` set to a GLS product (e.g. `flex`):

```json
{
  "carrier": { "code": "gls", "product": "flex" },
  "sender":    { "name": "Muster GmbH", "street": "Musterstr.", "house_number": "1",
                 "postal_code": "10115", "city": "Berlin", "country": "DE" },
  "recipient": { "name": "Erika Beispiel", "street": "Beispielweg", "house_number": "2",
                 "postal_code": "80331", "city": "München", "country": "DE" },
  "parcels": [ { "id": "p1", "weight_kg": 1.5 } ],
  "references": { "delivery_note": "ORDER-100245" }
}
```

## Create a label

```bash
# CLI
shiplabel create --carrier gls --from request.json --out label.pdf
```

From an MCP client, call `create_label` with the JSON above as `request`.

## Notes

- Supported service: **cash on delivery** (`services.cod`).
- No public sandbox — test against your GLS account per GLS's guidance.
