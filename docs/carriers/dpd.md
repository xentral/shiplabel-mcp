# DPD (Cloud API)

Direct DPD integration via the DPD Cloud API (`setOrder`). You need a **DPD
business account**; DPD provisions partner and cloud-user credentials.

## Get access

Ask your DPD contact for **DPD Cloud API** access. You'll receive:

- a **partner name** and **partner token** (identifies the integration), and
- a **cloud user id** and **user token** (identifies your account).

## Configure

```bash
export SHIPLABEL_DPD_PARTNER_NAME="your-partner-name"
export SHIPLABEL_DPD_PARTNER_TOKEN="your-partner-token"
export SHIPLABEL_DPD_CLOUD_USER_ID="your-cloud-user-id"
export SHIPLABEL_DPD_USER_TOKEN="your-user-token"
# optional
#export SHIPLABEL_DPD_FORMAT="pdf"      # label format
#export SHIPLABEL_DPD_PREDICT="true"    # DPD Predict notifications
```

Run `describe_carrier dpd` for the authoritative, current key list.

## Example request

`carrier.product` selects the DPD product (e.g. `Classic`):

```json
{
  "carrier": { "code": "dpd", "product": "Classic" },
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
shiplabel create --carrier dpd --from request.json --out label.pdf
```

Or the `create_label` MCP tool with the JSON above as `request`.

## Notes

- `dpd_predict` enables DPD Predict recipient notifications (needs a recipient
  email/phone on the request).
