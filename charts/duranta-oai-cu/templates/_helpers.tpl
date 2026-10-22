{{/* vim: set filetype=mustache: */}}
{{/*
Expand the name of the chart.
*/}}
{{- define "oai-cu.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "oai-cu.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "oai-cu.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "oai-cu.labels" -}}
helm.sh/chart: {{ include "oai-cu.chart" . }}
{{ include "oai-cu.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Selector labels
*/}}
{{- define "oai-cu.selectorLabels" -}}
app.kubernetes.io/name: {{ include "oai-cu.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Create the name of the service account to use
*/}}
{{- define "oai-cu.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
    {{ default (include "oai-cu.fullname" .) .Values.serviceAccount.name }}
{{- else -}}
    {{ default "default" .Values.serviceAccount.name }}
{{- end -}}
{{- end -}}

{{/*
Count enabled interfaces with defaultRoute defined and non-empty
*/}}
{{- define "oai-cu.countDefaultRouteInterfaces" -}}
{{- $count := 0 -}}
{{- if and .Values.multus.enabled (gt (len .Values.multus.interfaces) 0) -}}
  {{- range $i, $if := .Values.multus.interfaces }}
    {{- if $if.enabled }}
      {{- if (not (empty $if.defaultRoute)) }}
        {{- $count = add $count 1 }}
      {{- end }}
    {{- end }}
  {{- end }}
{{- end }}
{{- $count -}}
{{- end }}

{{/*
Resolve F1 interface name
- If Multus is enabled and the interface is defined and enabled, use the Multus interface name
- Else, default to pod networking interface (eth0)
*/}}
{{/*
config.f1IfName overrides the automatic choice below
*/}}
{{- define "oai-cu.f1IfName" -}}
{{- .Values.config.f1IfName | default (include "oai-cu.f1IfNameAuto" .) -}}
{{- end }}

{{- define "oai-cu.f1IfNameAuto" -}}
{{- $f1 := "eth0" -}}
{{- if .Values.multus.enabled -}}
{{- range $if := .Values.multus.interfaces }}
  {{- if and (eq $if.name "f1") $if.enabled }}{{- $f1 = $if.name -}}{{- end -}}
{{- end -}}
{{- end -}}
{{ $f1 }}
{{- end }}

{{/*
Resolve N2 interface name
- If Multus is enabled and the interface is defined and enabled, use the Multus interface name
- Else, default to pod networking interface (eth0)
*/}}
{{/*
config.n2IfName overrides the automatic choice below
*/}}
{{- define "oai-cu.n2IfName" -}}
{{- .Values.config.n2IfName | default (include "oai-cu.n2IfNameAuto" .) -}}
{{- end }}

{{- define "oai-cu.n2IfNameAuto" -}}
{{- $n2 := "eth0" -}}
{{- if .Values.multus.enabled -}}
{{- range $if := .Values.multus.interfaces }}
  {{- if and (eq $if.name "n2") $if.enabled }}{{- $n2 = $if.name -}}{{- end -}}
{{- end -}}
{{- end -}}
{{ $n2 }}
{{- end }}

{{/*
Resolve N3 interface name
- If Multus is enabled and the interface is defined and enabled, use the Multus interface name
- Else, default to pod networking interface (eth0)
*/}}
{{/*
config.n3IfName overrides the automatic choice below
*/}}
{{- define "oai-cu.n3IfName" -}}
{{- .Values.config.n3IfName | default (include "oai-cu.n3IfNameAuto" .) -}}
{{- end }}

{{- define "oai-cu.n3IfNameAuto" -}}
{{- $n3 := "eth0" -}}
{{- if .Values.multus.enabled -}}
{{- range $if := .Values.multus.interfaces }}
  {{- if and (eq $if.name "n3") $if.enabled }}{{- $n3 = $if.name -}}{{- end -}}
{{- end -}}
{{- end -}}
{{ $n3 }}
{{- end }}

{{/*
Resolve E2 interface name
- If Multus is enabled and the interface is defined and enabled, use the Multus interface name
- Else, default to pod networking interface (eth0)
*/}}
{{- define "oai-cu.e2IfName" -}}
{{- $e2 := "eth0" -}}
{{- if .Values.multus.enabled -}}
{{- range $if := .Values.multus.interfaces }}
  {{- if and (eq $if.name "e2") $if.enabled }}{{- $e2 = $if.name -}}{{- end -}}
{{- end -}}
{{- end -}}
{{ $e2 }}
{{- end }}