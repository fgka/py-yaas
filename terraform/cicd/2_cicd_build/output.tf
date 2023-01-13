
//////////////////////
// Service Accounts //
//////////////////////

output "tf_build_trigger" {
  value = google_cloudbuild_trigger.tf_build
}

output "tf_yaas_trigger" {
  value = google_cloudbuild_trigger.tf_yaas
}

output "python_build_trigger" {
  value = google_cloudbuild_trigger.python
}

output "docker_build_trigger" {
  value = google_cloudbuild_trigger.docker
}

output "image_yaas_trigger" {
  value = google_cloudbuild_trigger.image_yaas
}