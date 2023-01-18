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

///////////////////////////
// Cloud Build templates //
///////////////////////////

data "template_file" "tf_yaas_template_filename" {
  template = "${file("${path.module}/${var.tf_yaas_template_filename_tmpl}")}"
  vars = {
    TF_TEMPLATE_SCRIPT_CONTENT = file(var.wait_for_run_ready_script_filename)
  }
}

resource "local_file" "tf_yaas_template_filename" {
  content  = data.template_file.tf_yaas_template_filename.rendered
  filename = "${path.module}/tf_yaas_template_filename.yaml"
}

data "template_file" "image_build_template_filename" {
  template = "${file("${path.module}/${var.image_build_template_filename_tmpl}")}"
  vars = {
    TF_TEMPLATE_SCRIPT_CONTENT = file(var.wait_for_run_ready_script_filename)
  }
}

resource "local_file" "image_build_template_filename" {
  content  = data.template_file.tf_yaas_template_filename.rendered
  filename = "${path.module}/image_build_template_filename.yaml"
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
  filename           = local_file.tf_yaas_template_filename.filename
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
  substitutions = {
    _BUCKET_NAME  = var.build_bucket_name
    _TF_PLAN_ARGS = local.tf_yaas_plan_args_str
    _SERVICE_NAME = var.run_name
  }
  ignored_files = var.tf_build_ignored_files
  included_files = [
    "terraform/yaas/**",
    var.wait_for_run_ready_script_filename,
    var.tf_yaas_template_filename_tmpl,
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
    _DOCKER_BUILD_TRIGGER = google_cloudbuild_trigger.application.name
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

// application image
resource "google_cloudbuild_trigger" "application" {
  location           = var.region
  name               = var.app_build_trigger_name
  service_account    = data.google_service_account.build_service_account.id
  filename           = local_file.image_build_template_filename.filename
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
  substitutions = {
    _BUCKET_NAME    = var.build_bucket_name
    _DOCKERFILE     = var.yaas_dockerfile
    _PIP_PKG_ARG    = var.yaas_pip_package
    _BASE_IMAGE     = var.docker_base_image
    _IMAGE_NAME     = var.yaas_image_name
    _AR_DOCKER_REPO = var.docker_artifact_registry_url
    _AR_PIP_REPO    = var.python_artifact_registry_url
    _SERVICE_NAME   = var.run_name
  }
  ignored_files = var.tf_build_ignored_files
  included_files = [
    "docker/**",
    var.wait_for_run_ready_script_filename,
    var.image_build_template_filename_tmpl,
  ]
  github {
    owner = var.github_owner
    name  = var.github_repo_name
    push {
      branch = "^${var.github_branch}$"
    }
  }
}
