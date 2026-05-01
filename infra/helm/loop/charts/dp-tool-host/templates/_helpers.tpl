{{- define "dp-tool-host.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "dp-tool-host.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "dp-tool-host.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "dp-tool-host.labels" -}}
app.kubernetes.io/name: {{ include "dp-tool-host.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: loop
app.kubernetes.io/component: dp-tool-host
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- end -}}

{{- define "dp-tool-host.image" -}}
{{- printf "%s/%s:%s" .Values.global.imageRegistry .Values.image.repository .Values.image.tag -}}
{{- end -}}

{{- define "dp-tool-host.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "dp-tool-host.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{- define "dp-tool-host.kataCheckName" -}}
{{- printf "%s-kata-check" (include "dp-tool-host.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
