////////////////////
// Global/General //
////////////////////

data "google_project" "project" {
  project_id = var.project_id
}

//////////////////////
// Service Accounts //
//////////////////////

data "google_service_account" "build_service_account" {
  account_id = var.build_service_account_email
}

////////////////////
// Build Triggers //
////////////////////

resource "google_cloudbuild_trigger" "tf" {
  location           = var.region
  name               = var.tf_build_trigger_name
  service_account    = data.google_service_account.build_service_account.id
  filename           = var.tf_build_template_filename
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
  substitutions = {
    _BUCKET_NAME          = var.build_bucket_name
    _PYTHON_BUILD_TRIGGER = google_cloudbuild_trigger.python.name
  }
  ignored_files = [
    "**"
  ]
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
  ignored_files = [
    "**"
  ]
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

resource "google_cloudbuild_trigger" "docker" {
  location           = var.region
  name               = var.docker_build_trigger_name
  service_account    = data.google_service_account.build_service_account.id
  filename           = var.docker_build_template_filename
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
  substitutions = {
    _BUCKET_NAME    = var.build_bucket_name
    _DOCKERFILE     = var.yaas_dockerfile
    _PIP_PKG_ARG    = var.yaas_pip_package
    _BASE_IMAGE     = var.docker_base_image
    _IMAGE_NAME     = var.yaas_image_name
    _AR_DOCKER_REPO = var.docker_artifact_registry_url
    _AR_PIP_REPO    = var.python_artifact_registry_url
  }
  ignored_files = [
    "**"
  ]
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
