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

////////////////////
// Pub/Sub Topics //
////////////////////

variable "pubsub_cal_creds_refresh_name" {
  description = "Name of the Pub/Sub topic to send Google Calendar credentials refresh requests."
  type        = string
  default     = "yaas-cal-creds-refresh"
}

variable "pubsub_cache_refresh_name" {
  description = "Name of the Pub/Sub topic to send Google Calendar cache refresh requests."
  type        = string
  default     = "yaas-cache-refresh"
}

variable "pubsub_send_request_name" {
  description = "Name of the Pub/Sub topic to send requests to process all upcoming scaling requests."
  type        = string
  default     = "yaas-send-request"
}

variable "pubsub_enact_request_name" {
  description = "Name of the Pub/Sub topic to send specific scaling requests."
  type        = string
  default     = "yaas-enact-request"
}

variable "pubsub_notification_topic_name" {
  description = "Name of the Pub/Sub topic to send runtime notification about errors."
  type        = string
  default     = "yaas-notifications"
}

/////////////////////
// Caching Request //
/////////////////////

variable "cache_refresh_range_in_days" {
  description = "How many days, in the future, to cache events for."
  type        = number
  default     = 3
}

///////////////////////
// Scheduler/Cronjob //
///////////////////////

// By default, uses UTC
variable "scheduler_cron_timezone" {
  description = "Crontab entry timezone."
  type        = string
  default     = "Etc/UTC"
}

// Calendar Credentials Refresh

variable "scheduler_calendar_credentials_refresh_name" {
  description = "Name of the Cloud Scheduler that triggers YAAS calendar credentials refresh"
  type        = string
  default     = "yaas-calendar-credentials-refresh"
}

// This is to avoid clashing between scheduler and keep debugging easier.
variable "scheduler_calendar_credentials_refresh_cron_entry_triggering_minute" {
  description = "YAAS calendar calendar credentials refresh triggering minute. Please only change if you know what you are doing."
  type        = number
  default     = 13
}

// Calendar Cache Refresh

variable "scheduler_cache_refresh_name" {
  description = "Name of the Cloud Scheduler that triggers YAAS calendar cache refresh"
  type        = string
  default     = "yaas-cache-refresh"
}

// Set to run, by default, every 6 hours (minute 17)
variable "scheduler_cache_refresh_rate_in_hours" {
  description = "YAAS calendar cache refresh rate in hours, i.e., how many hours after a refresh to repeat it."
  type        = number
  default     = 6
}

// This is to avoid clashing between scheduler and keep debugging easier.
variable "scheduler_cache_refresh_cron_entry_triggering_minute" {
  description = "YAAS calendar cache refresh triggering minute. Please only change if you know what you are doing."
  type        = number
  default     = 17
}

// Send Requests

variable "scheduler_request_name" {
  description = "Name of the Cloud Scheduler that triggers YAAS request emission."
  type        = string
  default     = "yaas-request-emission"
}

// Set to run, by default, every hour
variable "scheduler_request_rate_in_minutes" {
  description = "YAAS calendar cache refresh rate in hours, i.e., how many hours after a refresh to repeat it."
  type        = number
  default     = 30
}

////////////////////
// Secret Manager //
////////////////////

variable "secrets_calendar_credentials_name" {
  description = "Secret name where the Google calendar credentials are stored"
  type        = string
  default     = "yaas_calendar_credentials"
}

//////////////////
// Docker image //
//////////////////

variable "image_name_uri" {
  description = "YAAS docker application image URI. E.g.: LOCATION-docker.pkg.dev/PROJECT_ID/yaas-docker/yaas:latest"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
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

///////////////
// Cloud Run //
///////////////

variable "run_name" {
  description = "YAAS Cloud Run name."
  type        = string
  default     = "yaas-run"
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
