///////////////
// Cloud Run //
///////////////

output "run_yaas" {
  value = google_cloud_run_service.yaas
}
/////////////////
// Config JSON //
/////////////////

output "local_config_json" {
  value = local_file.config_json.filename
}

output "gcs_config_json" {
  value = "gs://${google_storage_bucket_object.config_json.bucket}/${google_storage_bucket_object.config_json.output_name}"
}

/////////////////////////////
// Monitoring and Alerting //
/////////////////////////////

output "alert_policy_error_log" {
  value = google_monitoring_alert_policy.alert_error_log
}

