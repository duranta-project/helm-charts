<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Helm Charts for the Duranta RAN and FlexRIC

This repository provides Helm charts for deploying the [Duranta](https://github.com/duranta-project) OpenAirInterface RAN network functions
([openairinterface5g](https://github.com/duranta-project/openairinterface5g)), the FlexRIC near-RT RIC and xApps, in Kubernetes or OpenShift.
The OAI 5G core charts are maintained in [openairinterface/orchestration](https://github.com/openairinterface/orchestration).

To verify chart rendering syntax locally, run `./ci-scripts/checkHelmChartSyntax.sh`.

To run the end-to-end tests (core network, FlexRIC, xApps, monolithic gNB, F1 split and E1/F1 split, each with an
NR-UE), with or without multus, on minikube, an existing Kubernetes cluster or OpenShift, run
`./ci-scripts/runE2ETests.py`. It uses the charts of this repository and the OAI 5G core charts from [openairinterface/orchestration](https://github.com/openairinterface/orchestration) (cloned, or from a local folder or
another branch); see [`ci-scripts/README.md`](./ci-scripts/README.md) and `./ci-scripts/runE2ETests.py --help`.

To package all charts and push them to an OCI registry, run `./ci-scripts/publishCharts.sh oci://<registry>/<namespace>` (`--package-only` builds the packages into `dist/` without pushing; see the script header for login options). The charts are published as `duranta-*` with version `3.0.0`.

The [CNTi Test Suite](https://github.com/lfn-cnti/testsuite) certification of the charts, how to run it and the
results are in [`lfn-cnti/`](./lfn-cnti/README.md).

## RAN Network Functions
- [Duranta-OAI-CU](./charts/duranta-oai-cu/README.md)
- [Duranta-OAI-CU-CP](./charts/duranta-oai-cu-cp/README.md)
- [Duranta-OAI-CU-UP](./charts/duranta-oai-cu-up/README.md)
- [Duranta-OAI-DU](./charts/duranta-oai-du/README.md)
- [Duranta-OAI-gNB](./charts/duranta-oai-gnb/README.md)
- [Duranta-OAI-NR-UE](./charts/duranta-oai-nr-ue/README.md)
- [Duranta-OAI-gNB-FHI72](./charts/duranta-oai-gnb-fhi72/README.md)
- [Duranta-OAI-DU-FHI72](./charts/duranta-oai-du-fhi72/README.md)

## RIC
- [Duranta-FlexRIC](./charts/duranta-flexric/README.md) (near-RT RIC)
- [Duranta-xApp](./charts/duranta-xapp/README.md) (KPM, RC, KPM+RC and GTP/MAC/RLC/PDCP monitoring xApps)

## Tested Environment

- Kubernetes v1.31+
- Openshift: 4.17+
- Helm: v3.14+

## Future release

- vrtsim as radio for gNB and nr-ue
- raytracer helm-charts

# License

- The charts and ci-scripts are licensed under the [MIT License](./LICENSE).
- Network function configuration is licensed under [CSSL v1.0](./LICENSES/preferred/CSSL-v1.0.txt).
- Documentation is licensed under [CC-BY-4.0](./LICENSES/preferred/CC-BY-4.0.txt).

For third party libraries and helm-charts check the [NOTICE](./NOTICE) file.

# Contribute

Please check [CONTRIBUTING.md](./CONTRIBUTING.md)
