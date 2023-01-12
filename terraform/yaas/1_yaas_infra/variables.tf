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

////////////////////
// Secret Manager //
////////////////////

variable "secrets_calendar_credentials_name" {
  description = "Secret name where the Google calendar credentials are stored"
  type        = string
  default     = "yaas_calendar_credentials"
}

/////////////////////////////
// Monitoring and Alerting //
/////////////////////////////

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

variable "monitoring_email_address" {
  description = "When there is a failure, it needs to send the alert to a specific email."
  type        = string
}
