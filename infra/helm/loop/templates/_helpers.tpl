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

{{/*
loop.podSecurityContext — pod-level security defaults shared by every
service Deployment. Closes P0.6g from the prod-readiness audit.

Pod containers run as a non-root, non-zero UID with a fixed fsGroup so
volume mounts get the right ownership without `chown`. seccompProfile
RuntimeDefault gates syscall surface to the kubelet's distribution
default (gVisor / cri-o seccomp.json / containerd default).
*/}}
{{- define "loop.podSecurityContext" -}}
runAsNonRoot: true
runAsUser: 65532
runAsGroup: 65532
fsGroup: 65532
seccompProfile:
  type: RuntimeDefault
{{- end -}}

{{/*
loop.containerSecurityContext — container-level hardening shared by
every service container. Closes P0.6g.

readOnlyRootFilesystem stops a compromised process from writing back
into the image filesystem. allowPrivilegeEscalation:false stops setuid
binaries (the distroless-nonroot base has none, but defense-in-depth).
capabilities drop ALL because we never need any Linux capability for
serving HTTP on a high port.
*/}}
{{- define "loop.containerSecurityContext" -}}
runAsNonRoot: true
runAsUser: 65532
runAsGroup: 65532
readOnlyRootFilesystem: true
allowPrivilegeEscalation: false
capabilities:
  drop:
    - ALL
seccompProfile:
  type: RuntimeDefault
{{- end -}}

{{/*
loop.startupProbe — give slow-importing Python apps (uvicorn workers
loading FastAPI + sqlalchemy + opentelemetry) a 90s window to bind
the port before the kubelet's livenessProbe starts swinging. Closes
P1 finding from the infra audit ("no startupProbe → cold-start
restart loop on a 2-CPU node").
*/}}
{{- define "loop.startupProbe" -}}
httpGet:
  path: /healthz
  port: http
failureThreshold: 30
periodSeconds: 3
timeoutSeconds: 2
{{- end -}}

{{/*
loop.podAntiAffinity — soft anti-affinity across nodes + zones so the
scheduler spreads replicas before stacking them on one node. Closes
P1 ("no anti-affinity / topologySpreadConstraints anywhere").

We use `preferredDuringSchedulingIgnoredDuringExecution` (soft) so a
single-node dev cluster can still run >1 replica without going
Pending. Production overlays should bump to `requiredDuringScheduling…`
via the standard helm values override.
*/}}
{{- define "loop.podAntiAffinity" -}}
{{- $component := . -}}
podAntiAffinity:
  preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchLabels:
            app.kubernetes.io/component: {{ $component }}
        topologyKey: topology.kubernetes.io/zone
    - weight: 50
      podAffinityTerm:
        labelSelector:
          matchLabels:
            app.kubernetes.io/component: {{ $component }}
        topologyKey: kubernetes.io/hostname
{{- end -}}

{{/*
loop.gracefulShutdown — preStop sleep + 60s grace so SSE streams /
in-flight RPC drain instead of being guillotined at the default 30s.
Closes P1 ("no terminationGracePeriodSeconds / preStop hooks").

The 10s preStop sleep gives the load balancer / endpoints controller
time to remove the pod from rotation before kubelet sends SIGTERM.
*/}}
{{- define "loop.gracefulShutdown" -}}
terminationGracePeriodSeconds: 60
{{- end -}}

{{- define "loop.preStopHook" -}}
preStop:
  exec:
    command: ["/bin/sh", "-c", "sleep 10"]
{{- end -}}

{{/*
loop.writableTmpVolumes — when readOnlyRootFilesystem is on, anything
that needs to write at runtime (uvicorn /tmp scratch, prometheus
client multiproc dir, model-catalog disk cache) needs an emptyDir.
Mounted at /tmp by every service.
*/}}
{{- define "loop.writableTmpVolumeMounts" -}}
- name: tmp
  mountPath: /tmp
- name: home-cache
  mountPath: /home/nonroot/.cache
{{- end -}}

{{- define "loop.writableTmpVolumes" -}}
- name: tmp
  emptyDir:
    sizeLimit: 64Mi
- name: home-cache
  emptyDir:
    sizeLimit: 32Mi
{{- end -}}

{{/*
loop.cpuMillicores — parse a CPU quantity into millicores for
lightweight worker-count heuristics. Supports values like "500m" and
"2" (cores).
*/}}
{{- define "loop.cpuMillicores" -}}
{{- $raw := toString . -}}
{{- if hasSuffix "m" $raw -}}
{{- trimSuffix "m" $raw -}}
{{- else -}}
{{- mul (atoi $raw) 1000 -}}
{{- end -}}
{{- end -}}

{{/*
loop.recommendedWorkers — derive a per-pod UVICORN_WORKERS value from
resource limits and replica count. This keeps worker fan-out aligned
with requested compute and avoids over-subscribing small pods.
*/}}
{{- define "loop.recommendedWorkers" -}}
{{- $replicas := int (default 1 .replicaCount) -}}
{{- $limits := .resources.limits | default dict -}}
{{- $cpu := get $limits "cpu" | default "1000m" -}}
{{- $millicores := int (include "loop.cpuMillicores" $cpu) -}}
{{- $fromCpu := max 1 (div $millicores 500) -}}
{{- $clusterTarget := max 4 (mul $replicas 2) -}}
{{- $fromReplicas := max 1 (div $clusterTarget $replicas) -}}
{{- max $fromCpu $fromReplicas -}}
{{- end -}}
