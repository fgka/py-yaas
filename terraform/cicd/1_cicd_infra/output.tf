
//////////////////////
// Service Accounts //
//////////////////////

output "tf_build_service_account" {
  value = module.tf_build_service_account.service_account
}

output "build_service_account" {
  value = module.build_service_account.service_account
}

/////////////
// Buckets //
/////////////

output "build_bucket" {
  value = module.build_bucket.bucket
}

///////////////////////
// Artifact Registry //
///////////////////////

output "docker_repo" {
  value = google_artifact_registry_repository.docker_repo
}

output "docker_repo_url" {
  value = lookup(local.artifact_registry_urls, "docker", null)
}

output "python_repo" {
  value = google_artifact_registry_repository.python_repo
}

output "python_repo_url" {
  value = "https://${lookup(local.artifact_registry_urls, "python", null)}"
}

////////////
// PubSub //
////////////

output "build_monitoring_topic" {
  value = module.build_monitoring_topic.topic
}

/////////////////////////////
// Monitoring and Alerting //
/////////////////////////////

output "build_pubsub_monitoring_channel" {
  value = google_monitoring_notification_channel.build_pubsub_monitoring_channel
}

output "build_email_monitoring_channel" {
  value = google_monitoring_notification_channel.build_email_monitoring_channel
}

output "alert_error_log" {
  value = google_monitoring_alert_policy.alert_error_log
}
