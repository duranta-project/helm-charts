#!/bin/bash
# SPDX-License-Identifier: MIT
#
# Package every helm chart in the repo and push it to an OCI registry.
#
#   ./ci-scripts/publishCharts.sh oci://docker.io/<namespace>    # package + push
#   ./ci-scripts/publishCharts.sh --package-only                 # package only, into dist/
#
# Login: run `helm registry login <host>` beforehand, or export
# HELM_REGISTRY_USER and HELM_REGISTRY_PASSWORD and the script logs in for you.
# DIST_DIR overrides the output directory (default: <repo>/dist, git-ignored).
# HELM_PUSH_ARGS adds flags to helm push, e.g. "--plain-http" or "--insecure-skip-tls-verify".

set -euo pipefail

usage() { echo "usage: $0 oci://<registry>/<namespace> | --package-only"; exit 1; }
[[ $# -eq 1 ]] || usage
registry="$1"
if [[ "$registry" != "--package-only" && "$registry" != oci://* ]]; then usage; fi

command -v helm >/dev/null 2>&1 || { echo "helm is not installed, install it from --> https://helm.sh/docs/intro/install/"; exit 1; }

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dist="${DIST_DIR:-$repo_root/dist}"
rm -rf "$dist" && mkdir -p "$dist"

mapfile -t charts < <(find "$repo_root/charts" \
  -name Chart.yaml -not -path "$repo_root/*/charts/*" -print | sort | xargs -r -n1 dirname)
[[ ${#charts[@]} -gt 0 ]] || { echo "No charts found"; exit 1; }

# an OCI ref is <registry>/<name>:<version>, two charts with the same pair would overwrite each other
dups=$(for c in "${charts[@]}"; do
  echo "$(sed -n 's/^name: *//p' "$c/Chart.yaml"):$(sed -n 's/^version: *//p' "$c/Chart.yaml") ${c#"$repo_root"/}"
done | sort | awk '{n[$1]++; p[$1]=p[$1]" "$2} END {for (k in n) if (n[k] > 1) print k " ->" p[k]}')
if [[ -n "$dups" ]]; then
  echo "ERROR: duplicate chart name:version, rename or bump one of them:"
  echo "$dups"
  exit 1
fi

for chart in "${charts[@]}"; do
  echo "==> ${chart#"$repo_root"/}"
  if grep -q '^dependencies:' "$chart/Chart.yaml"; then
    helm dependency update "$chart" >/dev/null
  fi
  helm package "$chart" -d "$dist" >/dev/null
done
echo "Packaged ${#charts[@]} charts into $dist"

[[ "$registry" == "--package-only" ]] && exit 0

if [[ -n "${HELM_REGISTRY_USER:-}" && -n "${HELM_REGISTRY_PASSWORD:-}" ]]; then
  host="${registry#oci://}"; host="${host%%/*}"
  echo "$HELM_REGISTRY_PASSWORD" | helm registry login "$host" --username "$HELM_REGISTRY_USER" --password-stdin
fi

for pkg in "$dist"/*.tgz; do
  helm push "$pkg" "$registry" ${HELM_PUSH_ARGS:-}
done
echo "Pushed ${#charts[@]} charts to $registry"
