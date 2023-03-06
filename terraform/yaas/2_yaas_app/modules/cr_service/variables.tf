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

variable "run_sa_email" {
  description = "YAAS Scheduler Cloud Run Service Account identity email"
  type        = string
}

/////////////
// Buckets //
/////////////

variable "bucket_name" {
  description = "YAAS artefacts bucket name."
  type        = string
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
