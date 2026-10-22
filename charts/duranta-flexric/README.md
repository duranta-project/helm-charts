<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Helm Chart for FlexRIC (`duranta-flexric`)

This Helm chart deploys the **FlexRIC near-RT RIC**. RAN functions (gNB, CU, CU-CP, DU) connect to it over **E2**
(SCTP 36421); xApps connect over E42 (SCTP 36422).

Source code: [duranta-project/flexric](https://github.com/duranta-project/flexric)
Container image: [`oaisoftwarealliance/oai-flexric`](https://hub.docker.com/r/oaisoftwarealliance/oai-flexric)

---

## 📁 Chart Structure

```
.
├── Chart.yaml
├── templates
│ ├── configmap.yaml      # flexric.conf, NEAR_RIC_IP is filled with the E2 address at start-up
│ ├── deployment.yaml
│ ├── _helpers.tpl
│ ├── nad.yaml            # multus NetworkAttachmentDefinition (when multus is enabled)
│ ├── NOTES.txt
│ ├── rbac.yaml           # OpenShift only
│ ├── serviceaccount.yaml
│ └── service.yaml        # headless service "duranta-flexric" (E2 36421, E42 36422)
└── values.yaml
```

## Parameters

### 🧱 Base Parameters

| Parameter | Allowed Values | Description |
|------------|----------------|--------------|
| **kubernetesDistribution** | `Vanilla` / `Openshift` | Select Kubernetes flavor |
| **nfimage.repository** | String | RIC image (default: `docker.io/oaisoftwarealliance/oai-flexric`) |
| **nfimage.version** | String | Image tag (default: `develop`) |
| **nfimage.pullPolicy** | `IfNotPresent` / `Always` / `Never` | Container image pull policy |
| **imagePullSecrets** | List | Optional; for private registries, e.g. `[{name: regcred}]` |
| **serviceAccount.create** | `true` / `false` | Create a dedicated service account |
| **serviceAccount.annotations** | Map | Optional service account annotations |
| **podSecurityContext.runAsUser** | Integer | Usually `0` (root) |
| **podSecurityContext.runAsGroup** | Integer | Usually `0` (root) |
| **config.timeZone** | String | Container timezone (default: `Europe/Paris`) |

### 🕸️ Multus Interface Configuration

| Parameter | Allowed Values | Description |
|------------|----------------|--------------|
| **multus.enabled** | `true` / `false` | Enable Multus (default: `false`) |
| **multus.interfaces[].name** | String | Interface name inside the pod; the E2 address is taken from the enabled interface named `e2` (else the first enabled one) |
| **multus.interfaces[].enabled** | `true` / `false` | An interface without `enabled: true` is not created |
| **multus.interfaces[].hostInterface** | String | Host network interface name |
| **multus.interfaces[].ipAdd** | IPv4 | Static IP of the interface (this is the E2 address the RIC listens on) |
| **multus.interfaces[].netmask** | CIDR mask | Interface netmask |
| **multus.interfaces[].type** | `macvlan` / `vlan` | CNI plugin type (default: `macvlan`) |
| **multus.interfaces[].mode** | `bridge` / `vepa` / `private` / `passthru` | macvlan mode (default: `bridge`) |
| **multus.interfaces[].vlan** | Integer | VLAN ID, required when `type: vlan` |
| **multus.interfaces[].defaultRoute** | IPv4 | Default route via this interface (optional, only one interface may set it) |
| **multus.interfaces[].gateway** | IPv4 | Gateway for the interface (optional) |
| **multus.interfaces[].routes** | List | Extra routes, e.g. `[{dst: "172.21.8.0/22", gw: "192.168.85.1"}]` (optional) |
| **multus.interfaces[].mtu** | Integer | Interface MTU (optional) |
| **multus.interfaces[].mac** | MAC | Fixed MAC address (optional) |

> **E2 address with multus:** the RIC listens only on its E2 address (`NEAR_RIC_IP`), which is the multus interface's
> `ipAdd` when multus is enabled and the pod IP otherwise. The `duranta-flexric` service always resolves to the pod's
> `eth0` address, so **with multus enabled set `config.ricHost` of the gNB/CU/DU to the RIC's E2 `ipAdd`**.
> Without multus the default `ricHost: duranta-flexric` works.

### 💾 Shared xApp database (Grafana)

| Parameter | Allowed Values | Description |
|------------|----------------|--------------|
| **xappDb.enabled** | `true` / `false` | Create the PVC `duranta-flexric-xapp-db` and mount it at `/xapp_db_dir` (default: `false`) |
| **xappDb.size** | Quantity | PVC size (default: `1Gi`) |
| **xappDb.storageClass** | String | Storage class (empty = default class) |
| **xappDb.accessMode** | String | Access mode (default: `ReadWriteOnce`) |

The xApps of [`duranta-xapp`](../duranta-xapp/README.md#-grafana) write their SQLite databases into this PVC and
Grafana reads them; see that README for the full setup.

### 🧰 Debugging & Developer Options

| Parameter | Values | Description |
|------------|---------|-------------|
| **start.ric** | `true` / `false` | If `false`, the RIC container sleeps (manual debug) |
| **start.tcpdump** | `true` / `false` | If `true`, the tcpdump sidecar captures to `/tmp/pcap` |
| **includeTcpDumpContainer** | `true` / `false` | Add the tcpdump sidecar |
| **tcpdumpimage.repository / version / pullPolicy** | String | Tcpdump sidecar image |
| **resources.define** | `true` / `false` | Apply the requests/limits below (default: `true`) |
| **readinessProbe** / **livenessProbe** | `true` / `false` | `pgrep -f nearRT-RIC` probes (default: true) |
| **resources.limits.nf.cpu / memory** | String | RIC container limits |
| **resources.requests.nf.cpu / memory** | String | RIC container requests |
| **resources.limits.tcpdump.cpu / memory** | String | tcpdump sidecar limits |
| **resources.requests.tcpdump.cpu / memory** | String | tcpdump sidecar requests |
| **terminationGracePeriodSeconds** | Integer | Grace period before termination (default: 5 s) |
| **nodeSelector** | Map | Node label selector |
| **nodeName** | String | Pin the pod to a node |

## 🚀 Deployment

```bash
# to set the distribution --set kubernetesDistribution="Vanilla/Openshift"
helm install flexric ./duranta-flexric
```

Then enable E2 on the RAN side, e.g. for the gNB:

```bash
helm install gnb ./duranta-oai-gnb --set config.enableE2=true --set config.ricHost=duranta-flexric
# with FlexRIC on multus: --set config.ricHost=<multus.interfaces[e2].ipAdd>
```

Then run xApps against it with the [`duranta-xapp`](../duranta-xapp/README.md) chart, e.g.
`helm install xapp-kpm ./duranta-xapp --set xapp=kpm`.

Check the connection in the RIC logs: `kubectl logs deploy/duranta-flexric -c ric` shows the E2 setup from the RAN function.
