////////////////////
// Global/General //
////////////////////

locals {
  tf_build_plan_args = tomap({
    project_id                     = var.project_id,
    region                         = var.region,
    build_monitoring_email_address = var.build_monitoring_email_address,
    github_owner                   = var.github_owner,
    github_repo_name               = var.github_repo_name,
    github_branch                  = var.github_branch,
    yaas_pip_package               = var.yaas_pip_package,
  })
}

///////////
// CI/CD //
///////////

module "cicd_infra" {
  source                               = "./1_cicd_infra"
  project_id                           = var.project_id
  region                               = var.region
  build_service_account_name           = var.build_service_account_name
  build_bucket_name_prefix             = var.build_bucket_name_prefix
  docker_artifact_registry_name        = var.docker_artifact_registry_name
  python_artifact_registry_name        = var.python_artifact_registry_name
  build_monitoring_topic_name          = var.build_monitoring_topic_name
  build_pubsub_monitoring_channel_name = var.build_pubsub_monitoring_channel_name
  build_email_monitoring_channel_name  = var.build_email_monitoring_channel_name
  build_monitoring_email_address       = var.build_monitoring_email_address
}

module "cicd_build" {
  source                               = "./2_cicd_build"
  project_id                           = var.project_id
  region                               = var.region
  build_service_account_email          = module.cicd_infra.build_service_account.email
  build_bucket_name                    = module.cicd_infra.build_bucket.name
  docker_artifact_registry_url         = module.cicd_infra.docker_repo_url
  python_artifact_registry_url         = module.cicd_infra.python_repo_url
  build_pubsub_monitoring_channel_name = module.cicd_infra.build_pubsub_monitoring_channel.display_name
  build_email_monitoring_channel_name  = module.cicd_infra.build_email_monitoring_channel.display_name
  docker_base_image                    = var.docker_base_image
  yaas_image_name                      = var.yaas_image_name
  yaas_dockerfile                      = var.yaas_dockerfile
  tf_build_trigger_name                = var.tf_build_trigger_name
  tf_build_template_filename           = var.tf_build_template_filename
  python_build_trigger_name            = var.python_build_trigger_name
  python_build_template_filename       = var.python_build_template_filename
  docker_build_trigger_name            = var.docker_build_trigger_name
  docker_build_template_filename       = var.docker_build_template_filename
  github_owner                         = var.github_owner
  github_repo_name                     = var.github_repo_name
  github_branch                        = var.github_branch
  yaas_pip_package                     = var.yaas_pip_package
  tf_build_plan_args                   = local.tf_build_plan_args
  depends_on                           = [module.cicd_infra]
}