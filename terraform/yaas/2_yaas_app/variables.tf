////////////////////
// Global/General //
////////////////////

variable "project_id" {
  description = "Project ID where to deploy and source of data."
  type        = string
}

variable "region" {
  description = "Default region where to create resources."
  type        = string
  default     = "us-central1"
}

variable "run_cicd" {
  description = "If it is run through Cloud Build."
  type        = bool
  default     = true
}

//////////////////////
// Service Accounts //
//////////////////////

variable "run_sa_email" {
  description = "YAAS Cloud Run Service Account identity email"
  type        = string
}

variable "pubsub_sa_email" {
  description = "Service account email to be used by Pub/Sub to trigger YAAS."
  type        = string
}

/////////////
// Buckets //
/////////////

variable "bucket_name" {
  description = "YAAS artefacts bucket name."
  type        = string
}

/////////////
// Pub/Sub //
/////////////

variable "pubsub_cal_creds_refresh_id" {
  description = "ID of the Pub/Sub topic to send Google Calendar credentials refresh requests."
  type        = string
}

variable "pubsub_cache_refresh_id" {
  description = "Name of the Pub/Sub topic to send Google Calendar cache refresh requests."
  type        = string
}

variable "pubsub_send_request_id" {
  description = "ID of the Pub/Sub topic to send requests to process all upcoming scaling requests."
  type        = string
}

variable "pubsub_enact_standard_request_id" {
  description = "ID of the Pub/Sub topic to send standard scaling requests."
  type        = string
}

variable "pubsub_enact_gcs_batch_request_id" {
  description = "ID of the Pub/Sub topic to to send GCS based batch scaling requests."
  type        = string
}

variable "pubsub_notification_topic_id" {
  description = "ID of the Pub/Sub topic to send runtime notification about errors."
  type        = string
}

variable "pubsub_subscription_retention_in_sec" {
  description = "For how long, in seconds, to keep messages in PubSub."
  type        = number
  default     = 1200 # 20 minutes = 1200s
}

variable "pubsub_subscription_min_retry_backoff_in_sec" {
  description = "Minimum retry backoff time in seconds."
  type        = number
  default     = 10
}

////////////////////
// Secret Manager //
////////////////////

variable "secrets_calendar_credentials_id" {
  description = "Secret ID where the Google calendar credentials are stored"
  type        = string
}

//////////
// Code //
//////////

variable "calendar_id" {
  description = "YAAS Google Calendar ID to use"
  type        = string
}

variable "config_json_tmpl" {
  description = "Template for config json"
  type        = string
  default     = "templates/config.json.tmpl"
}

variable "sqlite_cache_path" {
  description = "YAAS Google Calendar cache SQLite GCS object path"
  type        = string
  default     = "yaas/calendar_cache.sql"
}

variable "log_level" {
  description = "YAAS Cloud Run log level."
  type        = string
  default     = "INFO"
}

variable "config_path" {
  description = "YAAS configuration object path in the bucket. E.g.: yaas/config.json"
  type        = string
  default     = "yaas/config.json"
}

// Do **NOT** change. Check code first
variable "service_path_update_calendar_credentials" {
  description = "YAAS Coud Run service path to trigger calendar credentials OAuth2 refresh."
  type        = string
  default     = "/update-calendar-credentials-secret"
}

// Do **NOT** change. Check code first
variable "service_path_update_cache" {
  description = "YAAS Coud Run service path to trigger calendar cache update."
  type        = string
  default     = "/update-cache"
}

// Do **NOT** change. Check code first
variable "service_path_request_emission" {
  description = "YAAS Coud Run service path to trigger scaling requests emission."
  type        = string
  default     = "/send-requests"
}

// Do **NOT** change. Check code first
variable "service_path_enact_standard_request" {
  description = "YAAS Coud Run service path to enact standard requests."
  type        = string
  default     = "/enact-standard-requests"
}

// Do **NOT** change. Check code first
variable "service_path_enact_gcs_batch_request" {
  description = "YAAS Coud Run service path to enact GCS batch requests."
  type        = string
  default     = "/enact-gcs-requests"
}

//////////////////
// Docker image //
//////////////////

variable "image_name_uri" {
  description = "YAAS docker application image URI. E.g.: LOCATION-docker.pkg.dev/PROJECT_ID/yaas-docker/yaas:latest"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

///////////////
// Cloud Run //
///////////////

variable "run_name" {
  description = "YAAS Cloud Run name."
  type        = string
  default     = "yaas-run"
}

variable "run_cpu" {
  description = "Cloud Run CPU request/limit."
  type        = string
  default     = "1000m"
}

variable "run_mem" {
  description = "Cloud Run Memory request/limit."
  type        = string
  default     = "512Mi"
}

variable "run_container_concurrency" {
  description = "Cloud Run request concurrency per container, mind thread-safety."
  type        = number
  default     = 80
}

variable "run_timeout" {
  description = "Cloud Run timeout in seconds."
  type        = number
  default     = 540
}

variable "run_min_instances" {
  description = "Cloud Run minimum instances."
  type        = number
  default     = 0
}

variable "run_max_instances" {
  description = "Cloud Run yaas maximum instances."
  type        = number
  default     = 10
}

/////////////////////////////
// Monitoring and Alerting //
/////////////////////////////

variable "monitoring_email_channel_name" {
  description = "Runtime monitoring channel name to email."
  type        = string
}

variable "monitoring_pubsub_channel_name" {
  description = "Runtime monitoring channel name."
  type        = string
}

variable "monitoring_alert_severity" {
  description = "Severity, included, above which it should generate an alert."
  type        = string
  default     = "ERROR"
}

variable "monitoring_notification_email_rate_limit_in_minutes" {
  description = "For how many minutes to wait for until sending the next email notification."
  type        = number
  default     = 60
}

variable "monitoring_notification_pubsub_rate_limit_in_minutes" {
  description = "For how many minutes to wait for until sending the next Pub/Sub notification."
  type        = number
  default     = 5
}

variable "monitoring_notification_auto_close_in_days" {
  description = "For how many days to keep an alert alive before closing due to lack of reaction to it."
  type        = number
  default     = 7
}
