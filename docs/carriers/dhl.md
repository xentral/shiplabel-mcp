# DHL Paket (Germany)

DHL uses OAuth2 with two credential pairs:

1. **A developer-app credential** (client id + secret) from
   [developer.dhl.com](https://developer.dhl.com) — this is the "app" identity.
2. **Your DHL business-customer login** (Geschäftskundenportal / "GKP"): a
   username, password and a billing/customer number.

## Try it in the sandbox (free, ~5 minutes)

1. Register at [developer.dhl.com](https://developer.dhl.com) and create an app
   with access to **Parcel DE Shipping (Post & Parcel Germany)**. You get a
   sandbox client id + secret.
2. Set the app credentials (read directly from the environment):

   ```bash
   export DHL_API_CLIENT_ID_SANDBOX="your-sandbox-app-id"
   export DHL_API_CLIENT_SECRET_SANDBOX="your-sandbox-app-secret"
   ```

3. Use DHL's **public sandbox business login** — no GKP contract needed for
   testing:

   ```bash
   export SHIPLABEL_DHL_USERNAME="user-valid"
   export SHIPLABEL_DHL_PASSWORD="SandboxPasswort2023!"
   export SHIPLABEL_DHL_ACCOUNTNUMBER="33333333330102"   # billing no. for V01PAK (national)
   export SHIPLABEL_DHL_SANDBOX="true"
   ```

4. Create a label (product `V01PAK` = DHL Paket national):

   ```bash
   shiplabel create --carrier dhl --from examples/dhl_sandbox_request.json --out label.pdf
   ```

   or via the MCP `create_label` tool with the request in
   [`examples/dhl_sandbox_request.json`](../../examples/dhl_sandbox_request.json).

## Going to production

Production label creation requires a **DHL business-customer contract** (Post &
DHL Geschäftskundenportal, "GKP") with your own customer/billing number. You
register with DHL as a business customer — it is not available "out of the box".
Once you have it:

```bash
export DHL_API_CLIENT_ID="your-production-app-id"
export DHL_API_CLIENT_SECRET="your-production-app-secret"
export SHIPLABEL_DHL_USERNAME="your-gkp-user"
export SHIPLABEL_DHL_PASSWORD="your-gkp-password"
export SHIPLABEL_DHL_ACCOUNTNUMBER="your-billing-number"
export SHIPLABEL_DHL_SANDBOX="false"
```

## Gotchas

- **`references.delivery_note` must be 8–35 characters** — DHL rejects shorter
  reference numbers (`refNo`) with a 400.
- Billing numbers are per product: the sandbox number above is for `V01PAK`
  (national). Other products (e.g. international, Warenpost) use different billing
  numbers — see your DHL business portal.
- Some spec fields (e.g. the full ISO country-code map) are marked `# VERIFY` —
  faithful to DHL's documented shape but confirm against your live lanes before
  relying on them in production.
