# Helm Chart for OAI Next Generation Node B (OAI-gNB)

Chart name: `duranta-oai-gnb` (use this name when installing from an OCI registry, e.g. `helm install <release> oci://<registry>/<namespace>/duranta-oai-gnb --version <version>`). Pods carry the label `app.kubernetes.io/name=duranta-oai-gnb`.

This Helm chart deploys the **OpenAirInterface Next Generation NodeB (OAI-gNB)** — the 5G New Radio (NR) base station component of the OpenAirInterface (OAI) 5G stack.

The chart supports both **RF-Simulated** and **physical (USRP-based)** deployments and has been tested on:

- [Minikube](https://minikube.sigs.k8s.io/docs/)
- [Red Hat OpenShift](https://www.redhat.com/en/technologies/cloud-computing/openshift) versions **4.16-4.20**

---

## ⚠️ Important Notes

- The gNB can operate in **three modes**:
  1. **RF Simulator (rfsim)** — no hardware required.
  2. **VRTSIM** -- no hardware required, read about [vrtsim](https://gitlab.eurecom.fr/oai/openairinterface5g/-/blob/develop/radio/vrtsim/README.md?ref_type=heads) 
  2. **Ethernet-based USRP/RRU** — using `ruInterface`.
  3. **USB-connected USRP (e.g. B210)** — requires host USB pass through.

- Multus-based interfaces inside the pod use **`macvlan`** mode by default.
  If your environment does **not** allow `macvlan`, modify the Multus network definitions accordingly.

- The chart has minimal hardware requirements for RFSim-gNB:
  **2 vCPUs** and **2 GiB RAM**.

---

## 🧩 Overview

The [OAI-gNB](https://gitlab.eurecom.fr/oai/openairinterface5g/-/tree/develop) implements 5G NR base station functions per **3GPP Release 16**.
The same code base supports **gNB**, **CU/DU splits**, and **NR-UE**.

More information:
- [OAI 5G NR Feature Set](https://gitlab.eurecom.fr/oai/openairinterface5g/-/blob/develop/doc/FEATURE_SET.md#openairinterface-5g-nr-feature-set)
- [nr-softmodem (binary entrypoint)](https://gitlab.eurecom.fr/oai/openairinterface5g/-/blob/develop/docker/scripts/gnb_entrypoint.sh?ref_type=heads)
- The configuration file used by the nf is in [config.yaml](./config.yaml). It is 
YAML based. You can refer to the sample configuration files in [Example configuration files](https://gitlab.eurecom.fr/oai/openairinterface5g/-/tree/develop/targets/PROJECTS/GENERIC-NR-5GC/CONF). Not all are YAML based but you can use the same parameter names

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
├── Chart.yaml
├── templates/
│ ├── configmap.yaml
│ ├── deployment.yaml
│ ├── _helpers.tpl
│ ├── nad.yaml
│ ├── NOTES.txt
│ ├── rbac.yaml
│ ├── serviceaccount.yaml
│ └── service.yaml
└── values.yaml
```

The chart creates:

1. **Service**
2. **RBAC** (Role + RoleBinding)
3. **Deployment**
4. **ConfigMap** (mounts gNB configuration)
5. **ServiceAccount**
6. **NetworkAttachmentDefinition** *(optional — when Multus is enabled)*

---

## ⚙️ Configuration Parameters

All parameters are defined in [`values.yaml`](./values.yaml).

### 🧱 Base Parameters

| Parameter | Allowed Values | Description |
|------------|----------------|-------------|
| **kubernetesDistribution** | `Vanilla` / `Openshift` | Kubernetes flavor |
| **nfimage.repository** | String | Image name (default: `oaisoftwarealliance/oai-gnb`) |
| **nfimage.version** | String | Image tag (default: `develop`) |
| **nfimage.pullPolicy** | `IfNotPresent` / `Always` / `Never` | Kubernetes image pull policy |
| **imagePullSecrets** | List | Optional; for private registries (e.g., DockerHub credentials) |
| **serviceAccount.create** | `true` / `false` | Whether to create a new service account |
| **serviceAccount.annotations** | Map | Optional annotations |
| **podSecurityContext.runAsUser** | Integer | Must be `0` (root) |
| **podSecurityContext.runAsGroup** | Integer | Must be `0` (root) |

💡 Optional:
You can specify private registry credentials by un-commenting and editing:

```yaml
imagePullSecrets:
 - name: regcred
```
---

### 🕸️ Multus Interface Configuration

Multus enables static IP assignments for N2/N3/RU interfaces.

| Parameter | Type | Description |
|------------|------|-------------|
| **multus.enabled** | `true` / `false` | Enable multus networking (default: true) |
| **multus.interfaces[].name** | String | Logical name inside container (e.g., `n2`, `n3`, `ru`) |
| **multus.interfaces[].hostInterface** | String | Physical host interface |
| **multus.interfaces[].ipAdd** | IPv4 | Static IP address |
| **multus.interfaces[].netmask** | String | Network mask |
| **multus.interfaces[].gateway** | IPv4 (optional) | Interface gateway |
| **multus.interfaces[].routes** | list [{}] | Routes to a subnet ex [{'dst': '','gw': ''}] (optional) |
| **multus.interfaces[].defaultRoute** | IPv4 (optional) | Default route in container |
| **multus.interfaces[].mtu** | Integer (optional) | MTU size |
| **multus.interfaces[].enabled** | `true` / `false` | Enable or disable the interface (an interface without `enabled: true` is not created) |
| **multus.interfaces[].type** | `macvlan` / `vlan` | CNI plugin type (default: `macvlan`) |
| **multus.interfaces[].mode** | `bridge` / `vepa` / `private` / `passthru` | macvlan mode (default: `bridge`) |
| **multus.interfaces[].vlan** | Integer | VLAN ID, required when `type: vlan` |
| **multus.interfaces[].mac** | MAC | Fixed MAC address for the interface (optional) |

> 💡 **Tip:**
> If you do not have a gateway for Multus interfaces, leave `gateway` and `defaultRoute` empty.
> Incorrect gateway configuration can break pod networking and DNS resolution.
> For DHCP addresses you need to the CNI plugin which provides DHCP addresses
---

### ⚙️ gNB Configuration

The main runtime configuration is mounted through `config.yaml`.
You can adapt it by editing `config.yaml` or override certain parameters in the `config` section of `values.yaml`.

| Parameter | Example | Description |
|------------|----------|-------------|
| **config.timeZone** | `"Europe/Paris"` | Pod timezone |
| **config.useAdditionalOptions** | `"-E --rfsim --log_config.global_log_options level,nocolor,time"` | Extra command-line options passed to `nr-softmodem` |
| **config.gnbName** | `"oai-gnb"` | gNB logical name |
| **config.gdbstack** | `0` | Enable (1) or disable (0) GDB traces |
| **config.radio** | `"rfsim"`, `"vrtsim"`, `"b2xx"`, `"n3xx"`, `"x3xx"`, `"aw2s"` | Select radio hardware |
| **config.amfHost** | `"oai-amf"` | AMF hostname or IP |
| **config.tac** | `1` | Tracking Area Code |
| **config.enableE2** | `false` | Start the E2 agent towards the near-RT RIC |
| **config.ricHost** | `"duranta-flexric"` | RIC hostname or IP; with FlexRIC on multus use its E2 address |
| **config.n2IfName** | `""` | Pod interface used for N2; empty = chosen automatically from `multus.interfaces` names |
| **config.n3IfName** | `""` | Pod interface used for N3; empty = chosen automatically from `multus.interfaces` names |
| **config.plmn_list** | List | PLMN and S-NSSAI configuration (must match AMF/SMF/UPF) |

> **Interface overrides:** by default each `*_IF_NAME` is taken from the multus interface with the matching `name` (falling back to another enabled one, then `eth0`). Set `config.<x>IfName` to choose it explicitly, e.g. one multus interface `net1` carrying all traffic:
> ```yaml
> config:
>   n2IfName: "net1"
>   n3IfName: "net1"
> ```

---

### 🧰 Debugging & Developer Options

| Parameter | Values | Description |
|------------|---------|-------------|
| **start.gnb** | `true` / `false` | If `false`, NF container sleeps (manual debug) |
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

---

## 🚀 Deployment Guide

### 0️⃣  Prerequisites
Ensure that the **core network** is already running. You can deploy it using:

- [OAI 5G Core Basic](../../oai-5g-basic/README.md)
- [OAI 5G Core Mini](../../oai-5g-mini/README.md)

### 1️⃣  Deploy the gNB

Check and adjust network and configuration parameters in `templates/configmap.yaml`, then install:

```bash
helm install oai-gnb .
```

### 2️⃣  Deploy NR-UE

```bash
helm install oai-nr-ue ../duranta-oai-nr-ue
```

### 3️⃣  Test UE Connectivity

```bash
kubectl exec -it <oai-nr-ue-pod> -- bash
# Ping UPF/SPGWU
ping -I oaitun_ue1 12.1.1.1
# Ping external DNS
ping -I oaitun_ue1 8.8.8.8
```
## 📝 Notes & Recommendations

1. **Multus Setup**: Ensure Multus CNI is correctly configured before enabling it in the chart. Avoid invalid gateway settings, as they may break pod connectivity.
2. **Configuration Flexibility**: The default config block exposes limited options for simplicity. For advanced setups, copy your own configuration file into `./config.yaml`.
3. **Performance**:
- For realistic radio setups:
- CPU cores should be more than 4GHz clock speed for USRPs and minimum 3.5
- CPU should support AVX2 for RFSIM/USRP B210 environment 
- CPU should support AVX2 for USRP N3xx/x4xx and O-RAN RUs with un-compress mode
- CPU should support AVX2 and AVX512 for USRP N3xx/x4xx and O-RAN RUs with compress mode
