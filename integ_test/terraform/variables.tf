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

//////////////////
// Docker image //
//////////////////

variable "image_name_uri" {
  description = "Test docker application image URI. E.g.: LOCATION-docker.pkg.dev/PROJECT_ID/REPO_NAME/IMAGE_NAME[:LABEL]"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

///////////////
// Cloud Run //
///////////////

variable "run_name" {
  description = "YAAS Cloud Run name."
  type        = string
  default     = "yaas-run"
}
