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

variable "terraform_bucket_name" {
  description = "Bucket name to store terraform states."
  type        = string
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

variable "monitoring_email_address" {
  description = "When YAAS fails, it needs to send the alert to a specific email."
  type        = string
}

////////////
// Docker //
////////////

variable "docker_base_image" {
  description = "Docker base image"
  type        = string
  default     = "python:buster"
}

variable "yaas_image_name" {
  description = "YAAS docker application image"
  type        = string
  default     = "yaas"
}

variable "yaas_dockerfile" {
  description = "YAAS application Dockerfile"
  type        = string
  default     = "./docker/Dockerfile"
}

///////////////
// Cloud Run //
///////////////

variable "yaas_service_to_run_name" {
  description = "Application to Cloud Run, e.g.: {\"scaler\" = \"yaas-scaler\"}"
  type = object({
    scaler    = string
    scheduler = string
  })
  default = {
    scaler    = "yaas-scaler",
    scheduler = "yaas-scheduler",
  }
}

variable "run_container_concurrency" {
  description = "YAAS Cloud Run container concurrency."
  type        = number
  default     = 80
}

/////////////////
// Cloud Build //
/////////////////

variable "python_build_trigger_name" {
  description = "Cloud Build trigger for Python code."
  type        = string
  default     = "yaas-py"
}

variable "app_build_trigger_name" {
  description = "Cloud Build trigger for Docker image."
  type        = string
  default     = "yaas-application"
}

variable "tf_build_trigger_name" {
  description = "Cloud Build trigger for CI/CD Terraform code."
  type        = string
  default     = "yaas-tf-cicd"
}


variable "tf_yaas_trigger_name" {
  description = "Cloud Build trigger for YAAS infrastructure Terraform code."
  type        = string
  default     = "yaas-tf-infra"
}

//////////
// Code //
//////////

variable "calendar_id" {
  description = "YAAS Google Calendar ID to use"
  type        = string
}

variable "gmail_username" {
  description = "Gmail username (email). If given will assume CalDAV access to Google Calendar."
  type        = string
  default     = ""
}

variable "yaas_pip_package" {
  description = "Python package full name with version, e.g.: [\"py-yaas-service>=1.0\", \"py-yaas-core>=1.0\"]"
  type        = list(string)
  default = [
    "py-yaas-core>=1.0",
    "py-yaas-service>=1.0",
  ]
}

variable "yaas_service_to_package" {
  description = "Python package full name where APPLICATION is declared, e.g.: {\"scaler\" = \"yaas_scaler_service\"}"
  type = object({
    scaler    = string
    scheduler = string
  })
  default = {
    scaler    = "yaas_scaler_service",
    scheduler = "yaas_scheduler_service",
  }
}

variable "yaas_py_modules" {
  description = "Python modules. Dot not change, unless you know what you are doing."
  type        = list(string)
  default     = ["core", "cli", "service"]
}

////////////////////
// Secret Manager //
////////////////////

variable "secrets_calendar_credentials_file" {
  description = "File with the secret content for Google calendar credentials"
  type        = string
  default     = ""
}

////////////
// Github //
////////////

variable "github_owner" {
  description = "GitHub repo owner"
  type        = string
}

variable "github_repo_name" {
  description = "GitHub repo name"
  type        = string
}

variable "github_branch" {
  description = "GitHub repo branch to track"
  type        = string
  default     = "main"
}

///////////////
// Terraform //
///////////////

variable "tf_cicd_plan_args" {
  description = "CI/CD Terraform plan args"
  type        = map(any)
  default     = {}
}

variable "tf_infra_plan_args" {
  description = "YAAS infrastructure Terraform plan args"
  type        = map(any)
  default     = {}
}

variable "tf_build_ignored_files" {
  description = "Which files to be ignored in all builds, typically documentation"
  type        = list(string)
  default     = ["**/*.md", "**/doc/*"]
}
