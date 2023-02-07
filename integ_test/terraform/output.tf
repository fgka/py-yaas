/////////////
// Modules //
/////////////

output "cloud_run" {
  value = google_cloud_run_service.main
}

output "cloud_sql" {
  value = google_sql_database_instance.main
  sensitive = true
}