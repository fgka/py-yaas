////////////////////
// Global/General //
////////////////////

locals {
  tf_cicd_plan_args_str = join(" ", [for key, val in var.tf_cicd_plan_args : "-var \"${key}=${val}\""])
  tf_yaas_plan_args_str = join(" ", [for key, val in var.tf_yaas_plan_args : "-var \"${key}=${val}\""])
}

data "google_project" "project" {
  project_id = var.project_id
}

//////////////////////
// Service Accounts //
//////////////////////

data "google_service_account" "tf_build_service_account" {
  account_id = var.tf_build_service_account_email
}

data "google_service_account" "build_service_account" {
  account_id = var.build_service_account_email
}

////////////////////
// Build Triggers //
////////////////////

// CI/CD itself
resource "google_cloudbuild_trigger" "tf_build" {
  location           = var.region
  name               = var.tf_build_trigger_name
  service_account    = data.google_service_account.tf_build_service_account.id
  filename           = var.tf_build_template_filename
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
  substitutions = {
    _BUCKET_NAME          = var.build_bucket_name
    _TF_PLAN_ARGS         = local.tf_cicd_plan_args_str
    _PYTHON_BUILD_TRIGGER = google_cloudbuild_trigger.python.name
    _INFRA_BUILD_TRIGGER  = google_cloudbuild_trigger.tf_yaas.name
  }
  ignored_files = var.tf_build_ignored_files
  included_files = [
    "terraform/cicd/**",
    var.tf_build_template_filename,
  ]
  github {
    owner = var.github_owner
    name  = var.github_repo_name
    push {
      branch = "^${var.github_branch}$"
    }
  }
}

// application infrastructure
resource "google_cloudbuild_trigger" "tf_yaas" {
  location           = var.region
  name               = var.tf_yaas_trigger_name
  service_account    = data.google_service_account.tf_build_service_account.id
  filename           = var.tf_yaas_template_filename
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
  substitutions = {
    _BUCKET_NAME  = var.build_bucket_name
    _TF_PLAN_ARGS = local.tf_yaas_plan_args_str
  }
  ignored_files = var.tf_build_ignored_files
  included_files = [
    "terraform/yaas/**",
    var.tf_yaas_template_filename,
  ]
  github {
    owner = var.github_owner
    name  = var.github_repo_name
    push {
      branch = "^${var.github_branch}$"
    }
  }
}

// builds python wheel
resource "google_cloudbuild_trigger" "python" {
  location           = var.region
  name               = var.python_build_trigger_name
  service_account    = data.google_service_account.build_service_account.id
  filename           = var.python_build_template_filename
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
  substitutions = {
    _BUCKET_NAME          = var.build_bucket_name
    _AR_PIP_REPO          = var.python_artifact_registry_url
    _DOCKER_BUILD_TRIGGER = google_cloudbuild_trigger.docker.name
  }
  ignored_files = var.tf_build_ignored_files
  included_files = [
    "code/**",
    var.python_build_template_filename,
  ]
  github {
    owner = var.github_owner
    name  = var.github_repo_name
    push {
      branch = "^${var.github_branch}$"
    }
  }
}

// application docker image
resource "google_cloudbuild_trigger" "docker" {
  location           = var.region
  name               = var.docker_build_trigger_name
  service_account    = data.google_service_account.build_service_account.id
  filename           = var.docker_build_template_filename
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
  substitutions = {
    _BUCKET_NAME          = var.build_bucket_name
    _DOCKERFILE           = var.yaas_dockerfile
    _PIP_PKG_ARG          = var.yaas_pip_package
    _BASE_IMAGE           = var.docker_base_image
    _IMAGE_NAME           = var.yaas_image_name
    _AR_DOCKER_REPO       = var.docker_artifact_registry_url
    _AR_PIP_REPO          = var.python_artifact_registry_url
    _IMAGE_DEPLOY_TRIGGER = google_cloudbuild_trigger.image_yaas.name
    _SERVICE_NAME         = var.run_name
  }
  ignored_files = var.tf_build_ignored_files
  included_files = [
    "docker/**",
    var.docker_build_template_filename,
  ]
  github {
    owner = var.github_owner
    name  = var.github_repo_name
    push {
      branch = "^${var.github_branch}$"
    }
  }
}

// application deployment
resource "google_cloudbuild_trigger" "image_yaas" {
  location           = var.region
  name               = var.image_yaas_trigger_name
  service_account    = data.google_service_account.tf_build_service_account.id
  filename           = var.image_yaas_template_filename
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
  substitutions = {
    _BUCKET_NAME  = var.build_bucket_name
    _SERVICE_NAME = var.run_name
    _IMAGE_URL    = var.image_name_uri
  }
  ignored_files = var.tf_build_ignored_files
  included_files = [
    var.image_yaas_template_filename,
  ]
  github {
    owner = var.github_owner
    name  = var.github_repo_name
    push {
      branch = "^${var.github_branch}$"
    }
  }
}