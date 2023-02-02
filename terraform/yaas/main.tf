////////////////////
// Global/General //
////////////////////

locals {
  secrets_calendar_credentials_id_map = tomap(module.yaas_infra.secrets_calendar_credentials_ids)
  secrets_calendar_credentials_id     = "${local.secrets_calendar_credentials_id_map[var.secrets_calendar_credentials_name]}/versions/latest"
}

//////////
// YAAS //
//////////

module "yaas_infra" {
  // basics
  source     = "./1_yaas_infra"
  project_id = var.project_id
  region     = var.region
  // service accounts
  run_service_account_name       = var.run_service_account_name
  scheduler_service_account_name = var.scheduler_service_account_name
  pubsub_service_account_name    = var.pubsub_service_account_name
  // resources
  bucket_name_prefix                = var.bucket_name_prefix
  pubsub_topic_name                 = var.pubsub_topic_name
  pubsub_notification_topic_name    = var.pubsub_notification_topic_name
  secrets_calendar_credentials_name = var.secrets_calendar_credentials_name
  // monitoring
  monitoring_email_channel_name  = var.monitoring_email_channel_name
  monitoring_pubsub_channel_name = var.monitoring_pubsub_channel_name
  monitoring_email_address       = var.monitoring_email_address
}

module "yaas_app" {
  // basics
  source     = "./2_yaas_app"
  project_id = var.project_id
  region     = var.region
  // service accounts
  run_sa_email       = module.yaas_infra.run_sa.email
  scheduler_sa_email = module.yaas_infra.scheduler_sa.email
  pubsub_sa_email    = module.yaas_infra.pubsub_sa.email
  // resources
  bucket_name                                  = module.yaas_infra.bucket.name
  pubsub_topic_id                              = module.yaas_infra.pubsub_topic.id
  pubsub_notification_topic_id                 = module.yaas_infra.pubsub_notification_topic.id
  pubsub_subscription_retention_in_sec         = var.pubsub_subscription_retention_in_sec
  pubsub_subscription_min_retry_backoff_in_sec = var.pubsub_subscription_min_retry_backoff_in_sec
  secrets_calendar_credentials_id              = local.secrets_calendar_credentials_id
  // code
  image_name_uri                = var.image_name_uri
  log_level                     = var.log_level
  config_path                   = var.config_path
  service_path_update_cache     = var.service_path_update_cache
  service_path_request_emission = var.service_path_request_emission
  // cloud run
  run_name                  = var.run_name
  run_cpu                   = var.run_cpu
  run_mem                   = var.run_mem
  run_container_concurrency = var.run_container_concurrency
  run_timeout               = var.run_timeout
  run_min_instances         = var.run_min_instances
  run_max_instances         = var.run_max_instances
  // scheduler
  scheduler_cron_timezone = var.scheduler_cron_timezone
  // scheduler: calendar
  scheduler_calendar_credentials_refresh_name                         = var.scheduler_calendar_credentials_refresh_name
  scheduler_calendar_credentials_refresh_cron_entry_triggering_minute = var.scheduler_calendar_credentials_refresh_cron_entry_triggering_minute
  // scheduler: cache
  scheduler_cache_refresh_name                         = var.scheduler_cache_refresh_name
  scheduler_cache_refresh_data                         = var.scheduler_cache_refresh_data
  scheduler_cache_refresh_rate_in_hours                = var.scheduler_cache_refresh_rate_in_hours
  scheduler_cache_refresh_cron_entry_triggering_minute = var.scheduler_cache_refresh_cron_entry_triggering_minute
  // scheduler: request
  scheduler_request_name            = var.scheduler_request_name
  scheduler_request_data            = var.scheduler_request_data
  scheduler_request_rate_in_minutes = var.scheduler_request_rate_in_minutes
  // monitoring
  monitoring_email_channel_name                        = module.yaas_infra.monitoring_channel_email.id
  monitoring_pubsub_channel_name                       = module.yaas_infra.monitoring_channel_pubsub.id
  monitoring_alert_severity                            = var.monitoring_alert_severity
  monitoring_notification_email_rate_limit_in_minutes  = var.monitoring_notification_email_rate_limit_in_minutes
  monitoring_notification_pubsub_rate_limit_in_minutes = var.monitoring_notification_pubsub_rate_limit_in_minutes
  monitoring_notification_auto_close_in_days           = var.monitoring_notification_auto_close_in_days
  depends_on                                           = [module.yaas_infra]
}