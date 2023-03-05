//////////////////////
// Service Accounts //
//////////////////////

output "run_sa" {
  value = google_service_account.run_sa
}

output "pubsub_sa" {
  value = google_service_account.pubsub_sa
}

/////////////
// Buckets //
/////////////

output "bucket" {
  value = module.bucket.bucket
}

////////////////////
// Pub/Sub Topics //
////////////////////

output "pubsub_command" {
  value = module.pubsub_command
}

output "pubsub_enact_standard_request" {
  value = module.pubsub_enact_standard_request
}

output "pubsub_enact_gcs_batch_request" {
  value = module.pubsub_enact_gcs_batch_request
}

output "pubsub_notification_topic" {
  value = module.pubsub_notification_topic
}

///////////////////////
// Scheduler/Cronjob //
///////////////////////

output "scheduler_calendar_credentials_refresh" {
  value = google_cloud_scheduler_job.calendar_credentials_refresh
}

output "scheduler_cache_refresh" {
  value = google_cloud_scheduler_job.cache_refresh
}

output "scheduler_request_emission" {
  value = google_cloud_scheduler_job.request_emission
}

////////////////////
// Secret Manager //
////////////////////

output "secrets_calendar_credentials_version_ids" {
  value     = module.secrets_calendar_credentials.version_ids
  sensitive = false
}

output "secrets_calendar_credentials_ids" {
  value     = module.secrets_calendar_credentials.ids
  sensitive = false
}

/////////////////////////////
// Monitoring and Alerting //
/////////////////////////////

output "monitoring_channel_email" {
  value = google_monitoring_notification_channel.monitoring_email
}

output "monitoring_channel_pubsub" {
  value = google_monitoring_notification_channel.monitoring_pubsub
}
