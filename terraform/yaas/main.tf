////////////////////
// Global/General //
////////////////////

locals {
  secrets_calendar_credentials_prj_name = tomap(module.yaas_infra.secrets_calendar_credentials_ids)[var.secrets_calendar_credentials_name]
  secrets_calendar_credentials_prj_num  = replace(local.secrets_calendar_credentials_prj_name, var.project_id, data.google_project.project.number)
  secrets_calendar_credentials_id       = "${local.secrets_calendar_credentials_prj_num}/versions/latest"
}

data "google_project" "project" {
  project_id = var.project_id
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
  run_sched_service_account_name   = var.run_sched_service_account_name
  run_sched_service_account_roles  = var.run_sched_service_account_roles
  run_scaler_service_account_name  = var.run_scaler_service_account_name
  run_scaler_service_account_roles = var.run_scaler_service_account_roles
  pubsub_service_account_name      = var.pubsub_service_account_name
  // bucket
  bucket_name_prefix = var.bucket_name_prefix
  // pubsub
  pubsub_command_name                 = var.pubsub_command_name
  pubsub_enact_standard_request_name  = var.pubsub_enact_standard_request_name
  pubsub_enact_gcs_batch_request_name = var.pubsub_enact_gcs_batch_request_name
  pubsub_notification_topic_name      = var.pubsub_notification_topic_name
  // caching
  cache_refresh_range_in_days = var.cache_refresh_range_in_days
  // scheduler
  scheduler_cron_timezone = var.scheduler_cron_timezone
  // scheduler: calendar
  scheduler_calendar_credentials_refresh_name                         = var.scheduler_calendar_credentials_refresh_name
  scheduler_calendar_credentials_refresh_cron_entry_triggering_minute = var.scheduler_calendar_credentials_refresh_cron_entry_triggering_minute
  scheduler_calendar_credentials_refresh_rate_in_hours                = var.scheduler_calendar_credentials_refresh_rate_in_hours
  // scheduler: cache
  scheduler_cache_refresh_name                         = var.scheduler_cache_refresh_name
  scheduler_cache_refresh_rate_in_hours                = var.scheduler_cache_refresh_rate_in_hours
  scheduler_cache_refresh_cron_entry_triggering_minute = var.scheduler_cache_refresh_cron_entry_triggering_minute
  // scheduler: request
  scheduler_request_name            = var.scheduler_request_name
  scheduler_request_rate_in_minutes = var.scheduler_request_rate_in_minutes
  // secrets
  secrets_calendar_credentials_name = var.secrets_calendar_credentials_name
  secrets_calendar_credentials_file = var.secrets_calendar_credentials_file
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
  run_sched_sa_email  = module.yaas_infra.run_sched_sa.email
  run_scaler_sa_email = module.yaas_infra.run_scaler_sa.email
  pubsub_sa_email     = module.yaas_infra.pubsub_sa.email
  // bucket
  bucket_name = module.yaas_infra.bucket.name
  // pubsub
  pubsub_command_id                 = module.yaas_infra.pubsub_command.id
  pubsub_enact_standard_request_id  = module.yaas_infra.pubsub_enact_standard_request.id
  pubsub_enact_gcs_batch_request_id = module.yaas_infra.pubsub_enact_gcs_batch_request.id
  // secrets
  secrets_calendar_credentials_id = local.secrets_calendar_credentials_id
  // code
  calendar_id = var.calendar_id
  log_level   = var.log_level
  // scheduler
  run_sched_name       = var.run_sched_name
  sched_image_name_uri = var.sched_image_name_uri
  // scaler
  run_scaler_name       = var.run_scaler_name
  scaler_image_name_uri = var.scaler_image_name_uri
  // monitoring
  monitoring_email_channel_name  = module.yaas_infra.monitoring_channel_email.id
  monitoring_pubsub_channel_name = module.yaas_infra.monitoring_channel_pubsub.id
  monitoring_alert_severity      = var.monitoring_alert_severity
  // dependencies
  depends_on = [module.yaas_infra]
}
