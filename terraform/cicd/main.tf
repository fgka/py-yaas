////////////////////
// Global/General //
////////////////////

locals {
  common_tf_plan_args = tomap({
    project_id = var.project_id,
    region     = var.region,
  })
  tf_cicd_plan_args = merge(local.common_tf_plan_args, tomap({
    build_monitoring_email_address = var.build_monitoring_email_address,
    monitoring_email_address       = var.monitoring_email_address,
    github_owner                   = var.github_owner,
    github_repo_name               = var.github_repo_name,
    github_branch                  = var.github_branch,
    yaas_pip_package               = var.yaas_pip_package,
    }),
  var.tf_cicd_plan_args)
  tf_infra_plan_args = merge(local.common_tf_plan_args, tomap({
    run_name                 = var.run_name
    monitoring_email_address = var.monitoring_email_address,
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
  source     = "./2_cicd_build"
  project_id = var.project_id
  region     = var.region
  // service accounts
  tf_build_service_account_email = module.cicd_infra.tf_build_service_account.email
  build_service_account_email    = module.cicd_infra.build_service_account.email
  // resources
  build_bucket_name                    = module.cicd_infra.build_bucket.name
  docker_artifact_registry_url         = module.cicd_infra.docker_repo_url
  python_artifact_registry_url         = module.cicd_infra.python_repo_url
  build_pubsub_monitoring_channel_name = module.cicd_infra.build_pubsub_monitoring_channel.display_name
  build_email_monitoring_channel_name  = module.cicd_infra.build_email_monitoring_channel.display_name
  // docker image
  docker_base_image = var.docker_base_image
  yaas_image_name   = var.yaas_image_name
  yaas_dockerfile   = var.yaas_dockerfile
  image_name_uri    = var.image_name_uri
  // cloud run
  run_name = var.run_name
  // build triggers
  tf_build_trigger_name          = var.tf_build_trigger_name
  tf_build_template_filename     = var.tf_build_template_filename
  tf_yaas_trigger_name           = var.tf_yaas_trigger_name
  tf_yaas_template_filename      = var.tf_yaas_template_filename
  python_build_trigger_name      = var.python_build_trigger_name
  python_build_template_filename = var.python_build_template_filename
  app_build_trigger_name         = var.app_build_trigger_name
  image_build_template_filename  = var.image_build_template_filename
  // github
  github_owner     = var.github_owner
  github_repo_name = var.github_repo_name
  github_branch    = var.github_branch
  // code
  yaas_pip_package = var.yaas_pip_package
  // terraform plan args
  tf_cicd_plan_args      = local.tf_cicd_plan_args
  tf_yaas_plan_args      = local.tf_infra_plan_args
  tf_build_ignored_files = var.tf_build_ignored_files
  depends_on             = [module.cicd_infra]
}