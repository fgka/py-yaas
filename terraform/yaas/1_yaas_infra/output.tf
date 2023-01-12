//////////////////////
// Service Accounts //
//////////////////////

output "run_sa" {
  value = google_service_account.run_sa
}

output "scheduler_sa" {
  value = google_service_account.scheduler_sa
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

output "pubsub_topic" {
  value = module.pubsub_topic
}

output "pubsub_notification_topic" {
  value = module.pubsub_notification_topic
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