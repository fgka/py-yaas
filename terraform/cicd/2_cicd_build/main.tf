////////////////////
// Global/General //
////////////////////

locals {
  # terraform args
  tf_cicd_plan_args_str = join(" ", [for key, val in var.tf_cicd_plan_args : "-var \"${key}=${val}\""])
  tf_yaas_plan_args_str = join(" ", [for key, val in var.tf_yaas_plan_args : "-var \"${key}=${val}\""])
  # absolute paths
  root_dir                       = var.run_cicd ? "" : "../../"
  code_root_dir                  = "${local.root_dir}code"
  docker_root_dir                = "${local.root_dir}docker"
  terraform_cicd_module_root_dir = "${local.root_dir}terraform/cicd/${path.module}"
  terraform_yaas_root_dir        = "${local.root_dir}terraform/yaas"
  # wait script
  wait_for_run_ready_script_filename = "${local.terraform_cicd_module_root_dir}/${var.wait_for_run_ready_script_filename}"
  # cloud build template files
  tf_build_template_filename      = "${local.terraform_cicd_module_root_dir}/${var.tf_build_template_filename}"
  tf_yaas_template_filename       = "${local.terraform_cicd_module_root_dir}/${var.tf_yaas_template_filename}"
  python_build_template_filename  = "${local.terraform_cicd_module_root_dir}/${var.python_build_template_filename}"
  image_build_template_filename   = "${local.terraform_cicd_module_root_dir}/${var.image_build_template_filename}"
  tf_backend_tf_template_filename = "${local.terraform_cicd_module_root_dir}/${var.tf_backend_tf_template_filename}"
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
  filename           = local.tf_build_template_filename
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
  substitutions = {
    _TF_BUCKET_NAME       = var.terraform_bucket_name
    _TF_MODULE            = "cicd"
    _TF_BACKEND_TF_TMPL   = local.tf_backend_tf_template_filename
    _BUCKET_NAME          = var.build_bucket_name
    _TF_PLAN_ARGS         = local.tf_cicd_plan_args_str
    _PYTHON_BUILD_TRIGGER = google_cloudbuild_trigger.python.name
    _INFRA_BUILD_TRIGGER  = google_cloudbuild_trigger.tf_yaas.name
  }
  ignored_files = var.tf_build_ignored_files
  included_files = [
    "${local.terraform_cicd_module_root_dir}/**",
    local.tf_build_template_filename,
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
  filename           = local.tf_yaas_template_filename
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
  substitutions = {
    _TF_BUCKET_NAME     = var.terraform_bucket_name
    _TF_MODULE          = "yaas"
    _TF_BACKEND_TF_TMPL = local.tf_backend_tf_template_filename
    _BUCKET_NAME        = var.build_bucket_name
    _TF_PLAN_ARGS       = local.tf_yaas_plan_args_str
    _SERVICE_NAME       = var.run_name
    _WAIT_SCRIPT        = local.wait_for_run_ready_script_filename
  }
  ignored_files = var.tf_build_ignored_files
  included_files = [
    "${local.terraform_yaas_root_dir}/**",
    local.tf_yaas_template_filename,
    local.wait_for_run_ready_script_filename,
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
  filename           = local.python_build_template_filename
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
  substitutions = {
    _BUCKET_NAME          = var.build_bucket_name
    _AR_PIP_REPO          = var.python_artifact_registry_url
    _DOCKER_BUILD_TRIGGER = google_cloudbuild_trigger.application.name
  }
  ignored_files = var.tf_build_ignored_files
  included_files = [
    "${local.code_root_dir}/**",
    local.python_build_template_filename,
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
  filename           = local.image_build_template_filename
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
    _WAIT_SCRIPT    = local.wait_for_run_ready_script_filename
    _CR_CONCURRENCY = var.run_container_concurrency
  }
  ignored_files = var.tf_build_ignored_files
  included_files = [
    "${local.docker_root_dir}/**",
    local.image_build_template_filename,
    local.wait_for_run_ready_script_filename,
  ]
  github {
    owner = var.github_owner
    name  = var.github_repo_name
    push {
      branch = "^${var.github_branch}$"
    }
  }
}
