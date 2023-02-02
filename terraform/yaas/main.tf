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
  run_service_account_name    = var.run_service_account_name
  pubsub_service_account_name = var.pubsub_service_account_name
  // bucket
  bucket_name_prefix = var.bucket_name_prefix
  // pubsub
  pubsub_cal_creds_refresh_name  = var.pubsub_cal_creds_refresh_name
  pubsub_cache_refresh_name      = var.pubsub_cache_refresh_name
  pubsub_send_request_name       = var.pubsub_send_request_name
  pubsub_enact_request_name      = var.pubsub_enact_request_name
  pubsub_notification_topic_name = var.pubsub_notification_topic_name
  // caching
  cache_refresh_range_in_days = var.cache_refresh_range_in_days
  // scheduler
  scheduler_cron_timezone = var.scheduler_cron_timezone
  // scheduler: calendar
  scheduler_calendar_credentials_refresh_name                         = var.scheduler_calendar_credentials_refresh_name
  scheduler_calendar_credentials_refresh_cron_entry_triggering_minute = var.scheduler_calendar_credentials_refresh_cron_entry_triggering_minute
  // scheduler: cache
  scheduler_cache_refresh_name                         = var.scheduler_cache_refresh_name
  scheduler_cache_refresh_rate_in_hours                = var.scheduler_cache_refresh_rate_in_hours
  scheduler_cache_refresh_cron_entry_triggering_minute = var.scheduler_cache_refresh_cron_entry_triggering_minute
  // scheduler: request
  scheduler_request_name            = var.scheduler_request_name
  scheduler_request_rate_in_minutes = var.scheduler_request_rate_in_minutes
  // secrets
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
  run_sa_email    = module.yaas_infra.run_sa.email
  pubsub_sa_email = module.yaas_infra.pubsub_sa.email
  // bucket
  bucket_name = module.yaas_infra.bucket.name
  // pubsub
  pubsub_cal_creds_refresh_id  = module.yaas_infra.pubsub_cal_creds_refresh.id
  pubsub_cache_refresh_id      = module.yaas_infra.pubsub_cache_refresh.id
  pubsub_send_request_id       = module.yaas_infra.pubsub_send_request.id
  pubsub_enact_request_id      = module.yaas_infra.pubsub_enact_request.id
  pubsub_notification_topic_id = module.yaas_infra.pubsub_notification_topic.id
  // secrets
  secrets_calendar_credentials_id = local.secrets_calendar_credentials_id
  // image
  image_name_uri = var.image_name_uri
  // code
  log_level                                = var.log_level
  config_path                              = var.config_path
  service_path_update_calendar_credentials = var.service_path_update_calendar_credentials
  service_path_update_cache                = var.service_path_update_cache
  service_path_request_emission            = var.service_path_request_emission
  // cloud run
  run_name = var.run_name
  // monitoring
  monitoring_email_channel_name  = module.yaas_infra.monitoring_channel_email.id
  monitoring_pubsub_channel_name = module.yaas_infra.monitoring_channel_pubsub.id
  monitoring_alert_severity      = var.monitoring_alert_severity
  // monitoring: not executed - let at least 1 fail, therefore the '2 *' prefix
  monitoring_not_executed_align_period_in_seconds = tomap({
    calendar_credentials_refresh = 25 * 60 * 60
    cache_refresh                = 2 * var.scheduler_cache_refresh_rate_in_hours * 60 * 60
    send_request                 = 2 * var.scheduler_request_rate_in_minutes * 60
  })

  depends_on = [module.yaas_infra]
}