////////////////////
// Global/General //
////////////////////

locals {
  artifact_registry_repos = tomap({
    docker = google_artifact_registry_repository.docker_repo,
    python = google_artifact_registry_repository.python_repo,
  })
  artifact_registry_urls = tomap({
    for k, v in local.artifact_registry_repos :
    k => "${v.location}-${lower(v.format)}.pkg.dev/${v.project}/${v.name}"
  })
}

data "google_project" "project" {
  project_id = var.project_id
}

//////////////////////
// Service Accounts //
//////////////////////

module "tf_build_service_account" {
  source       = "github.com/GoogleCloudPlatform/cloud-foundation-fabric/modules/iam-service-account"
  project_id   = var.project_id
  name         = var.tf_build_service_account_name
  generate_key = false
  iam_project_roles = {
    "${data.google_project.project.id}" = [
      "roles/artifactregistry.admin",
      "roles/cloudbuild.builds.editor",
      "roles/iam.serviceAccountAdmin",
      "roles/iam.serviceAccountUser",
      "roles/logging.logWriter",
      "roles/monitoring.admin",
      "roles/pubsub.admin",
      "roles/resourcemanager.projectIamAdmin",
      "roles/storage.admin",
    ]
  }
}

module "build_service_account" {
  source       = "github.com/GoogleCloudPlatform/cloud-foundation-fabric/modules/iam-service-account"
  project_id   = var.project_id
  name         = var.build_service_account_name
  generate_key = false
  iam_project_roles = {
    "${data.google_project.project.id}" = [
      "roles/cloudbuild.builds.builder",
      "roles/iam.serviceAccountUser",
      "roles/logging.logWriter",
    ]
  }
}

resource "google_artifact_registry_repository_iam_binding" "bindings" {
  for_each   = local.artifact_registry_repos
  provider   = google-beta
  project    = var.project_id
  location   = each.value.location
  repository = each.value.name
  role       = "roles/artifactregistry.writer"
  members    = [module.build_service_account.iam_email]
}

/////////////
// Buckets //
/////////////

module "build_bucket" {
  source     = "github.com/GoogleCloudPlatform/cloud-foundation-fabric/modules/gcs"
  project_id = var.project_id
  prefix     = var.build_bucket_name_prefix
  name       = data.google_project.project.number
  iam = {
    "roles/storage.objectAdmin" = [
      module.build_service_account.iam_email,
    ]
  }
}

///////////////////////
// Artifact Registry //
///////////////////////

resource "google_artifact_registry_repository" "docker_repo" {
  provider      = google-beta
  project       = var.project_id
  location      = var.region
  format        = "DOCKER"
  repository_id = var.docker_artifact_registry_name
}

resource "google_artifact_registry_repository" "python_repo" {
  provider      = google-beta
  project       = var.project_id
  location      = var.region
  format        = "PYTHON"
  repository_id = var.python_artifact_registry_name
}

////////////
// PubSub //
////////////

module "build_monitoring_topic" {
  source     = "github.com/GoogleCloudPlatform/cloud-foundation-fabric/modules/pubsub"
  project_id = var.project_id
  name       = var.build_monitoring_topic_name
  iam = {
    "roles/pubsub.admin" = [
      module.build_service_account.iam_email,
    ]
  }
}

/////////////////////////////
// Monitoring and Alerting //
/////////////////////////////

resource "google_monitoring_notification_channel" "build_pubsub_monitoring_channel" {
  display_name = var.build_pubsub_monitoring_channel_name
  type         = "pubsub"
  labels = {
    topic = module.build_monitoring_topic.id
  }
}

resource "google_monitoring_notification_channel" "build_email_monitoring_channel" {
  display_name = var.build_email_monitoring_channel_name
  type         = "email"
  labels = {
    email_address = var.build_monitoring_email_address
  }
}
