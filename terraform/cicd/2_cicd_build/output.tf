
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

output "app_deploy_trigger" {
  value = google_cloudbuild_trigger.application
}
