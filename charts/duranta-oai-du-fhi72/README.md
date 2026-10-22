# Helm Chart for OAI Distributed Unit (oai-du) Fronthaul 7.2

Chart name: `duranta-oai-du-fhi72` (use this name when installing from an OCI registry, e.g. `helm install <release> oci://<registry>/<namespace>/duranta-oai-du-fhi72 --version <version>`). Pods carry the label `app.kubernetes.io/name=duranta-oai-du-fhi72`.

7.2 fronthaul helm-charts are a bit special than RFSIM or VRTSIM based 
helm-charts as it requires special configuration on the DU host server. The DU 
host server should have: 

1. [PTP Operator](https://github.com/openshift/ptp-operator) or PTP configured in leader or follower mode
2. [SRIOV Operator](https://github.com/k8snetworkplumbingwg/sriov-network-operator) or sriov interface configuration
3. Disable chrony or timedatectl ntp service
4. OS realtime configuration with isolated cpus for workload

Performance profile for **openshift**:

```yaml
  globallyDisableIrqLoadBalancing: true
  additionalKernelArgs:
   - nmi_watchdog=0
   - audit=0
   - idle=poll
   - mce=off
   - processor.max_cstate=1
   - idle=poll
   - vfio_pci.enable_sriov=1
   - vfio_pci.disable_idle_d3=11 #depends on intel or AMD
   - intel_idle.max_cstate=0 #depends on intel or AMD
   - intel_iommu=on  #depends on intel or AMD
  cpu:
    isolated: "$ISOLATED_CPUS"
    reserved: "$RESERVED_CPUS" # 4 should be enough
  hugepages:
    defaultHugepagesSize: "1G"
    pages:
    - size: "1G"
      count: 20
      node: 0
  net:
    userLevelNetworking: true  #optional
  numa:
    topologyPolicy: restricted
  workloadHints:
    realTime: true
    highPowerConsumption: true
    perPodPowerManagement: false
  realTimeKernel:
    enabled: true
```

Isolated cpus are for the workload and reserved are for the operating system. 

Make sure this profile configure `cpuManagerPolicy` to static. If it does not 
then the helm-charts will not work. In openshift you can check 
`kubeletconfigs.machineconfiguration.openshift.io` to confirm cpuManagerPolicy. 

For **vanilla kubernetes** based cluster, before making the cluster update your 
grub command line to below command line

```bash
isolcpus=managed_irq,$ISOLATED_CPU nohz_full=$ISOLATED_CPU nohz=on rcu_nocbs=$ISOLATED_CPUS irqaffinity=$RESERVED_CPUS rcu_nocb_poll selinux=0 enforcing=0 crashkernel=auto nosoftlockup hugepagesz=1G hugepages=20 hugepagesz=2M hugepages=0 default_hugepagesz=1G mitigations=off processor.max_cstate=1 idle=poll iommu=pt skew_tick=1 tsc=nowatchdog nmi_watchdog=0 softlockup_panic=0 audit=0 mce=off
```

For intel (x86) you can add:

```bash
intel_pstate=disable intel_iommu=on
```

For AMD (x86) you can add:

```bash
amd_iommu=on
#disabling amd_pstate only available in kernel +6.8
amd_pstate=disable
```

**NOTE**: Use either tuned-adm or update grub. But don't do both. 

Sample kubeadm configuration (only for reference) you can use:

```yaml
apiVersion: kubeadm.k8s.io/v1beta4
kind: InitConfiguration
localAPIEndpoint:
  advertiseAddress: "$YOUR_CLUSTER_IP_ADDRESS"
  bindPort: 6443
nodeRegistration:
  criSocket: unix:///var/run/crio/crio.sock
---
kind: ClusterConfiguration
apiVersion: kubeadm.k8s.io/v1beta4
clusterName: "$YOUR_CLUSTER_NAME"
kubernetesVersion: "v1.31.1"
networking:
  serviceSubnet: "10.96.0.0/16"
  podSubnet: "10.244.0.0/24"
  dnsDomain: "cluster.local"
---
kind: KubeletConfiguration
apiVersion: kubelet.config.k8s.io/v1beta1
cgroupDriver: systemd
cpuManagerPolicy: static
cpuManagerPolicyOptions:
   "full-pcpus-only": "true"
reservedSystemCPUs: $RESERVED_CPUS
memorySwap: {}
topologyManagerPolicy: "best-effort"
failSwapOn: false
containerLogMaxSize: 50Mi
featureGates:
   CPUManager: true
   CPUManagerPolicyOptions: true
   CPUManagerPolicyBetaOptions: true
---
apiVersion: kubeproxy.config.k8s.io/v1alpha1
kind: KubeProxyConfiguration
ipvs:
  strictARP: true
```

Make sure you are also restricing the cpu affinity of systemd in 
`/etc/systemd/system.conf`

Common configuration: 

Openshift or Vanilla K8s cluster might need (depending if one of your 
configuration automatically applies it)

```bash
sysctl kernel.sched_rt_runtime_us
sysctl kernel.timer_migration
# check the values if they are not -1 and 0 then update
echo -1 > /proc/sys/kernel/sched_rt_runtime_us
echo 0 > /proc/sys/kernel/timer_migration
```

## Introduction

To know more about the feature set of OpenAirInterface you can check it [here](https://gitlab.eurecom.fr/oai/openairinterface5g/-/blob/develop/doc/FEATURE_SET.md#openairinterface-5g-nr-feature-set). 

The [codebase](https://gitlab.eurecom.fr/oai/openairinterface5g/-/tree/develop) for gNB, CU, DU, CU-CP/CU-UP, NR-UE is the same. 

The configuration file used by the nf is in [config.yaml](./config.yaml). It is 
YAML based. You can refer to the sample configuration files in [Example configuration files](https://gitlab.eurecom.fr/oai/openairinterface5g/-/tree/develop/targets/PROJECTS/GENERIC-NR-5GC/CONF). 

Not all are YAML based but you can use the same parameter names.

It is strongly recommended that you read about [OAI 7.2 implementation](https://gitlab.eurecom.fr/oai/openairinterface5g/-/blob/develop/doc/ORAN_FHI7.2_Tutorial.md?ref_type=heads)

## Prerequisite

1. Configure the baremetal DU server as mentioned explained above  
2. Before using the helm-charts you have to create two dedicated `SriovNetworkNodePolicy` for C and U plane. 

Using below Kubernetes manifest

```yaml
apiVersion: sriovnetwork.openshift.io/v1
kind: SriovNetworkNodePolicy
metadata:      
  name: RESOURCE_NAME_U_PLANE
  # in vanilla k8s the namespace is sriov-network-operator
  namespace: openshift-sriov-network-operator
spec:
  resourceName: RESOURCE_NAME_U_PLANE
  nodeSelector:
    feature.node.kubernetes.io/network-sriov.capable: "true"
  priority: 11
  mtu: 9216
  deviceType: vfio-pci
  isRdma: false
  numVfs: 4
  linkType: eth
  nicSelector:
    pfNames:
      - 'PHYSICAL_INTERFACE#0-1'     # Same device specified by rootDevices
    rootDevices:
      - 'PCI_ADDRESS_OF_THE_PHYSICAL_INTERFACE' # PCI bus address
---
apiVersion: sriovnetwork.openshift.io/v1
kind: SriovNetworkNodePolicy
metadata:      
  name: RESOURCE_NAME_C_PLANE
  # in vanilla k8s the namespace is sriov-network-operator
namespace: openshift-sriov-network-operator
spec:
  resourceName: RESOURCE_NAME_C_PLANE
  nodeSelector:
    feature.node.kubernetes.io/network-sriov.capable: "true"
  priority: 12
  mtu: 9216
  deviceType: vfio-pci
  isRdma: false
  numVfs: 4
  linkType: eth
  nicSelector:
    pfNames:
      - 'PHYSICAL_INTERFACE#2-3'     # Same device specified by rootDevices
    rootDevices:
      - 'PCI_ADDRESS_OF_THE_PHYSICAL_INTERFACE' # PCI bus address
```

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

### 🕸️ Multus Interface Configuration

| Parameter | Allowed Values | Description |
|------------|----------------|--------------|
| **multus.enabled** | `true` / `false` | Enable Multus (default: `false`) |
| **multus.interfaces[].name** | `f1c` / `f1u` / `ru` | Logical interface name inside the container |
| **multus.interfaces[].hostInterface** | String | Host network interface name |
| **multus.interfaces[].type** | String | macvlan, vlan, sriov (default: `macvlan`) |
| **multus.interfaces[].ipAdd** | IPv4 | Static IP assigned to the interface |
| **multus.interfaces[].netmask** | CIDR mask | Interface netmask |
| **multus.interfaces[].defaultRoute** | IPv4 | Default route (optional) |
| **multus.interfaces[].gateway** | IPv4 | Gateway for interface (optional) |
| **multus.interfaces[].mtu** | Integer | MTU for interface (optional) |
| **multus.interfaces[].enabled** | `true` / `false` | Enable or disable interface (an interface without `enabled: true` is not created) |
| **multus.interfaces[].mode** | `bridge` / `vepa` / `private` / `passthru` | macvlan mode (default: `bridge`) |
| **multus.interfaces[].vlan** | Integer | VLAN ID, required when `type: vlan` |
| **multus.interfaces[].routes** | List | Extra routes, e.g. `[{dst: "172.21.8.0/22", gw: "192.168.57.1"}]` (optional) |
| **multus.interfaces[].mac** | MAC | Fixed MAC address for the interface (optional) |
| **multus.interfaces[].sriovResourceName** | String | SR-IOV device-plugin resource name (for `type: sriov`) |
| **multus.interfaces[].sriovNetworkNamespace** | String | Namespace of the SR-IOV network operator (for `type: sriov`) |

> 💡 **Tip:**  
> If you do not have a gateway for Multus interfaces, leave `gateway` and `defaultRoute` empty.  
> Incorrect gateway configuration can break pod networking and DNS resolution.

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
| **config.cuHost** | CU hostname or IP |
| **config.gdbstack** | `1` to enable GDB traces |
| **config.tac** | Tracking Area Code |
| **config.enableE2** | Start the E2 agent towards the near-RT RIC (default: `false`) |
| **config.ricHost** | RIC hostname or IP (default: `duranta-flexric`); with FlexRIC on multus use its E2 address |
| **config.f1duPort** | UDP port for F1-U (GTP-U) |
| **config.ruCPlaneMacAdd** | MAC address of the RU C-plane (O-RAN 7.2 fronthaul) |
| **config.ruUPlaneMacAdd** | MAC address of the RU U-plane (O-RAN 7.2 fronthaul) |
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
| **resources.define** | `true` / `false` | Enable explicit CPU/memory limits |
| **resources.limits.cpu / memory** | String | NF CPU/memory limits |
| **resources.limits.hugepages** | Quantity | Hugepages-1Gi limit (DPDK) |
| **resources.limits.sriovClaims** | List | SR-IOV resources to claim, e.g. `openshift.io/ruvfiou` (use your cluster's prefix) |
| **resources.requests.cpu / memory** | String | NF CPU/memory requests |
| **resources.requests.hugepages** | Quantity | Hugepages-1Gi request (DPDK) |
| **resources.requests.sriovClaims** | List | SR-IOV resources to request |
| **terminationGracePeriodSeconds** | Integer | Grace period before termination (default: 5 s) |
| **securityContext** | Map | NF container security context |
| **nodeSelector** | Map | Node label selector |
| **nodeName** | String | Pin the pod to a node |

Depending on the distribution of your Kubernetes cluster 
`resources.limits.sriovClaims` and multus section needs to be updated will change. 

The pod finds the PCI address of each SR-IOV VF by itself: the SR-IOV device plugin exports `PCIDEVICE_<PREFIX>_<RESOURCE>` (e.g. `PCIDEVICE_OPENSHIFT_IO_RUVFIOU` on OpenShift, `PCIDEVICE_RANCHER_IO_RUVFIOU` on Rancher) and the chart matches it on `sriovResourceName` whatever the prefix is. Only `sriovClaims` must use the prefix of your cluster, e.g. `rancher.io/ruvfiou` on Rancher.

```yaml
- name: "uplane"
  enabled: true
  type: sriov
  mac: "00:11:22:33:44:66"
  #make sure the name is correct
  sriovNetworkNamespace: "openshift-sriov-network-operator"
  #make sure it exists
  sriovResourceName: "ruvfiou"
  vlan: "3"
- name: "cplane"
  enabled: true
  mac: "00:11:22:33:44:67"
  type: sriov
  #make sure the name is correct
  sriovNetworkNamespace: "openshift-sriov-network-operator"
  #make sure it exists
  sriovResourceName: "ruvfioc"
  vlan: "3"
.
.
.
resources:
  define: true
  limits:
    cpu: 14
    memory: 5Gi
    hugepages: 8Gi
    sriovClaims:
      - name: openshift.io/ruvfioc #make sure it exists
        quantity: 1
      - name: openshift.io/ruvfiou #make sure it exists
        quantity: 1
  requests:
    cpu: 14
    memory: 5Gi
    hugepages: 8Gi
    sriovClaims:
      - name: openshift.io/ruvfioc  #make sure it exists
        quantity: 1
      - name: openshift.io/ruvfiou  #make sure it exists
        quantity: 1
```

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

## 📝 Notes & Recommendations

1. **Multus Setup**: Ensure Multus CNI is correctly configured before enabling it in the chart. Avoid invalid gateway settings, as they may break pod connectivity.
2. **Configuration Flexibility**: The default config block exposes limited options for simplicity. For advanced setups, copy your own configuration file into `./config.yaml`.
3. **Performance**:
- Make sure the system is configured as mentioned above
- Facultative: for 4x4 100MHz scenario you would need total 14 isolated CPUs
- facultative: for 2x2 100MHz scenario you would need total 8 isolated CPUs
