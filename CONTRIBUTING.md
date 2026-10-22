<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Contributing

Thanks for contributing to the Duranta RAN and FlexRIC Helm charts repository.

This repository contains Helm charts for the Duranta OAI RAN network functions, FlexRIC and xApps. 
Contributions should keep charts deployable, documentation aligned with behavior, and changes scoped to the affected charts.

## Repository Layout

- `charts/`: Helm charts for the Duranta OAI RAN network functions, FlexRIC and xApps.
- `lfn-cnti/`: CNTi Test Suite configurations and results of every network function.
- `ci-scripts/`: Local and CI validation scripts.

Each chart generally contains:

- `Chart.yaml`: chart metadata and version.
- `values.yaml`: deployment and infrastructure settings.
- `config.yaml`: functional application configuration.
- `templates/`: rendered Kubernetes resources.
- `README.md`: chart-specific usage and configuration notes.

## Development Expectations

- Keep changes focused. If you modify one chart, avoid unrelated edits in other charts.
- Update `README.md` when configuration, behavior, prerequisites, or examples change.
- Update `Chart.yaml` when the chart content changes and a new chart release is intended.
- Preserve the existing separation between `values.yaml` and `config.yaml`:
  - `values.yaml` for deployment, image, and infrastructure parameters.
  - `config.yaml` for network-function runtime configuration.
- Follow the existing templating style and naming conventions already used in the chart you are editing.

## Local Validation

Before submitting a change, run the local syntax check from the repository root:

```bash
./ci-scripts/checkHelmChartSyntax.sh
```

This script renders every chart under `charts/`.

If your change affects deployment behavior, also validate it in an environment you control with the end-to-end test
`./ci-scripts/runE2ETests.py` (python3 with PyYAML, git, helm and kubectl). It deploys the OAI 5G core and FlexRIC,
then the `gnb`, `f1` and `e1-f1` scenarios, each with an NR-UE over the RF simulator and the FlexRIC xApps, and checks
the signalling, the UE PDU session and traffic, and the xApp data. It takes the charts of this repository and
the OAI 5G core charts from [openairinterface/orchestration](https://github.com/openairinterface/orchestration); to test a change that spans both repositories point it at your other checkout or branch
(`--core-path`/`--core-git`/`--core-branch`, `--ran-path`/`--ran-git`/`--ran-branch`). Run it both without and with
`--multus` when your change touches networking; see [`ci-scripts/README.md`](./ci-scripts/README.md). Test on OpenShift when the change is specific to OpenShift (security
context constraints, SCC or RBAC behavior, `kubernetesDistribution=Openshift`). If you don't have OpenShift then no
issues, please mention it in the merge request.

When a change touches security contexts, probes, resources, volumes or the container command, rerun the CNTi Test
Suite certification of the affected charts (`./lfn-cnti/runCNTI.sh`, see [`lfn-cnti/README.md`](./lfn-cnti/README.md))
and update the results.

## Documentation

- Keep top-level and chart-level documentation consistent with the implemented behavior.
- Use concrete install or upgrade examples when adding new options.
- If you add, rename, or remove values, document them in the affected chart `README.md`.

## Versioning and Release Notes

- Chart versions are declared in each chart `Chart.yaml`.
- Repository-wide release notes are tracked in `CHANGELOG.md`.
- If your contribution is intended for a release, make sure the relevant version and release notes are updated as part of the same change.

## License and Headers

This repository is MIT licensed. Keep existing SPDX headers intact and use the current conventions:

- CI-scripts and YAML files typically use `SPDX-License-Identifier: MIT`.
- Markdown documentation typically uses `SPDX-License-Identifier: CC-BY-4.0`.
- CNTi Test Suite configuration files (`lfn-cnti/*/cnti-testsuite.yaml`) use `SPDX-License-Identifier: Apache-2.0`, as required by the CNTi project.
- Network function configuration files use `SPDX-License-Identifier: LicenseRef-CSSL-1.0`

For third party libraries and helm-chart check the [NOTICE](./NOTICE) file.

When adding new files, match the header style already used by similar files in the repository.

## Merge Requests

- Describe the problem the change solves.
- Summarize which charts or scenarios are affected.
- List the validation you ran locally.
- Include any required manual steps, prerequisites, or migration notes.

Small, well-scoped merge requests are easier to review and merge than large mixed changes.
