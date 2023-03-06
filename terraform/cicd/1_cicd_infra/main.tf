////////////////////
// Global/General //
////////////////////

locals {
  // service account
  cloud_build_sa_email  = "${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
  cloud_build_sa_member = "serviceAccount:${local.cloud_build_sa_email}"
  // artifact registry
  artifact_registry_repos = tomap({
    docker = google_artifact_registry_repository.docker_repo,
    python = google_artifact_registry_repository.python_repo,
  })
  artifact_registry_urls = tomap({
    for k, v in local.artifact_registry_repos :
    k => "${v.location}-${lower(v.format)}.pkg.dev/${v.project}/${v.name}"
  })
  // monitoring
  monitoring_auto_close_in_seconds = var.monitoring_notification_auto_close_in_days * 24 * 60
  monitoring_alert_policies_error_log = tomap({
    email = {
      period_in_secs = var.monitoring_notification_email_rate_limit_in_minutes * 60,
      channel_name   = google_monitoring_notification_channel.build_email_monitoring_channel.id,
    },
    pubsub = {
      period_in_secs = var.monitoring_notification_pubsub_rate_limit_in_minutes * 60,
      channel_name   = google_monitoring_notification_channel.build_pubsub_monitoring_channel.id,
    },
  })
}

data "google_project" "project" {
  project_id = var.project_id
}

//////////////////////
// Service Accounts //
//////////////////////

module "tf_build_service_account" { #tfsec:ignore:google-iam-no-project-level-service-account-impersonation
  source       = "github.com/GoogleCloudPlatform/cloud-foundation-fabric/modules/iam-service-account"
  project_id   = var.project_id
  name         = var.tf_build_service_account_name
  generate_key = false
  iam_project_roles = {
    "${data.google_project.project.id}" = [
      "roles/artifactregistry.admin",
      "roles/cloudbuild.builds.editor",
      "roles/cloudscheduler.admin",
      "roles/editor",
      "roles/iam.serviceAccountAdmin",
      "roles/iam.serviceAccountUser",
      "roles/logging.logWriter",
      "roles/monitoring.admin",
      "roles/pubsub.admin",
      "roles/resourcemanager.projectIamAdmin",
      "roles/run.admin",
      "roles/secretmanager.admin",
      "roles/storage.admin",
    ]
  }
}

module "build_service_account" { #tfsec:ignore:google-iam-no-project-level-service-account-impersonation
  source       = "github.com/GoogleCloudPlatform/cloud-foundation-fabric/modules/iam-service-account"
  project_id   = var.project_id
  name         = var.build_service_account_name
  generate_key = false
  iam_project_roles = {
    "${data.google_project.project.id}" = [
      "roles/artifactregistry.admin",
      "roles/cloudbuild.builds.editor",
      "roles/iam.serviceAccountUser",
      "roles/run.admin",
      "roles/storage.admin",
    ]
  }
}

resource "google_artifact_registry_repository_iam_member" "iam_members" {
  for_each   = local.artifact_registry_repos
  provider   = google-beta
  project    = var.project_id
  location   = each.value.location
  repository = each.value.name
  role       = "roles/artifactregistry.writer"
  member     = module.build_service_account.iam_email
}

resource "google_project_iam_member" "cloud_build_roles" { #tfsec:ignore:google-iam-no-privileged-service-accounts
  project = var.project_id
  role    = "roles/editor"
  member  = local.cloud_build_sa_member
}

/////////////
// Buckets //
/////////////

module "build_bucket" { #tfsec:ignore:google-storage-bucket-encryption-customer-key
  source     = "github.com/GoogleCloudPlatform/cloud-foundation-fabric/modules/gcs"
  project_id = var.project_id
  prefix     = var.build_bucket_name_prefix
  name       = data.google_project.project.number
  iam = {
    "roles/storage.objectAdmin" = [
      module.build_service_account.iam_email,
    ]
  }
  lifecycle_rules = {
    clean_up = {
      action = {
        type = "Delete"
      }
      condition = {
        age = var.object_age_in_days
      }
    }
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

resource "google_monitoring_alert_policy" "alert_error_log" {
  for_each     = local.monitoring_alert_policies_error_log
  display_name = "CI/CD-${each.key}-error-monitoring"
  documentation {
    content   = "Alerts for YAAS CI/CD build execution errors - ${each.key}"
    mime_type = "text/markdown"
  }
  alert_strategy {
    notification_rate_limit {
      period = "${each.value.period_in_secs}s"
    }
    auto_close = "${local.monitoring_auto_close_in_seconds}s"
  }
  combiner = "OR"
  conditions {
    display_name = "ERROR in log for YAAS CI/CD build"
    condition_matched_log {
      filter = "resource.type=\"build\"\ntextPayload=~\"ERROR\""
    }
  }
  notification_channels = [each.value.channel_name]
}
