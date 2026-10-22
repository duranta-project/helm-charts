{{/* vim: set filetype=mustache: */}}
{{/*
Expand the name of the chart.
*/}}
{{- define "duranta-xapp.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "duranta-xapp.fullname" -}}
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
{{- define "duranta-xapp.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "duranta-xapp.labels" -}}
helm.sh/chart: {{ include "duranta-xapp.chart" . }}
{{ include "duranta-xapp.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Selector labels
*/}}
{{- define "duranta-xapp.selectorLabels" -}}
app.kubernetes.io/name: {{ include "duranta-xapp.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Create the name of the service account to use
*/}}
{{- define "duranta-xapp.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
    {{ default (include "duranta-xapp.fullname" .) .Values.serviceAccount.name }}
{{- else -}}
    {{ default "default" .Values.serviceAccount.name }}
{{- end -}}
{{- end -}}

{{/*
Interface used to reach the RIC: the enabled multus interface named "e2" (else the first enabled one), else eth0
*/}}
{{- define "duranta-xapp.e2IfName" -}}
{{- $e2 := "" -}}
{{- if .Values.multus.enabled -}}
{{- range $if := .Values.multus.interfaces }}
  {{- if and $if.enabled (or (eq $if.name "e2") (not $e2)) }}{{- $e2 = $if.name -}}{{- end -}}
{{- end -}}
{{- end -}}
{{ $e2 | default "eth0" }}
{{- end }}

