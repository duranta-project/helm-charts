# Helm Chart for OAI Distributed Unit (OAI-DU)

Chart name: `duranta-oai-du` (use this name when installing from an OCI registry, e.g. `helm install <release> oci://<registry>/<namespace>/duranta-oai-du --version <version>`). Pods carry the label `app.kubernetes.io/name=duranta-oai-du`.

This Helm chart deploys the **OpenAirInterface Distributed Unit (OAI-DU)**.  
It supports **RF-Simulated**, **split**, and **hardware-based** (USRP/RRU) configurations.

The chart has been tested on:
- [Minikube](https://minikube.sigs.k8s.io/docs/)
- [Red Hat OpenShift](https://www.redhat.com/fr/technologies/cloud-computing/openshift) versions **4.16–4.20**

**Note:**  
- RF-SIM requires at least **2 CPUs** and **2 GiB RAM**.  
- For split deployments with dedicated interfaces (e.g., RU or F1), you’ll need the [Multus CNI plugin](https://github.com/k8snetworkplumbingwg/multus-cni).

---

## ⚠️ Important Notes

- The DU can operate in **three modes**:
  1. **RF Simulator (rfsim)** — no hardware required.  
  2. **Ethernet-based USRP/RRU** — using `ruInterface`.
  3. **USB-connected USRP (e.g. B210)** — requires host USB pass through.

- Multus-based interfaces inside the pod use **`macvlan`** mode by default.  
  If your environment does **not** allow `macvlan`, modify the Multus network definitions accordingly.

- The chart has minimal hardware requirements for RFSim-du:  
  **2 vCPUs** and **2 GiB RAM**.

---

## 🧩 Overview

The [OAI-DU](https://gitlab.eurecom.fr/oai/openairinterface5g/-/tree/develop) implements 5G NR base station functions per **3GPP Release 16**.  
The same code base supports **gNB**, **CU/DU splits**, and **NR-UE**.

More information:
- [OAI 5G NR Feature Set](https://gitlab.eurecom.fr/oai/openairinterface5g/-/blob/develop/doc/FEATURE_SET.md#openairinterface-5g-nr-feature-set)
- [nr-softmodem (binary entrypoint)](https://gitlab.eurecom.fr/oai/openairinterface5g/-/blob/develop/docker/scripts/gnb_entrypoint.sh?ref_type=heads)
- The configuration file used by the nf is in [config.yaml](./config.yaml). It is 
YAML based. You can refer to the sample configuration files in [Example configuration files](https://gitlab.eurecom.fr/oai/openairinterface5g/-/tree/develop/targets/PROJECTS/GENERIC-NR-5GC/CONF). Not all are YAML based but you can use the same parameter names.

---

## 📦 Container Images

Our [Jenkins Platform](https://jenkins-oai.eurecom.fr/view/RAN/) publishes new ubuntu images weekly on Docker Hub:

| Image | Description |
|--------|--------------|
| [`oaisoftwarealliance/oai-gnb`](https://hub.docker.com/r/oaisoftwarealliance/oai-gnb) | Monolithic gNB, DU, CU, CU-CP |
| [`oaisoftwarealliance/oai-nr-cuup`](https://hub.docker.com/r/oaisoftwarealliance/oai-nr-cuup) | CU-UP component |

Tags available:
- `develop` → latest development image  
- `YYYY.wNN` → weekly tagged build (e.g., `2025.w44`)

> Only **Ubuntu 24.04** images are published.  
> For **Red Hat/UBI** systems, build locally following [this guide](../../../openshift/README.md).

---

## 📁 Chart Structure

```
.
├── Chart.yaml
├── templates
│ ├── configmap.yaml
│ ├── deployment.yaml
│ ├── _helpers.tpl
│ ├── nad.yaml
│ ├── NOTES.txt
│ ├── rbac.yaml
│ ├── serviceaccount.yaml
│ └── service.yaml
├── config.yaml
└── values.yaml
```

The chart creates:

1. **Service**
2. **RBAC** (Role + RoleBinding)
3. **Deployment**
4. **ConfigMap** (mounts DU configuration)
5. **ServiceAccount**
6. **NetworkAttachmentDefinition** *(optional — when Multus is enabled)*

## Parameters

All configurable parameters are defined in [values.yaml](./values.yaml).  
Below table summarizes key parameters.

### 🧱 Base Parameters

| Parameter | Allowed Values | Description |
|------------|----------------|--------------|
| **kubernetesDistribution** | `Vanilla` / `Openshift` | Select Kubernetes flavor |
| **nfimage.repository** | String | DU image name (default: `oaisoftwarealliance/oai-gnb`) |
| **nfimage.version** | String | Image tag (default: `develop`) |
| **nfimage.pullPolicy** | `IfNotPresent` / `Always` / `Never` | Container image pull policy |
| **imagePullSecrets** | List | Optional; for private registries (e.g., DockerHub credentials) |
| **serviceAccount.create** | `true` / `false` | Create a dedicated service account |
| **serviceAccount.annotations** | Map | Optional service account annotations |
| **podSecurityContext.runAsUser** | Integer | Usually `0` (root) |
| **podSecurityContext.runAsGroup** | Integer | Usually `0` (root) |

💡 Optional:
You can specify private registry credentials by un-commenting and editing:

```yaml
imagePullSecrets:
 - name: regcred
```

---

### 🕸️ Multus Interface Configuration

| Parameter | Allowed Values | Description |
|------------|----------------|--------------|
| **multus.enabled** | `true` / `false` | Enable Multus (default: `false`) |
| **multus.interfaces[].name** | `f1c` / `f1u` / `ru` | Logical interface name inside the container |
| **multus.interfaces[].hostInterface** | String | Host network interface name |
| **multus.interfaces[].ipAdd** | IPv4 | Static IP assigned to the interface |
| **multus.interfaces[].type** | String | macvlan, vlan (default: `macvlan`) |
| **multus.interfaces[].netmask** | CIDR mask | Interface netmask |
| **multus.interfaces[].defaultRoute** | IPv4 | Default route (optional) |
| **multus.interfaces[].routes** | list [{}] | Routes to a subnet ex [{'dst': '','gw': ''}] (optional) |
| **multus.interfaces[].gateway** | IPv4 | Gateway for interface (optional) |
| **multus.interfaces[].mtu** | Integer | MTU for interface (optional) |
| **multus.interfaces[].enabled** | `true` / `false` | Enable or disable interface (an interface without `enabled: true` is not created) |
| **multus.interfaces[].mode** | `bridge` / `vepa` / `private` / `passthru` | macvlan mode (default: `bridge`) |
| **multus.interfaces[].vlan** | Integer | VLAN ID, required when `type: vlan` |
| **multus.interfaces[].mac** | MAC | Fixed MAC address for the interface (optional) |

> 💡 **Tip:**  
> If you do not have a gateway for Multus interfaces, leave `gateway` and `defaultRoute` empty.  
> Incorrect gateway configuration can break pod networking and DNS resolution.
> For DHCP addresses you need to the CNI plugin which provides DHCP addresses

> ⚙️ **Usage Modes:**
> - **RF-SIM Mode:** only F1 interface needed (can reuse `eth0`)  
> - **Physical DU:** separate `ru` interface required for RU/Radio connection  

---

### ⚙️ DU Configuration

The main runtime configuration is mounted through `config.yaml`.  
You can adapt it by editing `config.yaml` or override certain parameters in the `config` section of `values.yaml`.

| Parameter | Description |
|------------|--------------|
| **config.timeZone** | Container timezone |
| **config.useAdditionalOptions** | CLI flags for `nr-softmodem` |
| **config.duName** | DU node name |
| **config.usrp** | Hardware mode (`rfsim`, `b2xx`, `n3xx`, `x3xx`) |
| **config.cuHost** | CU hostname or IP |
| **config.gdbstack** | `1` to enable GDB traces |
| **config.tac** | Tracking Area Code |
| **config.enableE2** | Start the E2 agent towards the near-RT RIC (default: `false`) |
| **config.ricHost** | RIC hostname or IP (default: `duranta-flexric`); with FlexRIC on multus use its E2 address |
| **config.f1duPort** | UDP port for F1-U (GTP-U) |
| **config.f1cIfName** | Pod interface used for F1-C; empty = chosen automatically from `multus.interfaces` names |
| **config.f1uIfName** | Pod interface used for F1-U; empty = chosen automatically from `multus.interfaces` names |
| **config.plmn_list** | PLMN and S-NSSAI configuration |

> **Interface overrides:** by default `F1C_IF_NAME` is taken from the multus interface named `f1c` (falling back to `f1u`, then `eth0`). A separate F1-U address is only used when an `f1u` interface is enabled or `config.f1uIfName` is set; otherwise F1-U uses the F1-C address. Set `config.<x>IfName` to choose it explicitly, e.g. one multus interface `net1` carrying all traffic:
> ```yaml
> config:
>   f1cIfName: "net1"
>   f1uIfName: "net1"
> ```

---

### 🧰 Debugging & Developer Options

| Parameter | Values | Description |
|------------|---------|-------------|
| **start.du** | `true` / `false` | If `false`, NF container sleeps (manual debug) |
| **start.tcpdump** | `true` / `false` | If `true`, tcpdump sidecar starts (sleep mode) |
| **includeTcpDumpContainer** | `true` / `false` | Include tcpdump sidecar |
| **tcpdumpimage.repository** | String | Tcpdump image name |
| **tcpdumpimage.version** | String | Tcpdump tag |
| **tcpdumpimage.pullPolicy** | String | Pull policy |
| **resources.define** | `true` / `false` | Enable explicit CPU/memory limits (default: true) |
| **readinessProbe** / **livenessProbe** | `true` / `false` | `pgrep -f nr-softmodem` probes (default: true) |
| **resources.limits.nf.cpu / memory** | String | NF resource limits |
| **resources.requests.nf.cpu / memory** | String | NF resource requests |
| **resources.limits.tcpdump.cpu / memory** | String | tcpdump sidecar limits |
| **resources.requests.tcpdump.cpu / memory** | String | tcpdump sidecar requests |
| **terminationGracePeriodSeconds** | Integer | Grace period before termination (default: 5 s) |
| **securityContext** | Map | NF container security context |
| **nodeSelector** | Map | Node label selector |
| **nodeName** | String | Pin the pod to a node |

## 🚀 Deployment Examples

Before deploying the DU, ensure the **Core Network** and **CU** are operational:

- [OAI 5G Core Basic](../../oai-5g-basic/README.md)
- [OAI 5G Core Mini](../../oai-5g-mini/README.md)

### F1 Split (CU–DU)

```bash
# to set the distribution --set kubernetesDistribution="Vanilla/Openshift"
helm install oai-cu ../duranta-oai-cu
# Wait for CU to start
helm install oai-du .
```

### F1 + E1 Split (CU-CP + CU-UP + DU)
```bash
# to set the distribution --set kubernetesDistribution="Vanilla/Openshift"
helm install oai-cu-cp ../duranta-oai-cu-cp
# Wait for CU-CP to start
helm install oai-cu-up ../duranta-oai-cu-up
helm install oai-du .
```

### Connect the UE

Deploy NR-UE once the DU is running:

```bash
helm install oai-nr-ue ../duranta-oai-nr-ue
```

### After connection:

```bash
kubectl exec -it <oai-nr-ue-pod> -- bash
ping -I oaitun_ue1 12.1.1.1   # towards UPF
ping -I oaitun_ue1 8.8.8.8    # external connectivity
```

If `oaitun_ue1` interface is missing, UE is not properly attached.

## 📝 Notes & Recommendations

1. **Multus Setup**: Ensure Multus CNI is correctly configured before enabling it in the chart. Avoid invalid gateway settings, as they may break pod connectivity.
2. **Configuration Flexibility**: The default config block exposes limited options for simplicity. For advanced setups, copy your own configuration file into `./config.yaml`.
3. **Performance**:
- For realistic radio setups:
- CPU cores should be more than 4GHz clock speed for USRPs and minimum 3.5
- CPU should support AVX2 for RFSIM/USRP B210 environment 
- CPU should support AVX2 for USRP N3xx/x4xx and O-RAN RUs with un-compress mode
- CPU should support AVX2 and AVX512 for USRP N3xx/x4xx and O-RAN RUs with compress mode
