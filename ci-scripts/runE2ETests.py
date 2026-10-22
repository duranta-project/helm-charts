#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""End-to-end test of the OAI 5G core charts (openairinterface/orchestration) and the Duranta RAN and FlexRIC charts
(duranta-project/helm-charts) on Kubernetes (minikube or an existing cluster) or OpenShift, with or without multus.

The same script is in both repositories. Each set of charts comes from a local folder (e.g. this repository) or is
cloned from a git repository and branch: "charts" in the settings file, --core-path/--core-git/--core-branch and
--ran-path/--ran-git/--ran-branch on the command line.

The core network (oai-5g-basic) is deployed first and checked (all NFs ready, SMF-UPF PFCP association,
NRF registrations), followed by the FlexRIC near-RT RIC and optionally Grafana. Each selected scenario then
  1. installs its RAN charts with the E2 agent enabled and checks NG/F1/E1 setup and the E2 setup with the RIC,
  2. deploys the xApps of the FlexRIC CI with the duranta-xapp chart (KPM, RC, KPM+RC, GTP/MAC/RLC/PDCP monitoring),
  3. attaches an NR-UE over the RF simulator (PDU session, ping to the UPF) and checks that every xApp receives
     the UE's data (and, with Grafana, that the dashboard shows it),
  4. detaches the UE (deregistration) and uninstalls what it installed.
Scenarios:

  gnb      monolithic gNB + NR-UE
  f1       CU + DU + NR-UE
  e1-f1    CU-CP + CU-UP + DU + NR-UE

Settings come from a YAML file (see ci-scripts/e2e-config.yaml); command line options override it.
Needs python3 with PyYAML, helm and kubectl (plus git to clone charts, minikube and docker when the script creates the
cluster).
Exit code 0 means every check passed. On exit the releases and the namespace are removed, and a minikube
cluster created by the script is deleted. With --keep, everything stays and the last scenario is left running
(RAN, UE, xApps and Grafana), so the script also deploys a complete setup for manual use.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENARIOS = ["gnb", "f1", "e1-f1"]
DEFAULTS = {
    "cluster": {"type": "kubernetes", "create": "minikube", "context": "", "deleteAfter": True},
    "namespace": "oai-e2e",
    "multus": False,
    "flexric": True,
    "grafana": False,
    "valuesDir": "ci-scripts/values",
    "scenarios": SCENARIOS,
    "timeout": 600,
    "checkTimeout": 180,
    "images": {"coreTag": "", "ranTag": "", "flexricTag": "", "charts": {}},
    # where the charts come from: "path" (a local repository, relative to this repository or absolute) or, when path
    # is empty, "git" + "branch" (cloned for the run). Both repositories keep their charts in charts/.
    "charts": {
        "core": {"path": "", "git": "https://github.com/openairinterface/orchestration.git", "branch": "main"},
        "ran": {"path": "", "git": "https://github.com/duranta-project/helm-charts.git", "branch": "main"},
    },
}
CORE_NFS = ["oai-nrf", "oai-udr", "oai-udm", "oai-ausf", "oai-amf", "oai-smf", "oai-upf", "oai-lmf"]  # subcharts of oai-5g-basic
CORE_READY = ["basic-mysql", "oai-nrf", "oai-udr", "oai-udm", "oai-ausf", "oai-amf", "oai-smf", "oai-upf"]
# charts installed with config.enableE2. Not duranta-oai-cu-up: nr-cuup (2026.w40/develop) blocks in initialize_agent()
# reading its E1 context and never starts the E2 agent, so only the CU-CP and DU of the E1/F1 split connect to the RIC.
RAN_E2 = {"duranta-oai-gnb", "duranta-oai-cu", "duranta-oai-cu-cp", "duranta-oai-du"}
# charts with an N2 link: installed with global.waitForAMF so an init container waits until the AMF accepts SCTP
# (the OAI gNB/CU send their single NG setup attempt at start and do not retry when it is refused)
RAN_N2 = {"duranta-oai-gnb", "duranta-oai-cu", "duranta-oai-cu-cp"}
# xApps of the FlexRIC CI scenario (duranta-xapp chart, one release each): the log lines that show each one works and
# whether they must appear after the UE attached (UE data) or anywhere in the log (kpm-rc sends its RC control once,
# when it starts, so its acknowledgement can come before the UE)
XAPPS = [
    ("kpm", ["DRB.UEThpDl"], "per-UE KPM measurements", True),
    ("rc", ["<measurementReport>"], "RRC measurement reports (RC)", True),
    ("kpm-rc", ["Successfully received CONTROL response"], "RC control acknowledged", False),
    ("gtp-mac-rlc-pdcp", ["MAC ind_msg", "RLC ind_msg", "PDCP ind_msg", "GTP ind_msg"], "MAC/RLC/PDCP/GTP indications", True),
]
# E1/F1 split: the RC control of kpm-rc (QoS flow mapping) is handled by the CU-UP, which cannot connect to the RIC
# (OAI nr-cuup bug: read_setup_ran() waits for NGAP/F1AP setups a CU-UP never has, see RAN_E2), so only its KPM part
# PDCP and GTP run in the CU-UP as well, so gtp-mac-rlc-pdcp only gets the DU's MAC and RLC statistics
XAPPS_E1_OVERRIDE = {
    "kpm-rc": (["DRB.UEThpDl"], "per-UE KPM measurements (RC control needs CU-UP E2)", True),
    "gtp-mac-rlc-pdcp": (["MAC ind_msg", "RLC ind_msg"], "MAC/RLC indications (PDCP/GTP need CU-UP E2)", True),
}
GRAFANA_DASHBOARD_UID = "cdtipm2on2f40e"  # FlexRIC "KPI measurements"


