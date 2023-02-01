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

variable "run_service_account_name" {
  description = "YAAS Cloud Run Service Account identity"
  type        = string
  default     = "yaas-run-sa"
}

variable "scheduler_service_account_name" {
  description = "YAAS Cloud Scheduler Service Account identity"
  type        = string
  default     = "yaas-sched-sa"
}

variable "pubsub_service_account_name" {
  description = "Service account to be used by Pub/Sub to trigger YAAS."
  type        = string
  default     = "yaas-pubsub-sa"
}

/////////////
// Buckets //
/////////////

variable "bucket_name_prefix" {
  description = "Prefix to name the YAAS artefacts bucket, the suffix is the project numerical ID."
  type        = string
  default     = "yaas-app"
}

//////////////////
// Docker image //
//////////////////

variable "image_name_uri" {
  description = "YAAS docker application image URI. E.g.: LOCATION-docker.pkg.dev/PROJECT_ID/yaas-docker/yaas:latest"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

/////////////
// Pub/Sub //
/////////////

variable "pubsub_topic_name" {
  description = "Name of the Pub/Sub topic to send DTOs to YAAS Cloud Run."
  type        = string
  default     = "yaas-requests"
}

variable "pubsub_notification_topic_name" {
  description = "Name of the Pub/Sub topic to send runtime notification about errors."
  type        = string
  default     = "yaas-notifications"
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

variable "secrets_calendar_credentials_name" {
  description = "Secret name where the Google calendar credentials are stored"
  type        = string
  default     = "yaas_calendar_credentials"
}

//////////
// Code //
//////////

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
  default     = 0
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

///////////////////////
// Scheduler/Cronjob //
///////////////////////

variable "scheduler_calendar_credentials_refresh_name" {
  description = "Name of the Cloud Scheduler that triggers YAAS calendar credentials refresh"
  type        = string
  default     = "yaas-calendar-credentials-refresh"
}

variable "scheduler_cache_refresh_name" {
  description = "Name of the Cloud Scheduler that triggers YAAS calendar cache refresh"
  type        = string
  default     = "yaas-cache-refresh"
}

variable "scheduler_cache_refresh_data" {
  description = "YAAS calendar cache refresh trigger payload."
  type        = string
  default     = ""
}

// Set to run, by default, every 6 hours (minute 17)
variable "scheduler_cache_refresh_rate_in_hours" {
  description = "YAAS calendar cache refresh rate in hours, i.e., how many hours after a refresh to repeat it."
  type        = number
  default     = 6
}

// This is to avoid clashing between scheduler and keep debugging easier.
variable "scheduler_calendar_credentials_refresh_cron_entry_triggering_minute" {
  description = "YAAS calendar calendar credentials refresh triggering minute. Please only change if you know what you are doing."
  type        = number
  default     = 13
}

// This is to avoid clashing between scheduler and keep debugging easier.
variable "scheduler_cache_refresh_cron_entry_triggering_minute" {
  description = "YAAS calendar cache refresh triggering minute. Please only change if you know what you are doing."
  type        = number
  default     = 17
}

variable "scheduler_request_name" {
  description = "Name of the Cloud Scheduler that triggers YAAS request emission."
  type        = string
  default     = "yaas-request-emission"
}

variable "scheduler_request_data" {
  description = "YAAS request emission trigger payload."
  type        = string
  default     = ""
}

// Set to run, by default, every hour
variable "scheduler_request_rate_in_minutes" {
  description = "YAAS calendar cache refresh rate in hours, i.e., how many hours after a refresh to repeat it."
  type        = number
  default     = 30
}

// By default, uses UTC
variable "scheduler_cron_timezone" {
  description = "Crontab entry timezone."
  type        = string
  default     = "Etc/UTC"
}

/////////////////////////////
// Monitoring and Alerting //
/////////////////////////////

variable "monitoring_email_address" {
  description = "When there is a failure, it needs to send the alert to a specific email."
  type        = string
}

variable "monitoring_email_channel_name" {
  description = "Runtime monitoring channel name to email."
  type        = string
  default     = "yaas-build-email-monitoring-channel"
}

variable "monitoring_pubsub_channel_name" {
  description = "Runtime monitoring channel name."
  type        = string
  default     = "yaas-build-pubsub-monitoring-channel"
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
