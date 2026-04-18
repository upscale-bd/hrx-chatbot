{{- define "pmx-backend.name" -}}pmx-backend{{- end -}}
{{- define "pmx-backend.fullname" -}}
{{- printf "%s-%s" .Release.Name (include "pmx-backend.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- define "pmx-backend.labels" -}}
app.kubernetes.io/name: {{ include "pmx-backend.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
{{- define "pmx-backend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "pmx-backend.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
