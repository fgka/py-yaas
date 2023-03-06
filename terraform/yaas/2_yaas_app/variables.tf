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

//////////////////////
// Service Accounts //
//////////////////////

variable "run_sched_sa_email" {
  description = "YAAS Scheduler Cloud Run Service Account identity email"
  type        = string
}

variable "run_scaler_sa_email" {
  description = "YAAS Scaler Cloud Run Service Account identity email"
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

variable "pubsub_command_id" {
  description = "ID of the Pub/Sub topic to send commands to."
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

variable "topic_to_pubsub_gcs_path" {
  description = "YAAS GCS object path to where extra topics will reside."
  type        = string
  default     = "yaas/topic_to_pubsub"
}

// Do **NOT** change. Check code first
variable "service_path_command" {
  description = "YAAS Cloud Run service path to trigger commands."
  type        = string
  default     = "/command"
}

// Do **NOT** change. Check code first
variable "service_path_enact_standard_request" {
  description = "YAAS Cloud Run service path to enact standard requests."
  type        = string
  default     = "/enact-standard-requests"
}

// Do **NOT** change. Check code first
variable "service_path_enact_gcs_batch_request" {
  description = "YAAS Cloud Run service path to enact GCS batch requests."
  type        = string
  default     = "/enact-gcs-requests"
}

//////////////////
// Docker image //
//////////////////

variable "sched_image_name_uri" {
  description = "YAAS Scheduler docker application image URI. E.g.: LOCATION-docker.pkg.dev/PROJECT_ID/yaas-docker/yaas_sched:latest"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "scaler_image_name_uri" {
  description = "YAAS Scaler docker application image URI. E.g.: LOCATION-docker.pkg.dev/PROJECT_ID/yaas-docker/yaas_sched:latest"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

///////////////
// Cloud Run //
///////////////

variable "run_sched_name" {
  description = "YAAS Scheduler Cloud Run name."
  type        = string
  default     = "yaas-sched"
}

variable "run_scaler_name" {
  description = "YAAS Scaler Cloud Run name."
  type        = string
  default     = "yaas-scaler"
}

variable "run_timeout" {
  description = "Cloud Run timeout in seconds."
  type        = number
  default     = 540
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
