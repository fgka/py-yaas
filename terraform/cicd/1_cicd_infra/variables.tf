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

variable "tf_build_service_account_name" {
  description = "Service account to build terraform"
  type        = string
  default     = "yaas-tf-build-sa"
}

variable "build_service_account_name" {
  description = "Service account to build artefacts"
  type        = string
  default     = "yaas-build-sa"
}

/////////////
// Buckets //
/////////////

variable "build_bucket_name_prefix" {
  description = "Prefix to name the build artefacts bucket, the suffix is the project numerical ID."
  type        = string
  default     = "yaas-build-artefacts"
}

variable "object_age_in_days" {
  description = "How long to keep objects, in days, before automatically remove them."
  type        = number
  default     = 7
}

///////////////////////
// Artifact Registry //
///////////////////////

variable "docker_artifact_registry_name" {
  description = "Cloud Run YAAS docker image registry name."
  type        = string
  default     = "yaas-docker"
}

variable "python_artifact_registry_name" {
  description = "Python YAAS package registry name."
  type        = string
  default     = "yaas-py"
}

////////////
// PubSub //
////////////

variable "build_monitoring_topic_name" {
  description = "Name of the PubSub topic to send monitoring alerts."
  type        = string
  default     = "yass-build-notification"
}

/////////////////////////////
// Monitoring and Alerting //
/////////////////////////////

variable "build_pubsub_monitoring_channel_name" {
  description = "Build monitoring channel name."
  type        = string
  default     = "yaas-build-pubsub-monitoring-channel"
}

variable "build_email_monitoring_channel_name" {
  description = "Build monitoring channel name to email."
  type        = string
  default     = "yaas-build-email-monitoring-channel"
}

variable "build_monitoring_email_address" {
  description = "When the build fails, it needs to send the alert to a specific email."
  type        = string
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
