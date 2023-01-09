////////////////////
// Global/General //
////////////////////

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
  yaas_base_image_name                 = var.yaas_base_image_name
  yaas_app_image_name                  = var.yaas_app_image_name
  yaas_base_dockerfile                 = var.yaas_base_dockerfile
  yaas_app_dockerfile                  = var.yaas_app_dockerfile
  python_build_trigger_name            = var.python_build_trigger_name
  python_build_template_filename       = var.python_build_template_filename
  docker_base_build_trigger_name       = var.docker_base_build_trigger_name
  docker_app_build_trigger_name        = var.docker_app_build_trigger_name
  docker_build_template_filename       = var.docker_build_template_filename
  tf_build_trigger_name                = var.tf_build_trigger_name
  github_owner                         = var.github_owner
  github_repo_name                     = var.github_repo_name
  github_branch                        = var.github_branch
  depends_on                           = [module.cicd_infra]
}