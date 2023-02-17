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

//////////
// APIs //
//////////

variable "minimum_apis" {
  description = "Minimum APIs to activate in the YAAS project. Only change if you know what you are doing."
  type        = list(string)
  default = [
    "artifactregistry.googleapis.com",
    "cloudapis.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "pubsub.googleapis.com",
    "secretmanager.googleapis.com",
    "servicemanagement.googleapis.com",
    "serviceusage.googleapis.com",
    "storage.googleapis.com",
  ]
}

/////////////
// Buckets //
/////////////

variable "tf_state_bucket_name_prefix" {
  description = "Prefix to name the terraform state bucket, the suffix is the project numerical ID."
  type        = string
  default     = "yaas-terraform"
}

////////////////
// backend.tf //
////////////////

variable "backend_tf_modules" {
  description = "Modules with their own Terraform state. Only change if you know what you are doing."
  type        = list(string)
  default = [
    "cicd",
    "yaas",
  ]
}

variable "backend_tf_tmpl" {
  description = "Template for backend.tf"
  type        = string
  default     = "templates/backend.tf.tmpl"
}

variable "backend_tf" {
  description = "Where to store backend.tf"
  type        = string
  default     = "backend.tf"
}