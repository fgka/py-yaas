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
  description = "Name of the PubSub topic to send BigQuery transfer runs' notifications to."
  type        = string
  default     = "yass-build-notification"
}

////////////////
// Monitoring //
////////////////

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

/////////////////
// Cloud Build //
/////////////////


variable "python_build_trigger_name" {
  description = "Cloud Build trigger for Python code."
  type        = string
  default     = "yaas-py"
}

variable "python_build_template_filename" {
  description = "Cloud Build template for Python code."
  type        = string
  default     = "cloudbuild/cloudbuild_py.yaml"
}

variable "docker_build_trigger_name" {
  description = "Cloud Build trigger for Docker image."
  type        = string
  default     = "yaas-docker"
}

variable "docker_build_template_filename" {
  description = "Cloud Build template for Python code."
  type        = string
  default     = "cloudbuild/cloudbuild_docker.yaml"
}

variable "tf_build_trigger_name" {
  description = "Cloud Build trigger for Terraform code."
  type        = string
  default     = "yaas-tf-cicd"
}

variable "tf_build_template_filename" {
  description = "Cloud Build template for CI/CD Terraform code."
  type        = string
  default     = "cloudbuild/cloudbuild_tf_cicd.yaml"
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

//////////
// Code //
//////////

variable "yaas_pip_package" {
  description = "Python package full name with version: \"$(python3 ./setup.py --name)>=$(python3 ./setup.py --version)\""
  type        = string
}