class CheckFailed(Exception):
    pass


def log(msg):
    print(f"---------- {msg} ----------", flush=True)


class Run:
    def __init__(self, cfg):
        self.cfg = cfg
        self.ns = cfg["namespace"]
        self.timeout = int(cfg["timeout"])  # install / pod ready
        self.check_timeout = int(cfg["checkTimeout"])  # log, E2, xApp and UE checks
        self.multus = bool(cfg["multus"])
        self.flexric = bool(cfg["flexric"])
        self.grafana = bool(cfg["grafana"]) and self.flexric
        self.keep_last = False  # --keep: leave the last scenario deployed
        self.openshift = cfg["cluster"]["type"] == "openshift"
        self.context = cfg["cluster"]["context"]
        self.images = cfg["images"]
        self.created_minikube = False
        self.watch = []  # pod labels whose logs are printed on failure
        self.tmp = []  # clones removed at the end
        self.roots = {}  # "core"/"ran" -> repository root with charts/

    # ---- chart sources ---------------------------------------------------------------------------------
    def fetch_charts(self):
        """Resolve each set of charts to a local repository: the configured path, or a clone of git + branch."""
        for kind, src in self.cfg["charts"].items():
            if src.get("path"):
                root = os.path.join(REPO, src["path"])
                log(f"{kind} charts: {os.path.abspath(root)}")
            else:
                root = tempfile.mkdtemp(prefix=f"e2e-{kind}-")
                self.tmp.append(root)
                log(f"{kind} charts: cloning {src['git']} (branch {src['branch']})")
                self.sh(["git", "clone", "-q", "--depth", "1", "-b", src["branch"], src["git"], root], capture=True)
            if not os.path.isdir(os.path.join(root, "charts")):
                raise CheckFailed(f"{kind} charts: no charts/ folder in {src.get('path') or src['git'] + ' ' + src['branch']}")
            self.roots[kind] = os.path.abspath(root)

    def chart(self, kind, name):
        return os.path.join(self.roots[kind], "charts", name)

    # ---- command helpers -------------------------------------------------------------------------------
    def sh(self, cmd, check=True, capture=False):
        try:
            r = subprocess.run(cmd, cwd=REPO, text=True, stdout=subprocess.PIPE if capture else None,
                               stderr=subprocess.STDOUT if capture else None)
        except OSError as e:
            raise CheckFailed(f"cannot run {cmd[0]}: {e}")
        if check and r.returncode != 0:
            raise CheckFailed(f"command failed ({r.returncode}): {' '.join(cmd)}" + (f"\n{r.stdout}" if capture else ""))
        return r

    def ctx(self, flag):
        return [flag, self.context] if self.context else []

    def kubectl(self, *args, **kw):
        return self.sh(["kubectl", *self.ctx("--context"), "-n", self.ns, *args], **kw)

    def helm(self, *args, **kw):
        return self.sh(["helm", *self.ctx("--kube-context"), "-n", self.ns, *args], **kw)

    def values(self, name):
        return os.path.join(REPO, self.cfg["valuesDir"], name)

    @staticmethod
    def selector(label):
        """A chart name selects app.kubernetes.io/name=<label>; a label containing "=" is used as the selector."""
        return label if "=" in label else f"app.kubernetes.io/name={label}"

    def pod(self, label):
        r = self.kubectl("get", "pods", "-l", self.selector(label),
                         "-o", "jsonpath={.items[0].metadata.name}", check=False, capture=True)
        return r.stdout.strip() if r.returncode == 0 else ""

    def logs(self, label, since=None):
        p = self.pod(label)
        if not p:
            return ""
        r = self.kubectl("logs", p, *([f"--since-time={since}"] if since else []), check=False, capture=True)
        return r.stdout if r.returncode == 0 else ""

    @staticmethod
    def now():
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # ---- image overrides -------------------------------------------------------------------------------
    def image_sets(self, chart, kind, prefix=""):
        """--set-string flags for nfimage of chart: the tag of its kind (core/ran/flexric), then images.charts.<chart>."""
        img = {"tag": self.images.get(f"{kind}Tag") or ""}
        img.update({k: v for k, v in ((self.images.get("charts") or {}).get(chart) or {}).items() if v})
        sets = [f"{prefix}nfimage.version={img['tag']}"] if img.get("tag") else []
        sets += [f"{prefix}nfimage.repository={img['repository']}"] if img.get("repository") else []
        return ["--set-string", ",".join(sets)] if sets else []

    # ---- building blocks -------------------------------------------------------------------------------
    def install(self, release, chart, label, multus_file=None, extra=()):
        name = os.path.basename(chart)
        args = ["install", release, chart, "--wait", "--timeout", f"{self.timeout}s"]
        if self.multus and multus_file:
            args += ["-f", self.values(multus_file)]
        if self.openshift:
            args += ["--set", "kubernetesDistribution=Openshift,global.kubernetesDistribution=Openshift"]
        if name in RAN_E2 and self.flexric:
            args += ["--set", "config.enableE2=true"]
        if name in RAN_N2:
            args += ["--set", "global.waitForAMF=true"]
        if name.startswith("oai-5g-"):
            for nf in CORE_NFS:
                args += self.image_sets(nf, "core", f"{nf}.")
        else:
            args += self.image_sets(name, "flexric" if name in ("duranta-flexric", "duranta-xapp") else "ran")
        log(f"Installing {release} ({chart}{', multus' if self.multus and multus_file else ''})")
        self.watch.append(label)
        self.helm(*args, *extra)
        self.kubectl("wait", "--for=condition=ready", "pod", "-l", self.selector(label),
                     f"--timeout={self.timeout}s")
        log(f"{label}: Ready")
        if self.multus:
            self.check_unique_ips()

    def check_unique_ips(self):
        """Two pods with the same multus IP on one network answer each other's ARP: traffic goes to a random one."""
        r = self.kubectl("get", "pods", "-o", "json", check=False, capture=True)
        seen = {}
        for p in (yaml.safe_load(r.stdout) or {}).get("items", []) if r.returncode == 0 else []:
            status = p["metadata"].get("annotations", {}).get("k8s.v1.cni.cncf.io/network-status", "[]")
            for net in yaml.safe_load(status) or []:
                if net.get("interface") in (None, "eth0"):
                    continue
                for ip in net.get("ips") or []:
                    seen.setdefault(ip, []).append(f"{p['metadata']['name']}/{net['interface']}")
        dup = {ip: who for ip, who in seen.items() if len(who) > 1}
        if dup:
            raise CheckFailed(f"duplicate multus IP address(es): {dup}")

    def uninstall(self, release, label):
        self.helm("uninstall", release, "--wait", check=False)
        # wait until the pods are gone, so the next scenario can reuse the multus addresses
        self.kubectl("wait", "--for=delete", "pod", "-l", self.selector(label),
                     f"--timeout={self.timeout}s", check=False)
        if label in self.watch:
            self.watch.remove(label)

    def expect_log(self, label, text, what, since=None, count=1, timeout=None):
        """Poll the pod log until it contains text (plain substring) at least count times."""
        deadline = time.time() + (timeout or self.check_timeout)
        while time.time() < deadline:
            if self.logs(label, since).count(text) >= count:
                log(f"{what}: OK")
                return
            time.sleep(5)
        raise CheckFailed(f"{what}: '{text}' found less than {count} time(s) in the {label} log")

    def e2_test(self, nodes, since):
        """Every RAN function of the scenario sent its E2 setup to the RIC."""
        if self.flexric:
            self.expect_log("duranta-flexric", "E2 SETUP-REQUEST rx", f"E2 setup of {nodes} RAN function(s) (FlexRIC)",
                            since=since, count=nodes)

    def xapps_install(self):
        """All xApps at once, each with its own E2 multus address; with Grafana they write into the shared PVC."""
        if not self.flexric:
            return
        base = yaml.safe_load(open(self.values("duranta-xapp-multus.yaml"))) if self.multus else {}
        for i, (xapp, _, _, _) in enumerate(XAPPS):
            extra = ["--set", f"xapp={xapp}"]
            if self.multus:
                itfs = base["multus"]["interfaces"]
                ip = itfs[0]["ipAdd"].rsplit(".", 1)
                itfs = [dict(itfs[0], ipAdd=f"{ip[0]}.{int(ip[1]) + i}")] + itfs[1:]
                extra += ["--set-json", f"multus.interfaces={json.dumps(itfs)}"]
            if self.grafana:
                extra += ["--set", "db.enabled=true"] + (["--set", "db.name=xapp_db"] if xapp == "kpm" else [])
            self.install(f"xapp-{xapp}", self.chart("ran", "duranta-xapp"), f"app.kubernetes.io/instance=xapp-{xapp}",
                         "duranta-xapp-multus.yaml", extra)

    def xapps_check(self, since, overrides=None):
        if not self.flexric:
            return
        for xapp, texts, what, after_ue in XAPPS:
            texts, what, after_ue = (overrides or {}).get(xapp, (texts, what, after_ue))
            for text in texts:
                self.expect_log(f"app.kubernetes.io/instance=xapp-{xapp}", text, f"xApp {xapp}: {what} ({text})",
                                since=since if after_ue else None)

    def xapps_uninstall(self):
        if self.flexric:
            for xapp, _, _, _ in XAPPS:
                self.uninstall(f"xapp-{xapp}", f"app.kubernetes.io/instance=xapp-{xapp}")

    def ue_attach(self):
        self.install("nrue", self.chart("ran", "duranta-oai-nr-ue"), "duranta-oai-nr-ue", "duranta-oai-nr-ue-multus.yaml")
        deadline = time.time() + self.check_timeout
        while True:
            r = self.kubectl("exec", self.pod("duranta-oai-nr-ue"), "--", "ip", "-4", "addr", "show", "oaitun_ue1",
                             check=False, capture=True)
            if r.returncode == 0 and "12.1.1." in r.stdout:
                log("UE PDU session (12.1.1.x on oaitun_ue1): OK")
                break
            if time.time() > deadline:
                raise CheckFailed("UE PDU session: no 12.1.1.x address on oaitun_ue1")
            time.sleep(5)
        since = self.now()
        self.kubectl("exec", self.pod("duranta-oai-nr-ue"), "--", "ping", "-I", "oaitun_ue1", "-c", "4", "-W", "2", "12.1.1.1")
        log("Ping UPF through the UE tunnel: OK")
        # keep some user-plane traffic going for the xApps (stops with the UE pod)
        self.kubectl("exec", self.pod("duranta-oai-nr-ue"), "--", "sh", "-c",
                     "nohup ping -I oaitun_ue1 -i 0.2 12.1.1.1 >/dev/null 2>&1 &", check=False)
        return since

    def ue_detach(self):
        since = self.now()
        self.uninstall("nrue", "duranta-oai-nr-ue")
        self.expect_log("oai-amf", "5GMM-DEREGISTERED", "UE deregistration (AMF)", since=since, timeout=120)

    def run_scenario(self, nodes, ran, since, xapp_overrides=None):
        """Common part of every scenario once its RAN is up: E2, xApps, UE, data checks, then tear down."""
        self.e2_test(nodes, since)
        self.xapps_install()  # before the UE: the xApps must pick the UE up when it attaches
        ue_t0 = time.time()
        ue_since = self.ue_attach()
        self.xapps_check(ue_since, xapp_overrides)
        self.grafana_check(ue_t0)
        if self.keep_last:
            log("--keep: leaving this scenario deployed")
            return
        self.ue_detach()
        self.xapps_uninstall()
        for release, label in ran:
            self.uninstall(release, label)

    # ---- Grafana ---------------------------------------------------------------------------------------
    def grafana_install(self):
        self.sh(["helm", "repo", "add", "grafana-community", "https://grafana-community.github.io/helm-charts", "--force-update"], capture=True)
        self.sh(["helm", "repo", "update", "grafana-community"], capture=True)
        extra = ["-f", os.path.join(self.chart("ran", "duranta-xapp"), "grafana", "values.yaml")]
        if self.openshift:  # let OpenShift assign the UID (restricted SCC), as documented by the Grafana chart
            extra += ["-f", os.path.join(self.chart("ran", "duranta-xapp"), "grafana", "values-openshift.yaml")]
        log("Installing grafana (grafana-community/grafana)")
        self.watch.append("grafana")
        self.helm("install", "grafana", "grafana-community/grafana", "--wait", "--timeout", f"{self.timeout}s", *extra)
        log("grafana: Ready")

    def grafana_api(self, path, body=None):
        """Call the Grafana HTTP API through a short port-forward (admin password from the chart's secret)."""
        import base64, json, random, urllib.request
        pw = base64.b64decode(self.kubectl("get", "secret", "grafana", "-o", "jsonpath={.data.admin-password}",
                                           capture=True).stdout).decode()
        port = random.randint(20000, 40000)
        pf = subprocess.Popen(["kubectl", *self.ctx("--context"), "-n", self.ns, "port-forward", "svc/grafana",
                               f"{port}:80"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(20):
                try:
                    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", json.dumps(body).encode() if body else None,
                                                 {"Content-Type": "application/json",
                                                  "Authorization": "Basic " + base64.b64encode(f"admin:{pw}".encode()).decode()})
                    return json.load(urllib.request.urlopen(req, timeout=10))
                except OSError:
                    time.sleep(1)
            raise CheckFailed(f"Grafana API {path} not reachable")
        finally:
            pf.terminate()

    def grafana_check(self, t0):
        """The dashboard's own DRB.UEThpDl panel query returns data points since t0 (this scenario's UE attach)."""
        if not self.grafana:
            return
        health = self.grafana_api("/api/datasources/uid/flexric-sqlite/health")
        if health.get("status") != "OK":
            raise CheckFailed(f"Grafana SQLite datasource: {health}")
        dash = self.grafana_api(f"/api/dashboards/uid/{GRAFANA_DASHBOARD_UID}")["dashboard"]
        panel = next(p for p in dash["panels"] if p.get("title") == "DRB.UEThpDl")
        target = dict(panel["targets"][0], datasource={"uid": "flexric-sqlite"})
        deadline = time.time() + self.check_timeout
        while True:
            res = self.grafana_api("/api/ds/query", {"from": str(int(t0 * 1000)), "to": "now", "queries": [target]})["results"]["A"]
            # the panel SQL has no time filter: count only the points (epoch ms) since this scenario's UE attached
            points = sum(1 for fr in res.get("frames", []) if fr["data"]["values"]
                         for ts in fr["data"]["values"][0] if ts >= t0 * 1000)
            if points:
                log(f"Grafana dashboard 'KPI measurements' shows the UE throughput ({points} points): OK")
                return
            if time.time() > deadline:
                raise CheckFailed(f"Grafana: no DRB.UEThpDl data in the dashboard query ({res.get('error', 'no points')})")
            time.sleep(5)

    # ---- stages ----------------------------------------------------------------------------------------
    def cluster_is_minikube(self):
        return not self.openshift and self.cfg["cluster"]["create"] == "minikube"

    def setup_cluster(self):
        if self.cluster_is_minikube():
            log("Creating minikube cluster (ci-scripts/create-cluster.sh)")
            self.created_minikube = True
            self.sh(["./ci-scripts/create-cluster.sh"])
            self.context = "minikube"
        if self.multus:
            self.kubectl("get", "crd", "network-attachment-definitions.k8s.cni.cncf.io", capture=True)
        manifest = {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": self.ns, "labels": {
            f"pod-security.kubernetes.io/{m}": "privileged" for m in ("enforce", "audit", "warn")}}}
        p = subprocess.run(["kubectl", *self.ctx("--context"), "apply", "-f", "-"],
                           input=yaml.safe_dump(manifest), text=True, cwd=REPO)
        if p.returncode != 0:
            raise CheckFailed(f"cannot create namespace {self.ns}")

    def core(self):
        extra = ["--set-file", f"config={self.values('oai-5g-basic-config-multus.yaml')}"] if self.multus else []
        self.sh(["helm", "dependency", "update", self.chart("core", "oai-5g-basic")], capture=True)
        self.install("basic", self.chart("core", "oai-5g-basic"), "oai-amf", "oai-5g-basic-multus.yaml", extra)
        for nf in CORE_READY:
            self.kubectl("wait", "--for=condition=ready", "pod", "-l", f"app.kubernetes.io/name={nf}",
                         f"--timeout={self.timeout}s")
        log("Core NFs: Ready")
        self.watch += ["oai-smf", "oai-upf", "oai-nrf"]
        self.expect_log("oai-smf", "handle_receive", "PFCP association (SMF)")
        self.expect_log("oai-upf", "handle_receive", "PFCP association (UPF)")
        for nf in ["AMF", "SMF", "UPF", "UDR", "UDM", "AUSF"]:
            self.expect_log("oai-nrf", f"OAI-{nf}", f"NRF registration OAI-{nf}")
        if self.flexric:
            self.install("flexric", self.chart("ran", "duranta-flexric"), "duranta-flexric", "duranta-flexric-multus.yaml",
                         ["--set", "xappDb.enabled=true"] if self.grafana else [])
        if self.grafana:
            self.grafana_install()

    def scenario_gnb(self):
        since = self.now()
        self.install("gnb", self.chart("ran", "duranta-oai-gnb"), "duranta-oai-gnb", "duranta-oai-gnb-multus.yaml")
        self.expect_log("duranta-oai-gnb", "associated AMF 1", "NG setup (gNB - AMF)")
        self.expect_log("duranta-oai-gnb", "Frame.Slot", "gNB running")
        self.run_scenario(1, [("gnb", "duranta-oai-gnb")], since)

    def scenario_f1(self):
        since = self.now()
        self.install("cu", self.chart("ran", "duranta-oai-cu"), "duranta-oai-cu", "duranta-oai-cu-multus.yaml")
        self.expect_log("duranta-oai-cu", "associated AMF 1", "NG setup (CU - AMF)")
        self.install("du", self.chart("ran", "duranta-oai-du"), "duranta-oai-du", "duranta-oai-du-multus.yaml")
        self.expect_log("duranta-oai-cu", "Received F1 Setup Request", "F1 setup (DU - CU)")
        self.expect_log("duranta-oai-du", "Frame.Slot", "DU running")
        self.run_scenario(2, [("du", "duranta-oai-du"), ("cu", "duranta-oai-cu")], since)

    def scenario_e1_f1(self):
        since = self.now()
        self.install("cucp", self.chart("ran", "duranta-oai-cu-cp"), "duranta-oai-cu-cp", "duranta-oai-cu-cp-multus.yaml")
        self.expect_log("duranta-oai-cu-cp", "associated AMF 1", "NG setup (CU-CP - AMF)")
        self.install("cuup", self.chart("ran", "duranta-oai-cu-up"), "duranta-oai-cu-up", "duranta-oai-cu-up-multus.yaml")
        self.expect_log("duranta-oai-cu-cp", "Accepting new CU-UP ID", "E1 setup (CU-UP - CU-CP)")
        self.install("du", self.chart("ran", "duranta-oai-du"), "duranta-oai-du", "duranta-oai-du-multus.yaml")
        self.expect_log("duranta-oai-cu-cp", "Received F1 Setup Request", "F1 setup (DU - CU-CP)")
        self.expect_log("duranta-oai-du", "Frame.Slot", "DU running")
        self.run_scenario(2, [("du", "duranta-oai-du"), ("cuup", "duranta-oai-cu-up"), ("cucp", "duranta-oai-cu-cp")],
                          since, XAPPS_E1_OVERRIDE)  # 2 E2 nodes: CU-CP + DU (see RAN_E2)

    # ---- diagnostics and cleanup -----------------------------------------------------------------------
    def diagnostics(self):
        print("\n========== Diagnostics ==========", flush=True)
        self.kubectl("get", "pods", "-o", "wide", check=False)
        for label in dict.fromkeys(self.watch):
            print(f"\n----- last 40 log lines of {label} -----", flush=True)
            print("\n".join(self.logs(label).splitlines()[-40:]), flush=True)
        # init containers of pods that are not ready (e.g. a config-patcher that cannot resolve a host)
        r = self.kubectl("get", "pods", "-o", "json", check=False, capture=True)
        for p in (yaml.safe_load(r.stdout) or {}).get("items", []) if r.returncode == 0 else []:
            for st in p.get("status", {}).get("initContainerStatuses") or []:
                if not st.get("ready"):
                    out = self.kubectl("logs", p["metadata"]["name"], "-c", st["name"], check=False, capture=True).stdout
                    print(f"\n----- init container {st['name']} of {p['metadata']['name']} (not ready) -----", flush=True)
                    print("\n".join(out.splitlines()[-20:]), flush=True)

    def print_access(self):
        k = f"kubectl{' --context ' + self.context if self.context else ''} -n {self.ns}"
        print(f"""
========== --keep: everything is left running in namespace {self.ns} ==========
  pods:        {k} get pods
  UE shell:    {k} exec -it deploy/duranta-oai-nr-ue -- bash      (ping -I oaitun_ue1 12.1.1.1)
  xApp logs:   {k} logs -f deploy/xapp-kpm-duranta-xapp            (also xapp-rc / xapp-kpm-rc / xapp-gtp-mac-rlc-pdcp)""",
              flush=True)
        if self.grafana:
            print(f"""  Grafana:     {k} port-forward svc/grafana 3000:80   then http://localhost:3000, user admin, password:
               {k} get secret grafana -o jsonpath='{{.data.admin-password}}' | base64 -d
               dashboard: FlexRIC / KPI measurements""", flush=True)
        print(f"  remove:      helm{' --kube-context ' + self.context if self.context else ''} -n {self.ns} list -q | xargs -r -n1"
              f" helm -n {self.ns} uninstall; {k.split(' -n ')[0]} delete ns {self.ns}"
              + ("; minikube delete" if self.created_minikube else ""), flush=True)

    def cleanup(self):
        log("Cleanup")
        r = self.helm("list", "-q", check=False, capture=True)
        # no --wait: the shared xApp DB PVC of duranta-flexric is only deleted once the xApps and Grafana that mount it
        # are gone, so waiting per release can block; deleting the namespace waits for everything
        for rel in (r.stdout.split() if r.returncode == 0 else []):
            self.helm("uninstall", rel, check=False)
        self.sh(["kubectl", *self.ctx("--context"), "delete", "ns", self.ns, "--ignore-not-found"], check=False)
        if self.created_minikube and self.cfg["cluster"]["deleteAfter"]:
            self.sh(["minikube", "delete"], check=False)

    def remove_clones(self):
        for d in self.tmp:
            shutil.rmtree(d, ignore_errors=True)


