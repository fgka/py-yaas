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

variable "pubsub_service_account_name" {
  description = "Service account to be used by Pub/Sub to trigger YAAS."
  type        = string
  default     = "yaas-pubsub-sa"
}

////////////////////////////////////////
// Service Accounts: YAAS permissions //
////////////////////////////////////////

variable "run_service_account_roles" {
  description = "All admin roles required to let YAAS manage resources"
  type        = list(string)
  default = [
    "roles/compute.instanceAdmin.v1",
    "roles/cloudfunctions.admin",
    "roles/cloudsql.admin",
    "roles/run.admin",
    "roles/iam.serviceAccountUser", // for impersonation
  ]
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

variable "pubsub_command_name" {
  description = "Name of the Pub/Sub topic to send commands to."
  type        = string
  default     = "yaas-command"
}

variable "pubsub_enact_standard_request_name" {
  description = "Name of the Pub/Sub topic to send standard scaling requests."
  type        = string
  default     = "yaas-enact-standard-request"
}

variable "pubsub_enact_gcs_batch_request_name" {
  description = "Name of the Pub/Sub topic to send GCS based batch scaling requests."
  type        = string
  default     = "yaas-enact-gcs-batch-request"
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

// Set to run, by default, every 4 hours (minute 13)
variable "scheduler_calendar_credentials_refresh_rate_in_hours" {
  description = "YAAS calendar credentials refresh rate in hours, i.e., how many hours after a refresh to repeat it."
  type        = number
  default     = 4
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

variable "secrets_calendar_credentials_file" {
  description = "File with the secret content for Google calendar credentials"
  type        = string
  default     = null
}

variable "secrets_calendar_credentials_name" {
  description = "Secret name where the Google calendar credentials are stored"
  type        = string
  default     = "yaas_calendar_credentials"
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
