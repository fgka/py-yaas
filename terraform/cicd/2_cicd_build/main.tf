////////////////////
// Global/General //
////////////////////

locals {
  # terraform args
  # YES there is a <'> wrapping the "-var" argument.
  # To know why: https://github.com/hashicorp/terraform/issues/17032#issuecomment-365703492
  tf_cicd_plan_args_str = join(" ", [for key, val in var.tf_cicd_plan_args : "-var '${key}=${val}'"])
  tf_yaas_plan_args_str = join(" ", [for key, val in var.tf_yaas_plan_args : "-var '${key}=${val}'"])
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
resource "google_cloudbuild_trigger" "tf_cicd" {
  location           = var.region
  name               = var.tf_build_trigger_name
  service_account    = data.google_service_account.tf_build_service_account.id
  filename           = local.tf_build_template_filename
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
  substitutions = {
    _TF_BUCKET_NAME           = var.terraform_bucket_name
    _TF_MODULE                = "cicd"
    _TF_BACKEND_TF_TMPL       = local.tf_backend_tf_template_filename
    _BUCKET_NAME              = var.build_bucket_name
    _TF_PLAN_ARGS             = local.tf_cicd_plan_args_str
    _PYTHON_BUILD_TRIGGER_LST = join("@", [for trigger in google_cloudbuild_trigger.python : trigger.name])
    _INFRA_BUILD_TRIGGER      = google_cloudbuild_trigger.tf_infra.name
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
resource "google_cloudbuild_trigger" "tf_infra" {
  location           = var.region
  name               = var.tf_yaas_trigger_name
  service_account    = data.google_service_account.tf_build_service_account.id
  filename           = local.tf_yaas_template_filename
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
  substitutions = {
    _TF_BUCKET_NAME         = var.terraform_bucket_name
    _TF_MODULE              = "yaas"
    _TF_BACKEND_TF_TMPL     = local.tf_backend_tf_template_filename
    _BUCKET_NAME            = var.build_bucket_name
    _TF_PLAN_ARGS           = local.tf_yaas_plan_args_str
    _SCHEDULER_SERVICE_NAME = var.yaas_service_to_run_name.scheduler
    _SCALER_SERVICE_NAME    = var.yaas_service_to_run_name.scaler
    _WAIT_SCRIPT            = local.wait_for_run_ready_script_filename
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
  for_each           = toset(var.yaas_py_modules)
  location           = var.region
  name               = "${var.python_build_trigger_name}-${each.key}"
  service_account    = data.google_service_account.build_service_account.id
  filename           = local.python_build_template_filename
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
  substitutions = {
    _CODE_DIR                 = "./code/${each.key}"
    _BUCKET_NAME              = var.build_bucket_name
    _AR_PIP_REPO              = var.python_artifact_registry_url
    _DOCKER_BUILD_TRIGGER_LST = join("@", [for trigger in google_cloudbuild_trigger.application : trigger.name])
  }
  ignored_files = var.tf_build_ignored_files
  included_files = [
    "${local.code_root_dir}/${each.key}/**",
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
  for_each           = var.yaas_service_to_package
  location           = var.region
  name               = "${var.app_build_trigger_name}-${each.key}"
  service_account    = data.google_service_account.build_service_account.id
  filename           = local.image_build_template_filename
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
  substitutions = {
    _BUCKET_NAME    = var.build_bucket_name
    _DOCKERFILE     = var.yaas_dockerfile
    _PIP_PKG_LST    = "${join("@", var.yaas_pip_package)}"
    _BASE_IMAGE     = var.docker_base_image
    _IMAGE_NAME     = "${var.yaas_image_name}-${each.key}"
    _AR_DOCKER_REPO = var.docker_artifact_registry_url
    _AR_PIP_REPO    = var.python_artifact_registry_url
    _SERVICE_NAME   = lookup(var.yaas_service_to_run_name, each.key)
    _WAIT_SCRIPT    = local.wait_for_run_ready_script_filename
    _CR_CONCURRENCY = var.run_container_concurrency
    _PY_PACKAGE     = each.value
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