def load_config(args, ap):
    cfg = {**DEFAULTS, "cluster": dict(DEFAULTS["cluster"]), "images": dict(DEFAULTS["images"]),
           "charts": {k: dict(v) for k, v in DEFAULTS["charts"].items()}}
    if os.path.exists(args.config):
        user = yaml.safe_load(open(args.config)) or {}
        cfg.update({k: v for k, v in user.items() if k not in ("cluster", "images", "charts")})
        cfg["cluster"].update(user.get("cluster") or {})
        cfg["images"].update(user.get("images") or {})
        for kind, src in (user.get("charts") or {}).items():
            if kind not in cfg["charts"]:
                sys.exit(f"invalid setting: charts.{kind} (core or ran)")
            cfg["charts"][kind].update(src or {})
    elif args.config != ap.get_default("config"):
        sys.exit(f"config file not found: {args.config}")
    if args.multus is not None:
        cfg["multus"] = args.multus
    if args.grafana:
        cfg["grafana"] = True
    if args.scenarios:
        cfg["scenarios"] = args.scenarios.split(",")
    for kind in ("core", "ran", "flexric"):
        if getattr(args, f"{kind}_tag"):
            cfg["images"][f"{kind}Tag"] = getattr(args, f"{kind}_tag")
    for kind in ("core", "ran"):
        src = cfg["charts"][kind]
        if getattr(args, f"{kind}_path"):
            src["path"] = os.path.abspath(getattr(args, f"{kind}_path"))  # relative to the current directory
        for key in ("git", "branch"):  # a repository or branch on the command line means: clone it
            if getattr(args, f"{kind}_{key}"):
                src[key], src["path"] = getattr(args, f"{kind}_{key}"), ""
    bad = [s for s in cfg["scenarios"] if s not in SCENARIOS]
    bad += [v for v, ok in ((cfg["cluster"]["type"], ("kubernetes", "openshift")),
                            (cfg["cluster"]["create"], ("minikube", "existing"))) if v not in ok]
    if bad:
        sys.exit(f"invalid setting(s): {bad} (see --help)")
    return cfg


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-c", "--config", default=os.path.join(REPO, "ci-scripts", "e2e-config.yaml"),
                    help="YAML settings file (default: ci-scripts/e2e-config.yaml)")
    m = ap.add_mutually_exclusive_group()
    m.add_argument("--multus", dest="multus", action="store_true", default=None, help="use multus (overrides the file)")
    m.add_argument("--no-multus", dest="multus", action="store_false", help="cluster network only (overrides the file)")
    ap.add_argument("--scenarios", help=f"comma separated subset of {','.join(SCENARIOS)} (overrides the file)")
    ap.add_argument("--core-tag", help="image tag of every core NF (overrides images.coreTag)")
    ap.add_argument("--ran-tag", help="image tag of every RAN chart: gNB, CU, CU-CP, CU-UP, DU, NR-UE (overrides images.ranTag)")
    ap.add_argument("--flexric-tag", help="image tag of FlexRIC (overrides images.flexricTag)")
    for kind, what in (("core", "OAI 5G core (orchestration)"), ("ran", "Duranta RAN and FlexRIC (helm-charts)")):
        ap.add_argument(f"--{kind}-path", help=f"local repository with the {what} charts (overrides charts.{kind})")
        ap.add_argument(f"--{kind}-git", help=f"git repository to clone the {what} charts from (overrides charts.{kind})")
        ap.add_argument(f"--{kind}-branch", help=f"branch of that git repository (overrides charts.{kind}.branch)")
    ap.add_argument("--grafana", action="store_true", default=None,
                    help="also deploy Grafana with the FlexRIC dashboard fed by the xApps (overrides the file)")
    ap.add_argument("--keep", action="store_true",
                    help="keep everything at the end and leave the last scenario running (RAN, UE, xApps, Grafana)")
    args = ap.parse_args()
    cfg = load_config(args, ap)

    run = Run(cfg)
    print(f"========== E2E test: {cfg['cluster']['type']} ({'minikube' if run.cluster_is_minikube() else 'existing cluster'}),"
          f" multus={run.multus}, flexric={run.flexric}, grafana={run.grafana}, scenarios={','.join(cfg['scenarios'])}"
          " ==========", flush=True)
    ok = False
    try:
        run.fetch_charts()
        run.setup_cluster()
        run.core()
        for i, s in enumerate(cfg["scenarios"]):
            print(f"========== Scenario {s} ==========", flush=True)
            run.keep_last = args.keep and i == len(cfg["scenarios"]) - 1
            getattr(run, "scenario_" + s.replace("-", "_"))()
        ok = True
        print("========== Test PASSED ==========", flush=True)
    except (CheckFailed, KeyboardInterrupt) as e:
        print(f"\n========== Test FAILED: {e} ==========", flush=True)
        run.diagnostics()
    finally:
        if args.keep:
            run.print_access()
        else:
            run.cleanup()
        run.remove_clones()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
