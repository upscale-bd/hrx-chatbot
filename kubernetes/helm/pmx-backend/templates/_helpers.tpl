{{- define "hrx-chatbot.name" -}}hrx-chatbot{{- end -}}
{{- define "hrx-chatbot.fullname" -}}
{{- printf "%s-%s" .Release.Name (include "hrx-chatbot.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- define "hrx-chatbot.labels" -}}
app.kubernetes.io/name: {{ include "hrx-chatbot.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
{{- define "hrx-chatbot.selectorLabels" -}}
app.kubernetes.io/name: {{ include "hrx-chatbot.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
