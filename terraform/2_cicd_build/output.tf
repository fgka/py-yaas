
//////////////////////
// Service Accounts //
//////////////////////

output "python_build_trigger" {
  value = google_cloudbuild_trigger.python
}

output "docker_build_trigger" {
  value = google_cloudbuild_trigger.docker
}
