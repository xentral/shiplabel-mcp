# UPS (Shipping REST API)

Direct UPS integration via the UPS Shipping REST API. Uses OAuth2 client
credentials (an app on the UPS developer portal) plus your UPS account number.

## Get access

1. Create an app at **[developer.ups.com](https://developer.ups.com)** → you get
   a **client id** and **client secret**.
2. Have your **UPS account number** ready. UPS offers a test/CIE environment —
   toggle it with `ups_sandbox`.

## Configure

```bash
export SHIPLABEL_UPS_CLIENT_ID="your-app-client-id"
export SHIPLABEL_UPS_CLIENT_SECRET="your-app-client-secret"
export SHIPLABEL_UPS_ACCOUNT_NUMBER="your-ups-account-number"
export SHIPLABEL_UPS_SANDBOX="true"       # false / unset = production
# optional: override the service code (else carrier.product is used)
#export SHIPLABEL_UPS_SERVICE_CODE="11"
```

Run `describe_carrier ups` for the authoritative, current key list.

## Example request

`carrier.product` selects the UPS service (e.g. `11` = UPS Standard):

```json
{
  "carrier": { "code": "ups", "product": "11" },
  "sender":    { "name": "Muster GmbH", "street": "Musterstr.", "house_number": "1",
                 "postal_code": "10115", "city": "Berlin", "country": "DE" },
  "recipient": { "name": "Erika Beispiel", "street": "Beispielweg", "house_number": "2",
                 "postal_code": "80331", "city": "München", "country": "DE" },
  "parcels": [ { "id": "p1", "weight_kg": 2.0,
                 "dimensions_cm": { "length": 30, "width": 20, "height": 10 } } ],
  "references": { "delivery_note": "ORDER-100245" }
}
```

## Create a label

```bash
shiplabel create --carrier ups --from request.json --out label.pdf
```

Or the `create_label` MCP tool with the JSON above as `request`.

## Notes

- Sandbox is toggled per call via `ups_sandbox`.
- Cross-border shipments may need `customs` on the request (see the library
  reference in [`../../src/shiplabel/README.md`](../../src/shiplabel/README.md)).
