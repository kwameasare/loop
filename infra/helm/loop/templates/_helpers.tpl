{{/*
Expand the name of the chart.
*/}}
{{- define "loop.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "loop.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "loop.labels" -}}
app.kubernetes.io/name: {{ include "loop.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
loop.ai/deployment-mode: {{ .Values.global.deploymentMode | quote }}
{{- if .Values.global.customerId }}
loop.ai/customer-id: {{ .Values.global.customerId | quote }}
{{- end }}
loop.ai/dedicated-stack: {{ ternary "true" "false" .Values.global.isolation.dedicatedStack | quote }}
{{- end -}}

{{- define "loop.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "loop.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{- define "loop.image" -}}
{{- $component := index . 1 -}}
{{- $root := index . 0 -}}
{{- $registry := $root.Values.global.imageRegistry -}}
{{- printf "%s/%s:%s" $registry $component.image.repository $component.image.tag -}}
{{- end -}}
