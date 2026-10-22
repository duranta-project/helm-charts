#!/bin/bash
# SPDX-License-Identifier: MIT
#
# Runs the CNTi Test Suite certification (cert) for each network function as its own CNF.
#
# Usage: lfn-cnti/runCNTI.sh [nf ...]      (default: all)
#   nf: duranta-oai-gnb duranta-oai-cu duranta-oai-du duranta-oai-nr-ue duranta-oai-cu-cp duranta-oai-cu-up
#       duranta-flexric
#
# Environment (defaults in brackets):
#   CNTI [cnti-testsuite]     path of the cnti-testsuite binary
#   WORK [lfn-cnti/.work]     working directory of the testsuite (its tools and state)
#   CORE_CHART                the oai-5g-basic chart of the OAI core (a directory of the openairinterface/orchestration repository
#                             or an oci:// reference), needed by every NF except duranta-flexric
#
# The CNF under test is installed by the testsuite in namespace oai-cnti. Its peers are test infrastructure,
# installed by this script outside the CNF: the core in oai-core, a CU, CU-CP or gNB in oai-cnti-deps.
# Results: lfn-cnti/<nf>/results/latest.yml. Needs a cluster with containerd (or CRI-O) and two nodes, see README.md.

set -uo pipefail
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then sed -n '4,18p' "$0" | sed 's/^# \?//'; exit 0; fi
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(dirname "$HERE")
CNTI=$(realpath "$(command -v "${CNTI:-cnti-testsuite}")") || { echo "cnti-testsuite not found, set CNTI"; exit 1; }
WORK=${WORK:-$HERE/.work}
CORE_NS=oai-core
DEPS_NS=oai-cnti-deps
AMF=oai-amf.$CORE_NS.svc.cluster.local
NFS=("$@"); [[ ${#NFS[@]} -eq 0 ]] && NFS=(duranta-oai-gnb duranta-oai-cu duranta-oai-du duranta-oai-nr-ue duranta-oai-cu-cp duranta-oai-cu-up duranta-flexric)

core_up() {
  helm status basic -n $CORE_NS &>/dev/null && return
  [[ -n "${CORE_CHART:-}" ]] || { echo "CORE_CHART is not set (oai-5g-basic chart of the core)"; return 1; }
  [[ -d "$CORE_CHART" ]] && helm dependency update "$CORE_CHART" >/dev/null
  helm install basic "$CORE_CHART" -n $CORE_NS --create-namespace --wait --timeout 10m
}
dep_up() {  # release chart [--set ...]
  local r=$1 c=$2; shift 2
  helm install "$r" "$ROOT/charts/$c" -n $DEPS_NS --create-namespace --wait --timeout 10m "$@"
}
deps_down() {
  helm list -n $DEPS_NS -q | xargs -r -n1 helm uninstall -n $DEPS_NS --wait
}

mkdir -p "$WORK" && cd "$WORK" || exit 1
"$CNTI" setup >/dev/null

for nf in "${NFS[@]}"; do
  cfg=$HERE/$nf/cnti-testsuite.yaml
  [[ -f $cfg ]] || { echo "unknown NF $nf"; continue; }
  echo "========== $nf =========="
  # a CU, DU, gNB, CU-CP, CU-UP or UE is one node with its own identity (gNB-DU ID, IMSI...): extra replicas
  # are rejected by the peers instead of sharing the load, so the capacity test does not apply
  skip=(--skip increase_decrease_capacity)
  case $nf in
    duranta-flexric) skip=() ;;
    duranta-oai-gnb|duranta-oai-cu|duranta-oai-cu-cp) core_up || continue ;;
    duranta-oai-du)    core_up && dep_up cu duranta-oai-cu --set config.amfHost=$AMF || continue ;;
    duranta-oai-cu-up) core_up && dep_up cucp duranta-oai-cu-cp --set config.amfHost=$AMF || continue ;;
    duranta-oai-nr-ue) core_up && dep_up gnb duranta-oai-gnb --set config.amfHost=$AMF || continue ;;
  esac
  rm -rf "$HERE/$nf/results" && mkdir -p "$HERE/$nf/results"
  if "$CNTI" cnf_install --cnf-config "$cfg" --timeout 900; then
    "$CNTI" cert "${skip[@]}" --results-dir "$HERE/$nf/results" 2>&1 | grep -v "CNTI-ClusterTools" \
      | sed 's/\x1b\[[0-9;]*m//g' | tee "$HERE/$nf/results/cert.log" | grep -E "PASSED|FAILED|SKIPPED|ERROR|Cert:"
  fi
  "$CNTI" cnf_uninstall --cnf-config "$cfg" >/dev/null
  deps_down
done
helm uninstall basic -n $CORE_NS --wait &>/dev/null

echo "========== Summary =========="
for nf in "${NFS[@]}"; do
  printf '%-16s %s\n' "$nf" "$(grep -h -m1 'Cert:' "$HERE/$nf/results/cert.log" 2>/dev/null || echo 'no result')"
done
