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

| NF | Badge | Essential tests passed | Not passed |
|----|-------|------------------------|------------|
| `duranta-oai-gnb` | [![CNTi essential](https://github.com/duranta-project/helm-charts/raw/badges/duranta-oai-gnb/cnti-badge.svg)](https://github.com/duranta-project/helm-charts/actions/workflows/cnti.yml) | 18 of 19 | `non_root_containers` |
| `duranta-oai-cu` | [![CNTi essential](https://github.com/duranta-project/helm-charts/raw/badges/duranta-oai-cu/cnti-badge.svg)](https://github.com/duranta-project/helm-charts/actions/workflows/cnti.yml) | 18 of 19 | `non_root_containers` |
| `duranta-oai-du` | [![CNTi essential](https://github.com/duranta-project/helm-charts/raw/badges/duranta-oai-du/cnti-badge.svg)](https://github.com/duranta-project/helm-charts/actions/workflows/cnti.yml) | 18 of 19 | `non_root_containers` |
| `duranta-oai-nr-ue` | [![CNTi essential](https://github.com/duranta-project/helm-charts/raw/badges/duranta-oai-nr-ue/cnti-badge.svg)](https://github.com/duranta-project/helm-charts/actions/workflows/cnti.yml) | 18 of 19 | `non_root_containers` |
| `duranta-oai-cu-cp` | [![CNTi essential](https://github.com/duranta-project/helm-charts/raw/badges/duranta-oai-cu-cp/cnti-badge.svg)](https://github.com/duranta-project/helm-charts/actions/workflows/cnti.yml) | 18 of 19 | `non_root_containers` |
| `duranta-oai-cu-up` | [![CNTi essential](https://github.com/duranta-project/helm-charts/raw/badges/duranta-oai-cu-up/cnti-badge.svg)](https://github.com/duranta-project/helm-charts/actions/workflows/cnti.yml) | 18 of 19 | `non_root_containers` |
| `duranta-flexric` | [![CNTi essential](https://github.com/duranta-project/helm-charts/raw/badges/duranta-flexric/cnti-badge.svg)](https://github.com/duranta-project/helm-charts/actions/workflows/cnti.yml) | 17 of 19 | `non_root_containers`, `specialized_init_system` |

The badges show the latest nightly run of the CNTi job (below) on `main`. The scores are from the job's run on a fork, 7 Nov 2026:
CNTi Test Suite v2.4.1 on a kind cluster with a control plane and two workers (threshold: 15 of 19). A test listed in
`<nf>/expected.yaml` is a known result: when any result changes, the job says so in its summary and as a warning.

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

## In CI

`.github/workflows/cnti.yml` runs the same steps every night, on demand and on pull requests that change a chart, this
directory or the job, with [testsuite-action](https://github.com/lfn-cnti/testsuite-action): one job per NF, each on
its own kind cluster (`kind.yaml`) on a GitHub-hosted runner. It runs all 19 essential tests, without the script's
`--skip`: `increase_decrease_capacity` passes there for every RAN NF, which is why the table shows 18 of 19. Runs on
`main` publish one badge per NF to the `badges` branch; pull requests publish nothing. Two settings are for GitHub's
runners only, and change neither the CNF under test nor its values:

- The runner's AppArmor profile for `/usr/sbin/mysqld` is unloaded before the OAI core is installed. GitHub's Ubuntu
  images ship MySQL with that profile; kind's nodes run unconfined, so it attaches to the core's MySQL container by
  path and denies it its own files, and MySQL never gets Ready. A cluster outside GitHub's runners needs nothing.
- The NR-UE's gNB peer is installed without `SYS_NICE`. In rfsim mode a real-time gNB and a real-time UE leave the
  runner's four cores no time for the cluster's API server. The UE under test keeps its defaults.

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
| `sig_term_handled` (intermittent) | `nr-softmodem` and `nr-uesoftmodem` fork a helper (`start_background_system`) that tini, without `-g`, does not signal: it exits when the main process does, and when tini exits first the kernel kills it with SIGKILL | the main process waiting for its helper before it exits (OAI), or tini signalling the whole process group (`-g`, or `TINI_KILL_PROCESS_GROUP=1`) |
| `specialized_init_system` (FlexRIC) | no init (tini) in the FlexRIC image (the gNB, CU, DU, CU-UP and NR-UE images have one) | tini in the FlexRIC image |
