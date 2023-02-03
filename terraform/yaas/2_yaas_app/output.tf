///////////////
// Cloud Run //
///////////////

output "run_yaas" {
  value = google_cloud_run_service.yaas
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