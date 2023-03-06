///////////////
// Cloud Run //
///////////////

output "service" {
  value = google_cloud_run_service.default
}

output "service_url" {
  value = google_cloud_run_service.default.status[0].url
}

/////////////////////////////
// Monitoring and Alerting //
/////////////////////////////

output "alert_policy_error_log" {
  value = google_monitoring_alert_policy.alert_error_log
}
