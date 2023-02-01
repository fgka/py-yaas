////////////////////
// Global/General //
////////////////////

data "google_project" "project" {
  project_id = var.project_id
}

//////////////////////
// Service Accounts //
//////////////////////

resource "google_service_account" "run_sa" {
  account_id   = var.run_service_account_name
  display_name = "Cloud Run Service Account Identity"
}

resource "google_service_account" "scheduler_sa" {
  account_id   = var.scheduler_service_account_name
  display_name = "Scheduler Service Account Identity"
}

resource "google_service_account" "pubsub_sa" {
  account_id   = var.pubsub_service_account_name
  display_name = "Pub/Sub Service Account Subscription Identity"
}

// https://cloud.google.com/run/docs/troubleshooting
resource "google_project_iam_member" "serverless_service_agent" {
  for_each = toset([
    "roles/serverless.serviceAgent",
    "roles/run.serviceAgent",
  ])
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:service-${data.google_project.project.number}@serverless-robot-prod.iam.gserviceaccount.com"
}

/////////////
// Buckets //
/////////////

module "bucket" {
  source     = "github.com/GoogleCloudPlatform/cloud-foundation-fabric/modules/gcs"
  project_id = var.project_id
  prefix     = var.bucket_name_prefix
  name       = data.google_project.project.number
  iam = {
    "roles/storage.legacyBucketReader" = [
      google_service_account.run_sa.member,
    ]
  }
}

////////////////////
// Pub/Sub Topics //
////////////////////

module "pubsub_topic" {
  source     = "github.com/GoogleCloudPlatform/cloud-foundation-fabric/modules/pubsub"
  project_id = var.project_id
  name       = var.pubsub_topic_name
  iam = {
    "roles/pubsub.publisher" = [google_service_account.run_sa.member]
  }
}

module "pubsub_notification_topic" {
  source     = "github.com/GoogleCloudPlatform/cloud-foundation-fabric/modules/pubsub"
  project_id = var.project_id
  name       = var.pubsub_notification_topic_name
  iam = {
    "roles/pubsub.publisher" = [google_service_account.run_sa.member]
  }
}

////////////////////
// Secret Manager //
////////////////////

module "secrets_calendar_credentials" {
  source     = "github.com/GoogleCloudPlatform/cloud-foundation-fabric/modules/secret-manager"
  project_id = var.project_id
  secrets = {
    "${var.secrets_calendar_credentials_name}" = [var.region]
  }
  versions = {
    "${var.secrets_calendar_credentials_name}" = {
      v1 = { enabled = true, data = "ADD YOUR SECRET CONTENT MANUALLY AND NOT HERE" }
    }
  }
  iam = {
    "${var.secrets_calendar_credentials_name}" = {
      "roles/secretmanager.secretVersionAdder" = [google_service_account.run_sa.member]
    }
  }
}

/////////////////////////////
// Monitoring and Alerting //
/////////////////////////////

resource "google_monitoring_notification_channel" "monitoring_email" {
  display_name = var.monitoring_email_channel_name
  type         = "email"
  labels = {
    email_address = var.monitoring_email_address
  }
}

resource "google_monitoring_notification_channel" "monitoring_pubsub" {
  display_name = var.monitoring_pubsub_channel_name
  type         = "pubsub"
  labels = {
    topic = module.pubsub_notification_topic.id
  }
}
