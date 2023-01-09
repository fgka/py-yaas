
//////////////////////
// Service Accounts //
//////////////////////

output "python_build_trigger" {
  value = google_cloudbuild_trigger.python
}

output "docker_base_build_trigger" {
  value = google_cloudbuild_trigger.docker_base
}

output "docker_app_build_trigger" {
  value = google_cloudbuild_trigger.docker_app
}
