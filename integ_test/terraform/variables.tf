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
  description = "Integration tests Cloud Run name."
  type        = string
  default     = "integ-test"
}

///////////////
// Cloud SQL //
///////////////

variable "sql_name" {
  description = "Integration tests Cloud SQL name."
  type        = string
  default     = "integ-test"
}

variable "sql_database_version" {
  description = "Integration tests Cloud SQL name."
  type        = string
  default     = "POSTGRES_14"
}

////////////////////////
// YAAS: request body //
////////////////////////

variable "request_body_tmpl" {
  description = "Template for YAAS request body"
  type        = string
  default     = "templates/request_body.txt.tmpl"
}

variable "request_body" {
  description = "YAAS request body"
  type        = string
  default     = "request_body.txt"
}
