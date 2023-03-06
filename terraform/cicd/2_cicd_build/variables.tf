////////////////////
// Global/General //
////////////////////

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

variable "tf_build_service_account_email" {
  description = "Service account to build terraform"
  type        = string
}

variable "build_service_account_email" {
  description = "Service account to build artefacts"
  type        = string
}

/////////////
// Buckets //
/////////////

variable "build_bucket_name" {
  description = "Bucket name to store build artefacts."
  type        = string
}

variable "terraform_bucket_name" {
  description = "Bucket name to store terraform states."
  type        = string
}

///////////////////////
// Artifact Registry //
///////////////////////

variable "docker_artifact_registry_url" {
  description = "Cloud Run YAAS docker image registry full name."
  type        = string
}

variable "python_artifact_registry_url" {
  description = "Python YAAS package registry full name."
  type        = string
}

////////////
// Docker //
////////////

variable "docker_base_image" {
  description = "Docker base image. Only change if you know what you are doing."
  type        = string
  default     = "python:buster"
}

variable "yaas_image_name" {
  description = "YAAS docker application image."
  type        = string
  default     = "yaas"
}

variable "yaas_dockerfile" {
  description = "YAAS application Dockerfile. Only change if you know what you are doing."
  type        = string
  default     = "./docker/Dockerfile"
}

///////////////
// Cloud Run //
///////////////

variable "run_name" {
  description = "YAAS Cloud Run name."
  type        = string
  default     = "yaas-run"
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

variable "python_build_template_filename" {
  description = "Cloud Build template for Python code. Only change if you know what you are doing."
  type        = string
  default     = "cloudbuild/cloudbuild_py.yaml"
}

variable "app_build_trigger_name" {
  description = "Cloud Build trigger for Docker image."
  type        = string
  default     = "yaas-application"
}

variable "image_build_template_filename" {
  description = "Cloud Build template for docker image. Only change if you know what you are doing."
  type        = string
  default     = "cloudbuild/cloudbuild_image.yaml"
}

variable "wait_for_run_ready_script_filename" {
  description = "BASH script for waiting until Cloud Run is ready. Only change if you know what you are doing."
  type        = string
  default     = "scripts/wait_for_run_ready.sh"
}

variable "tf_build_trigger_name" {
  description = "Cloud Build trigger for CI/CD Terraform code."
  type        = string
  default     = "yaas-tf-cicd"
}

variable "tf_build_template_filename" {
  description = "Cloud Build template for CI/CD Terraform code. Only change if you know what you are doing."
  type        = string
  default     = "cloudbuild/cloudbuild_tf_cicd.yaml"
}

variable "tf_yaas_trigger_name" {
  description = "Cloud Build trigger for YAAS infrastructure Terraform code."
  type        = string
  default     = "yaas-tf-infra"
}

variable "tf_yaas_template_filename" {
  description = "Cloud Build template for YAAS infrastructure Terraform code. Only change if you know what you are doing."
  type        = string
  default     = "cloudbuild/cloudbuild_tf_infra.yaml"
}

variable "tf_backend_tf_template_filename" {
  description = "Cloud Build template for backend.tf. Only change if you know what you are doing."
  type        = string
  default     = "templates/backend.tf.tmpl"
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

variable "yaas_py_modules" {
  description = "Python modules. Dot not change, unless you know what you are doing."
  type        = list(string)
  default     = ["core", "cli", "service"]
}

///////////////
// Terraform //
///////////////

variable "tf_cicd_plan_args" {
  description = "CI/CD Terraform args"
  type        = map(any)
  default     = {}
}

variable "tf_yaas_plan_args" {
  description = "YAAS infrastructure Terraform args"
  type        = map(any)
  default     = {}
}

variable "tf_build_ignored_files" {
  description = "Which files to be ignored in all builds, typically documentation"
  type        = list(string)
  default     = ["**/*.md", "**/doc/*"]
}
