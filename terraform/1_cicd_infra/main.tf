////////////////////
// Global/General //
////////////////////

data "google_project" "project" {
  project_id = var.project_id
}

//////////////////////
// Service Accounts //
//////////////////////

module "build_service_account" {
  source       = "github.com/GoogleCloudPlatform/cloud-foundation-fabric/modules/iam-service-account"
  project_id   = var.project_id
  name         = var.build_service_account_name
  generate_key = false
  iam_project_roles = {
    "${var.project_id}" = [
      "roles/cloudbuild.builds.builder",
    ]
  }
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
    "roles/storage.legacyBucketReader" = [
      module.build_service_account.iam_email,
    ]
  }
}


///////////////////////
// Artifact Registry //
///////////////////////

module "docker_repo" {
  source     = "github.com/GoogleCloudPlatform/cloud-foundation-fabric/modules/artifact-registry"
  project_id = var.project_id
  location   = var.region
  id         = var.docker_artifact_registry_name
  format     = "DOCKER"
  iam = {
    "roles/artifactregistry.writer" = [
      module.build_service_account.iam_email,
    ]
  }
}

module "python_repo" {
  source     = "github.com/GoogleCloudPlatform/cloud-foundation-fabric/modules/artifact-registry"
  project_id = var.project_id
  location   = var.region
  id         = var.python_artifact_registry_name
  format     = "PYTHON"
  iam = {
    "roles/artifactregistry.writer" = [
      module.build_service_account.iam_email,
    ]
  }
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
    email_address = var.build_notification_monitoring_email_address
  }
}
