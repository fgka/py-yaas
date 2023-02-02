///////////////
// Cloud Run //
///////////////

output "run_yaas" {
  value = google_cloud_run_service.yaas
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

/////////////////////////////
// Monitoring and Alerting //
/////////////////////////////

output "alert_policy_error_log" {
  value = google_monitoring_alert_policy.alert_error_log
}

output "alert_policy_not_executed" {
  value = google_monitoring_alert_policy.alert_not_executed
}