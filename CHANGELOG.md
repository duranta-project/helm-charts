<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# RELEASE NOTES: #

## v3.0.0 -- October 2026

Charts version `3.0.0`.

* **New repository**: the RAN and RIC charts moved from the OAI helm-charts repository to
  [duranta-project/helm-charts](https://github.com/duranta-project/helm-charts); the OAI 5G core charts (version
  `2.2.2`) are in [openairinterface/orchestration](https://github.com/openairinterface/orchestration); the end-to-end
  scenario charts are maintained separately
* Charts are in `charts/` and every chart folder has the name of its chart
* Renamed to `duranta-*`, with the Duranta icon and [duranta-project/openairinterface5g](https://github.com/duranta-project/openairinterface5g) as source:
	- `oai-gnb` -> `duranta-oai-gnb`, `oai-cu` -> `duranta-oai-cu`, `oai-du` -> `duranta-oai-du`,
	  `oai-cu-cp` -> `duranta-oai-cu-cp`, `oai-cu-up` -> `duranta-oai-cu-up`, `oai-nr-ue` -> `duranta-oai-nr-ue`
	- `oai-gnb-fhi-72` -> `duranta-oai-gnb-fhi72`, `oai-du-fhi-72` -> `duranta-oai-du-fhi72`
* Renamed to `duranta-*`, with the Duranta icon and [duranta-project/openairinterface5g](https://github.com/duranta-project/flexric) as source:
	- `oai-flexric` -> `duranta-flexric`
* New chart `duranta-xapp`: one chart for the FlexRIC xApps (`kpm`, `rc`, `kpm-rc`, `gtp-mac-rlc-pdcp`), selected with
  `xapp`; optional SQLite database for Grafana, OpenShift SCC
* `duranta-flexric`: optional PVC shared with the xApps and Grafana (`xappDb`), E2 interface and tcpdump fixes,
  probes; Grafana values for the FlexRIC "KPI measurements" dashboard in `charts/duranta-xapp/grafana/`
* E2 agent: service model directory set, `ricHost` defaults to `duranta-flexric`, the gNB resolves the RIC (not the AMF)
* Interface names (`f1cIfName`, `n2IfName`, ...) can be overridden in the CU, CU-CP, CU-UP, DU and gNB charts, also
  to share one Multus interface between several 3GPP interfaces
* Multus: NADs rendered only for interfaces with `enabled: true`, `type` (macvlan/vlan) honoured, missing `enabled`
  flags added
* FHI 7.2 charts: the SR-IOV `PCI_LIST` prefix is detected automatically (OpenShift and Rancher)
* CU-UP: tcpdump sidecar indentation fixed; CU-CP: container `securityContext` taken from the values instead of a
  hard-coded `privileged: true`; NR-UE: `hostIPC` moved to the pod spec (vrtsim)
* CNTi Test Suite readiness:
	- CPU/memory limits enabled by default (`resources.define: true`), sized from measured usage
	- liveness and readiness probes in every chart
	- NR-UE no longer privileged and without hostPath: `/dev/net/tun` is created by an init container (`MKNOD`) in
	  an `emptyDir`; `tini` kept as PID 1
	- FlexRIC with `shareProcessNamespace`
* CNTi Test Suite (`cert`, 19 essential tests, 15 required) results in `lfn-cnti/`, each network function tested as
  its own CNF (`lfn-cnti/runCNTI.sh`): gNB, CU, DU, CU-UP and FlexRIC 17/19, NR-UE and CU-CP 16/19, all PASSED
* `ci-scripts/runE2ETests.py`: end-to-end test (core, FlexRIC, xApps, Grafana, `gnb`, `f1` and `e1-f1` scenarios with
  an NR-UE, with or without multus, on minikube, Kubernetes or OpenShift). The same script is in both repositories:
  it takes the charts of this repository and clones the OAI 5G core charts (`charts` in
  `ci-scripts/e2e-config.yaml`), or uses a local folder or another git repository and branch
* `ci-scripts`: `publishCharts.sh` (OCI registry), `checkHelmChartSyntax.sh` and `create-cluster.sh` with `--help`;
  `create-cluster.sh` takes `NODES`, `CONTAINER_RUNTIME`, `CPUS` and `MEMORY`
* Apache-2.0 for the CNTi Test Suite configuration files (`LICENSES/preferred/Apache-2.0.txt`, `NOTICE`)

## v1.0.1 -- March 2026

* Re-license the helm-charts in MIT license
* Configuration files for NF in CSSL v1.0
* Documentation licensed in CC-BY-4.0

## v1.0.0 -- December 2025 ##

* Migrate helm-charts from `oai-cn5g-fed` repository
* Release helm-charts for OAI-gNB/DU for 7.2 radio units
* Release helm-chart for FlexRIC
* Future work:
	- Helm-chart template for xAPPs
	- Helm-chart for raytracing-channel-emulator
	- Add vrtsim radio in gNB/DU and NR-UE helm-charts
