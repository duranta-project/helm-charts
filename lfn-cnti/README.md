<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# CNTi Test Suite

Certification of the charts with the [CNTi Test Suite](https://github.com/lfn-cnti/testsuite) (`cert`, the 19
essential tests; a CNF is certified when at least 15 pass). Every network function is tested as its own CNF:

| Folder | CNF under test (namespace `oai-cnti`) | Peers, installed outside the CNF |
|--------|----------------------------------------|----------------------------------|
| [`duranta-oai-gnb`](./duranta-oai-gnb) | `duranta-oai-gnb` | OAI core (`oai-core`, from `CORE_CHART`) |
| [`duranta-oai-cu`](./duranta-oai-cu) | `duranta-oai-cu` | core |
| [`duranta-oai-du`](./duranta-oai-du) | `duranta-oai-du` | core, CU (`oai-cnti-deps`) |
| [`duranta-oai-nr-ue`](./duranta-oai-nr-ue) | `duranta-oai-nr-ue` | core, gNB (`oai-cnti-deps`) |
| [`duranta-oai-cu-cp`](./duranta-oai-cu-cp) | `duranta-oai-cu-cp` | core |
| [`duranta-oai-cu-up`](./duranta-oai-cu-up) | `duranta-oai-cu-up` | core, CU-CP (`oai-cnti-deps`) |
| [`duranta-flexric`](./duranta-flexric) | `duranta-flexric` | none |

Each folder has the `cnti-testsuite.yaml` and, after a run, `results/` (`latest.yml`, the testsuite's result
file, and `cert.log`, its output).

## Results

| NF | Result | Essential tests passed | Not passed |
|----|--------|------------------------|------------|
| `duranta-oai-gnb` | **PASSED** | 17 of 19 | `non_root_containers`, `increase_decrease_capacity` (skipped) |
| `duranta-oai-cu` | **PASSED** | 17 of 19 | `non_root_containers`, `increase_decrease_capacity` (skipped) |
| `duranta-oai-du` | **PASSED** | 17 of 19 | `non_root_containers`, `increase_decrease_capacity` (skipped) |
| `duranta-oai-nr-ue` | **PASSED** | 16 of 19 | `non_root_containers`, `sig_term_handled`, `increase_decrease_capacity` (skipped) |
| `duranta-oai-cu-cp` | **PASSED** | 16 of 19 | `non_root_containers`, `sig_term_handled`, `increase_decrease_capacity` (skipped) |
| `duranta-oai-cu-up` | **PASSED** | 17 of 19 | `non_root_containers`, `increase_decrease_capacity` (skipped) |
| `duranta-flexric` | **PASSED** | 17 of 19 | `non_root_containers`, `specialized_init_system` |

CNTi Test Suite v2.3.0, minikube with 2 nodes and containerd (threshold: 15 of 19).

## Running

The microservice tests read the container processes on the nodes (containerd or CRI-O, not the Docker runtime)
and `node_drain` needs two nodes:

```bash
NODES=2 MEMORY=8G CONTAINER_RUNTIME=containerd ./ci-scripts/create-cluster.sh
minikube addons disable storage-provisioner   # a pod without controller: node_drain cannot drain its node
export CNTI=/path/to/cnti-testsuite
export CORE_CHART=/path/to/orchestration/charts/oai-5g-basic   # the OAI core (openairinterface/orchestration), peer of the RAN NFs
./lfn-cnti/runCNTI.sh                                  # all NFs
./lfn-cnti/runCNTI.sh duranta-oai-du duranta-oai-cu    # some of them
```

For each NF the script installs its peers, installs the CNF with `cnf_install`, runs `cert`, stores the results
and removes everything. `increase_decrease_capacity` is skipped for the RAN NFs (`--skip`): a gNB, CU, DU, CU-CP,
CU-UP or UE is one node with its own identity (gNB-DU ID, IMSI), extra replicas are rejected by the peers (e.g.
F1 Setup Failure) instead of sharing the load. A skipped test does not count as passed.

## What the charts do for it

- CPU/memory limits (`resources.define: true`) and liveness/readiness probes on every container.
- No privileged container and no hostPath: `/dev/net/tun` (NR-UE) is created by an init container with `MKNOD`
  in an `emptyDir`.
- Pinned image tags.
- `shareProcessNamespace` in FlexRIC: the pause process reaps zombies and the RIC is not PID 1. The RAN images use
  `tini` (the NR-UE chart keeps it as PID 1 in its own command).
- The literal IPs left in the rendered configuration (template placeholders replaced at start, demo data) are
  listed under `hardcoded_ip_exceptions`.

## Not handled by the charts

| Test | Why | Needs |
|------|-----|-------|
| `non_root_containers` | the OAI images run as root | non-root images (file capabilities on the binaries, writable config directory) |
| `sig_term_handled` (NR-UE, CU-CP) | `nr-uesoftmodem` and the CU-CP `nr-softmodem` do not stop on SIGTERM | clean SIGTERM shutdown in OAI |
| `specialized_init_system` (FlexRIC) | no init (tini) in the FlexRIC image (the gNB, CU, DU, CU-UP and NR-UE images have one) | tini in the FlexRIC image |
