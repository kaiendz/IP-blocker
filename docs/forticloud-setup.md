# FortiCloud log source setup

Use this when a FortiGate's logs are forwarded off-box to FortiCloud (FortiGate Cloud / FortiAnalyzer Cloud) rather than retained locally — the app pulls from FortiCloud's API instead of the device directly.

> FortiCloud's log-query API differs slightly depending on your subscription (FortiGate Cloud vs. FortiAnalyzer Cloud vs. the unified FortiCloud IAM). The OAuth token endpoint below is stable; the log-query endpoint the app calls (`services/forticloud_client.py`) may need its `log_query_base_url` adjusted for your subscription — use the "Test Connection" action after setup and check `backend` logs if events aren't showing up.

## 1. Create an API application in FortiCloud IAM

1. Sign in to [FortiCloud](https://support.fortinet.com) and open **IAM**.
2. Create a new **API User** (client-credentials style), scoped to read-only access on Logging / FortiView for the account that owns your FortiGate(s).
3. Note the generated **Client ID** and **Client Secret**.

## 2. Add the credential in the app

Devices page → **FortiCloud credentials** → add a credential with:
- Name: something identifying (e.g. `hq-forticloud`)
- Client ID / Client secret: from step 1
- API gateway: `https://customerapiauth.fortinet.com` (default, usually correct)

## 3. Link a device to it

When adding (or editing) a FortiGate device, set **Log source** to `FortiCloud`, pick the credential you just created, and enter the device's **serial number** (visible on the FortiGate's dashboard or via `get system status`).

## 4. Verify

Use **Test Connection** on the device row — it confirms the OAuth token exchange succeeds. If event counts stay at zero after that, the log-query endpoint shape likely needs adjusting for your subscription; see the caveat at the top of this doc.

## Alternative: if the device is directly reachable

This OAuth-based FortiCloud IAM path exists for FortiGates the app **can't** reach directly over the network (e.g. no inbound route to the device's management IP). If the device *is* directly reachable, it's simpler and more reliably documented to instead set **Log source** to `Device API` and point the app at the FortiGate itself — its own Log Access API (`/api/v2/log/forticloud/event/<subtype>`) transparently proxies the query to FortiCloud when `store=forticloud`, without needing separate FortiCloud IAM credentials at all.
