////////////////////
// Global/General //
////////////////////

locals {
  // system sa
  serverless_system_sa_iam_member = "serviceAccount:service-${data.google_project.project.number}@serverless-robot-prod.iam.gserviceaccount.com"
  scheduler_system_sa_iam_member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-cloudscheduler.iam.gserviceaccount.com"
  // scheduler
  scheduler_cron_entry_credentials_refresh = "${var.scheduler_calendar_credentials_refresh_cron_entry_triggering_minute} */${var.scheduler_cache_refresh_rate_in_hours} * * *"
  scheduler_cron_entry_cache_refresh       = "${var.scheduler_cache_refresh_cron_entry_triggering_minute} */${var.scheduler_cache_refresh_rate_in_hours} * * *"
  scheduler_cron_entry_request             = "*/${var.scheduler_request_rate_in_minutes} * * * *"
  // scheduler data
  cache_refresh_range_in_minutes = var.cache_refresh_range_in_days * 24 * 60
  calendar_creds_refresh_data    = "{\"to_be_ignored\": \"this not used anywhere\"}"
  scheduler_cache_refresh_data   = "{\"period_minutes\":${local.cache_refresh_range_in_minutes}, \"now_diff_minutes\":${var.scheduler_request_rate_in_minutes}}"
  scheduler_request_data         = "{\"period_minutes\":${var.scheduler_request_rate_in_minutes}, \"now_diff_minutes\":-1}"
}

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
  member  = local.serverless_system_sa_iam_member
}

////////////////////////////////////////
// Service Accounts: YAAS permissions //
////////////////////////////////////////

resource "google_project_iam_member" "yaas_permissions" {
  for_each = toset(var.run_service_account_roles)
  project  = var.project_id
  role     = each.key
  member   = google_service_account.run_sa.member
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
    "roles/storage.objectAdmin" = [
      google_service_account.run_sa.member,
    ]
  }
}

////////////////////
// Pub/Sub Topics //
////////////////////

module "pubsub_cal_creds_refresh" {
  source     = "github.com/GoogleCloudPlatform/cloud-foundation-fabric/modules/pubsub"
  project_id = var.project_id
  name       = var.pubsub_cal_creds_refresh_name
  iam = {
    "roles/pubsub.publisher" = [local.scheduler_system_sa_iam_member]
  }
}

module "pubsub_cache_refresh" {
  source     = "github.com/GoogleCloudPlatform/cloud-foundation-fabric/modules/pubsub"
  project_id = var.project_id
  name       = var.pubsub_cache_refresh_name
  iam = {
    "roles/pubsub.publisher" = [local.scheduler_system_sa_iam_member]
  }
}

module "pubsub_send_request" {
  source     = "github.com/GoogleCloudPlatform/cloud-foundation-fabric/modules/pubsub"
  project_id = var.project_id
  name       = var.pubsub_send_request_name
  iam = {
    "roles/pubsub.publisher" = [local.scheduler_system_sa_iam_member]
  }
}

module "pubsub_enact_request" {
  source     = "github.com/GoogleCloudPlatform/cloud-foundation-fabric/modules/pubsub"
  project_id = var.project_id
  name       = var.pubsub_enact_request_name
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

///////////////////////
// Scheduler/Cronjob //
///////////////////////

resource "google_cloud_scheduler_job" "calendar_credentials_refresh" {
  name        = var.scheduler_calendar_credentials_refresh_name
  description = "Cronjob to trigger YAAS calendar credentials OAuth2 refresh."
  schedule    = local.scheduler_cron_entry_credentials_refresh
  time_zone   = var.scheduler_cron_timezone
  pubsub_target {
    # topic.id is the topic's full resource name.
    topic_name = module.pubsub_cal_creds_refresh.topic.id
    data       = base64encode(local.calendar_creds_refresh_data)
  }
}

resource "google_cloud_scheduler_job" "cache_refresh" {
  name        = var.scheduler_cache_refresh_name
  description = "Cronjob to trigger YAAS calendar cache refresh."
  schedule    = local.scheduler_cron_entry_cache_refresh
  time_zone   = var.scheduler_cron_timezone
  pubsub_target {
    # topic.id is the topic's full resource name.
    topic_name = module.pubsub_cache_refresh.topic.id
    data       = base64encode(local.scheduler_cache_refresh_data)
  }
}

resource "google_cloud_scheduler_job" "request_emission" {
  name        = var.scheduler_request_name
  description = "Cronjob to trigger YAAS scaling request emission."
  schedule    = local.scheduler_cron_entry_request
  time_zone   = var.scheduler_cron_timezone
  pubsub_target {
    # topic.id is the topic's full resource name.
    topic_name = module.pubsub_enact_request.topic.id
    data       = base64encode(local.scheduler_request_data)
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
      "roles/secretmanager.secretVersionAdder" = [google_service_account.run_sa.member],
      "roles/secretmanager.secretAccessor"     = [google_service_account.run_sa.member],
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
