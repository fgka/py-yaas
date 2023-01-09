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

resource "google_cloudbuild_trigger" "python" {
  location           = var.region
  name               = var.python_build_trigger_name
  service_account    = data.google_service_account.build_service_account.id
  filename           = var.python_build_template_filename
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
  substitutions = {
    _BUCKET_NAME = var.build_bucket_name
    _AR_PIP_REPO = var.python_artifact_registry_url
  }
  github {
    owner = var.github_owner
    name  = var.github_repo_name
    push {
      branch = "^${var.github_branch}$"
    }
  }
}

resource "google_cloudbuild_trigger" "docker_base" {
  location           = var.region
  name               = var.docker_base_build_trigger_name
  service_account    = data.google_service_account.build_service_account.id
  filename           = var.docker_build_template_filename
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
  substitutions = {
    _BUCKET_NAME     = var.build_bucket_name
    _DOCKERFILE      = var.yaas_base_dockerfile
    _PIP_INSTALL_ARG = ""
    _BASE_IMAGE      = var.docker_base_image
    _IMAGE_NAME      = var.yaas_base_image_name
    _AR_DOCKER_REPO  = var.docker_artifact_registry_url
    _AR_PIP_REPO     = var.python_artifact_registry_url
  }
  github {
    owner = var.github_owner
    name  = var.github_repo_name
    push {
      branch = "^${var.github_branch}$"
    }
  }
}

resource "google_cloudbuild_trigger" "docker_app" {
  location           = var.region
  name               = var.docker_app_build_trigger_name
  service_account    = data.google_service_account.build_service_account.id
  filename           = var.docker_build_template_filename
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
  substitutions = {
    _BUCKET_NAME     = var.build_bucket_name
    _DOCKERFILE      = var.yaas_app_dockerfile
    _PIP_INSTALL_ARG = var.yaas_py_package_name
    _BASE_IMAGE      = var.yaas_base_image_name
    _IMAGE_NAME      = var.yaas_app_image_name
    _AR_DOCKER_REPO  = var.docker_artifact_registry_url
    _AR_PIP_REPO     = var.python_artifact_registry_url
  }
  github {
    owner = var.github_owner
    name  = var.github_repo_name
    push {
      branch = "^${var.github_branch}$"
    }
  }
}
