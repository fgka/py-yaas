////////////////////
// Global/General //
////////////////////

locals {
  // service accounts
  pubsub_sa_member = "serviceAccount:${var.pubsub_sa_email}"
  // config JSON
  terraform_module_root_dir = path.module
  config_json_tmpl          = "${local.terraform_module_root_dir}/${var.config_json_tmpl}"
  local_config_json         = "${local.terraform_module_root_dir}/output/config.json.local"
  // topic_to_pubsub_gcs
  batch_topic_to_pubsub_path  = "${var.topic_to_pubsub_gcs_path}/gcs"
  local_batch_topic_to_pubsub = "${local.terraform_module_root_dir}/output/topic_gcs.local"
  // scheduler
  run_sched_service_url     = module.yaas_sched.service_url
  pubsub_enact_standard_url = "${local.run_sched_service_url}${var.service_path_enact_standard_request}"
  pubsub_enact_gcs_url      = "${local.run_sched_service_url}${var.service_path_enact_gcs_batch_request}"
  // scaler
  run_scaler_service_url = module.yaas_scaler.service_url
  pubsub_command_url     = "${local.run_scaler_service_url}${var.service_path_command}"
}

/////////////////
// Config JSON //
/////////////////

resource "local_file" "config_json" {
  content = templatefile(local.config_json_tmpl, {
    CALENDAR_ID                 = var.calendar_id,
    SECRET_NAME                 = var.secrets_calendar_credentials_id,
    BUCKET_NAME                 = var.bucket_name,
    SQLITE_OBJECT_PATH          = var.sqlite_cache_path,
    PUBSUB_TOPIC_ENACT_STANDARD = var.pubsub_enact_standard_request_id
    TOPIC_TO_PUBSUB_PATH        = var.topic_to_pubsub_gcs_path
  })
  filename = local.local_config_json
}

resource "google_storage_bucket_object" "config_json" {
  name   = var.config_path
  source = local_file.config_json.filename
  bucket = var.bucket_name
}

//////////////////////
// Topic to Pub/Sub //
//////////////////////

resource "local_file" "topic_to_pubsub_gcs" {
  content  = var.pubsub_enact_gcs_batch_request_id
  filename = local.local_batch_topic_to_pubsub
}

resource "google_storage_bucket_object" "topic_to_pubsub_gcs" {
  name   = local.batch_topic_to_pubsub_path
  source = local_file.topic_to_pubsub_gcs.filename
  bucket = var.bucket_name
}

///////////////////////////
// Pub/Sub Subscriptions //
///////////////////////////

// Scaler

resource "google_pubsub_subscription" "command" {
  name                       = "${module.yaas_scaler.service.name}_command_http_push_subscription"
  topic                      = var.pubsub_command_id
  ack_deadline_seconds       = var.run_timeout
  message_retention_duration = "${var.pubsub_subscription_retention_in_sec}s"
  push_config {
    push_endpoint = local.pubsub_command_url
    oidc_token {
      service_account_email = var.run_scaler_sa_email
      audience              = local.run_scaler_service_url
    }
  }
  retry_policy {
    minimum_backoff = "${var.pubsub_subscription_min_retry_backoff_in_sec}s"
  }
}

// Scheduler

resource "google_pubsub_subscription" "enact_standard_request" {
  name                       = "${module.yaas_sched.service.name}_enact_standard_http_push_subscription"
  topic                      = var.pubsub_enact_standard_request_id
  ack_deadline_seconds       = var.run_timeout
  message_retention_duration = "${var.pubsub_subscription_retention_in_sec}s"
  push_config {
    push_endpoint = local.pubsub_enact_standard_url
    oidc_token {
      service_account_email = var.run_sched_sa_email
      audience              = local.run_sched_service_url
    }
  }
  retry_policy {
    minimum_backoff = "${var.pubsub_subscription_min_retry_backoff_in_sec}s"
  }
}

resource "google_pubsub_subscription" "enact_gcs_request" {
  name                       = "${module.yaas_sched.service.name}_enact_gcs_batch_http_push_subscription"
  topic                      = var.pubsub_enact_gcs_batch_request_id
  ack_deadline_seconds       = var.run_timeout
  message_retention_duration = "${var.pubsub_subscription_retention_in_sec}s"
  push_config {
    push_endpoint = local.pubsub_enact_gcs_url
    oidc_token {
      service_account_email = var.run_sched_sa_email
      audience              = local.run_sched_service_url
    }
  }
  retry_policy {
    minimum_backoff = "${var.pubsub_subscription_min_retry_backoff_in_sec}s"
  }
}

///////////////
// Cloud Run //
///////////////

// Scheduler

module "yaas_sched" {
  source     = "./modules/cr_service"
  project_id = var.project_id
  region     = var.region
  # cloud run
  run_name     = var.run_sched_name
  run_sa_email = var.run_sched_sa_email
  run_timeout  = var.run_timeout
  # code
  log_level      = var.log_level
  bucket_name    = var.bucket_name
  config_path    = var.config_path
  image_name_uri = var.sched_image_name_uri
  # monitoring
  monitoring_alert_severity      = var.monitoring_alert_severity
  monitoring_email_channel_name  = var.monitoring_email_channel_name
  monitoring_pubsub_channel_name = var.monitoring_pubsub_channel_name
}

// Scaler

module "yaas_scaler" {
  source     = "./modules/cr_service"
  project_id = var.project_id
  region     = var.region
  # cloud run
  run_name     = var.run_scaler_name
  run_sa_email = var.run_scaler_sa_email
  run_timeout  = var.run_timeout
  # code
  log_level      = var.log_level
  bucket_name    = var.bucket_name
  config_path    = var.config_path
  image_name_uri = var.scaler_image_name_uri
  # monitoring
  monitoring_alert_severity      = var.monitoring_alert_severity
  monitoring_email_channel_name  = var.monitoring_email_channel_name
  monitoring_pubsub_channel_name = var.monitoring_pubsub_channel_name
}

// pubsub SA

resource "google_cloud_run_service_iam_member" "run_pubsub_invoker" {
  for_each = toset([
    module.yaas_sched.service.name,
    module.yaas_scaler.service.name,
  ])
  service  = each.key
  location = var.region
  role     = "roles/run.invoker"
  member   = local.pubsub_sa_member
}
