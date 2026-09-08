# FortiGate-side setup

The app never writes to a FortiGate. It only:

1. **Reads** VPN/admin login logs from each FortiGate (or from FortiCloud), over a **read-only** REST API token.
2. **Writes** the resulting blacklist to Azure Blob Storage, which each FortiGate then **pulls from itself** via its built-in External Resource (Threat Feed) feature.

You configure both sides on the FortiGate. Steps below use the GUI where possible, with the equivalent CLI.

> Field names/endpoints below target FortiOS 7.x. If you're on 6.4 or an older 7.0.x build, some names differ slightly — validate with the app's "Test Connection" button after adding a device, and adjust as needed.

## 1. Create a read-only API admin for log polling

**GUI:** System > Admin Profiles > Create New

Create a profile (e.g. `readonly-logs`) with:
- Log & Report: **Read**
- VPN: **Read**
- User & Authentication: **Read**
- Everything else: **None**

Then: System > Administrators > Create New > REST API Admin
- Administrator Profile: `readonly-logs`
- Restrict login to trusted hosts: set this to the IP of the server running the app
- Save — the API token is shown **once**. Paste it into the app when adding the device (it's encrypted at rest).

**CLI equivalent:**

```
config system accprofile
    edit "readonly-logs"
        set logreport read
        set vpngrp read
        set authgrp read
    next
end

config system api-user
    edit "ip-blacklister"
        set accprofile "readonly-logs"
        set vdom "root"
        config trusthost
            edit 1
                set ipv4-trusthost <app-server-ip> 255.255.255.255
            next
        end
    next
end

execute api-user generate-key ip-blacklister
```

Copy the generated key into the app's "Add device" form as the API token.

## 2. Point External Resource objects at the Azure blob parts

After you configure Azure Storage in the app's **Azure Publish** page and click **Publish now**, the app shows you one blob URL per chunk (e.g. `part-1.txt`, `part-2.txt`, ...). Create one External Resource per URL:

**GUI:** Security Fabric > External Connectors > Create New > IP Address (Threat Feed)
- Name: `blacklist-part1` (etc.)
- URI: the blob URL from the app (includes a read SAS token if you left "Generate read SAS tokens" enabled)
- Refresh Rate: 5 minutes (or match `AZURE_PUBLISH_INTERVAL_MINUTES`)

**CLI equivalent** (repeat per chunk):

```
config system external-resource
    edit "blacklist-part1"
        set type address
        set resource "https://<account>.blob.core.windows.net/fortigate-blacklist/blacklist/part-1.txt?<sas-token>"
        set refresh-rate 5
    next
end
```

## 3. Reference every part in a deny policy (or a local-in policy)

Once created, an `address`-type external resource is usable directly wherever a firewall address is expected — no separate address object needed.

**Firewall policy** (blocks the IPs from reaching anything through the FortiGate):

```
config firewall policy
    edit 0
        set name "Block-published-blacklist"
        set srcintf "wan1"
        set dstintf "any"
        set srcaddr "blacklist-part1" "blacklist-part2" "blacklist-part3"
        set dstaddr "all"
        set action deny
        set schedule "always"
        set service "ALL"
        set logtraffic all
    next
end
```

Place this policy **above** your SSL VPN / IPsec / admin-access allow rules.

**Local-in policy** (blocks traffic destined to the FortiGate's own SSL VPN portal / IKE / admin GUI specifically, without touching general traffic policies — often preferred just to stop brute-forcing the VPN/admin login itself):

```
config firewall local-in-policy
    edit 0
        set intf "wan1"
        set srcaddr "blacklist-part1" "blacklist-part2" "blacklist-part3"
        set dstaddr "all"
        set action deny
        set service "ALL"
        set schedule "always"
    next
end
```

If your blacklist grows beyond one chunk, add every `blacklist-part*` object to the `srcaddr` list of the same policy — the app will tell you (via the Azure Publish page) exactly how many parts currently exist.

## 4. If your FortiGate forwards logs to FortiCloud instead of storing them locally

Some deployments disable local log storage entirely. In that case, set the device's **Log source** to **FortiCloud** in the app instead of **Device API**, and link a FortiCloud credential (see [forticloud-setup.md](./forticloud-setup.md)). You still create the read-only API admin above if you *also* want the app to be able to test/monitor the device directly — otherwise it's optional for FortiCloud-sourced devices.
