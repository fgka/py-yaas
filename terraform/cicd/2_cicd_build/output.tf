
//////////////////////
// Service Accounts //
//////////////////////

output "tf_build_trigger" {
  value = google_cloudbuild_trigger.tf_cicd
}

output "tf_yaas_trigger" {
  value = google_cloudbuild_trigger.tf_infra
}

output "python_build_trigger" {
  value = google_cloudbuild_trigger.python
}

output "app_deploy_trigger" {
  value = google_cloudbuild_trigger.application
}
