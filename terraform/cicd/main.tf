////////////////////
// Global/General //
////////////////////

locals {
  // helpers
  yaas_service_to_run_name_pairs = [for service, name in var.yaas_service_to_run_name : "\"${service}\"=\"${name}\""]
  yaas_service_to_package_pairs  = [for service, pkg in var.yaas_service_to_package : "\"${service}\"=\"${pkg}\""]
  yaas_pip_package_lst           = [for pkg in var.yaas_pip_package : "\"${pkg}\""]
  yaas_py_modules_lst            = [for pkg in var.yaas_py_modules : "\"${pkg}\""]
  // plan args
  common_tf_plan_args = tomap({
    project_id     = var.project_id,
    region         = var.region,
    calendar_id    = var.calendar_id,
    gmail_username = var.gmail_username,
  })
  tf_cicd_plan_args = merge(local.common_tf_plan_args, tomap({
    terraform_bucket_name          = var.terraform_bucket_name
    build_monitoring_email_address = var.build_monitoring_email_address,
    monitoring_email_address       = var.monitoring_email_address,
    github_owner                   = var.github_owner,
    github_repo_name               = var.github_repo_name,
    github_branch                  = var.github_branch,
    yaas_pip_package               = "[${join(",", local.yaas_pip_package_lst)}]",
    yaas_py_modules                = "[${join(",", local.yaas_py_modules_lst)}]",
    yaas_service_to_run_name       = "{${join(",", local.yaas_service_to_run_name_pairs)}}",
    yaas_service_to_package        = "{${join(",", local.yaas_service_to_package_pairs)}}",
    }),
  var.tf_cicd_plan_args)
  tf_infra_plan_args = merge(local.common_tf_plan_args, tomap({
    run_sched_name                    = var.yaas_service_to_run_name.scheduler
    run_scaler_name                   = var.yaas_service_to_run_name.scaler
    run_container_concurrency         = var.run_container_concurrency
    secrets_calendar_credentials_file = var.secrets_calendar_credentials_file
    monitoring_email_address          = var.monitoring_email_address,
    }),
  var.tf_infra_plan_args)
}

///////////
// CI/CD //
///////////

module "cicd_infra" {
  // basics
  source     = "./1_cicd_infra"
  project_id = var.project_id
  region     = var.region
  // service accounts
  tf_build_service_account_name = var.tf_build_service_account_name
  build_service_account_name    = var.build_service_account_name
  // resources
  build_bucket_name_prefix      = var.build_bucket_name_prefix
  object_age_in_days            = var.object_age_in_days
  docker_artifact_registry_name = var.docker_artifact_registry_name
  python_artifact_registry_name = var.python_artifact_registry_name
  // monitoring
  build_monitoring_topic_name          = var.build_monitoring_topic_name
  build_pubsub_monitoring_channel_name = var.build_pubsub_monitoring_channel_name
  build_email_monitoring_channel_name  = var.build_email_monitoring_channel_name
  build_monitoring_email_address       = var.build_monitoring_email_address
}

module "cicd_build" {
  // basics
  source   = "./2_cicd_build"
  region   = var.region
  run_cicd = var.run_cicd
  // service accounts
  tf_build_service_account_email = module.cicd_infra.tf_build_service_account.email
  build_service_account_email    = module.cicd_infra.build_service_account.email
  // resources
  terraform_bucket_name        = var.terraform_bucket_name
  build_bucket_name            = module.cicd_infra.build_bucket.name
  docker_artifact_registry_url = module.cicd_infra.docker_repo_url
  python_artifact_registry_url = module.cicd_infra.python_repo_url
  // docker image
  docker_base_image = var.docker_base_image
  yaas_image_name   = var.yaas_image_name
  yaas_dockerfile   = var.yaas_dockerfile
  // cloud run
  yaas_service_to_run_name  = var.yaas_service_to_run_name
  yaas_service_to_package   = var.yaas_service_to_package
  run_container_concurrency = var.run_container_concurrency
  // build triggers
  tf_build_trigger_name     = var.tf_build_trigger_name
  tf_yaas_trigger_name      = var.tf_yaas_trigger_name
  python_build_trigger_name = var.python_build_trigger_name
  app_build_trigger_name    = var.app_build_trigger_name
  // github
  github_owner     = var.github_owner
  github_repo_name = var.github_repo_name
  github_branch    = var.github_branch
  // code
  yaas_py_modules  = var.yaas_py_modules
  yaas_pip_package = var.yaas_pip_package
  // terraform plan args
  tf_cicd_plan_args      = local.tf_cicd_plan_args
  tf_yaas_plan_args      = local.tf_infra_plan_args
  tf_build_ignored_files = var.tf_build_ignored_files
  // dependencies
  depends_on = [module.cicd_infra]
}
