////////////////////
// Global/General //
////////////////////

locals {
  // service accounts
  pubsub_sa_member    = "serviceAccount:${var.pubsub_sa_email}"
  run_sa_email_member = "serviceAccount:${var.run_sa_email}"
  // config JSON
  terraform_module_root_dir = path.module
  config_json_tmpl          = "${local.terraform_module_root_dir}/${var.config_json_tmpl}"
  local_config_json         = "${local.terraform_module_root_dir}/output/config.json.local"
  // topic_to_pubsub_gcs
  batch_topic_to_pubsub_path  = "${var.topic_to_pubsub_gcs_path}/gcs"
  local_batch_topic_to_pubsub = "${local.terraform_module_root_dir}/output/topic_gcs.local"
  // cloud run
  run_service_url = google_cloud_run_service.yaas.status[0].url
  // pubsub endpoints
  pubsub_command_url        = "${local.run_service_url}${var.service_path_command}"
  pubsub_enact_standard_url = "${local.run_service_url}${var.service_path_enact_standard_request}"
  pubsub_enact_gcs_url      = "${local.run_service_url}${var.service_path_enact_gcs_batch_request}"
  // monitoring
  monitoring_auto_close_in_seconds = var.monitoring_notification_auto_close_in_days * 24 * 60
  monitoring_alert_policies_error_log = tomap({
    email = {
      period_in_secs = var.monitoring_notification_email_rate_limit_in_minutes * 60,
      channel_name   = var.monitoring_email_channel_name,
    },
    pubsub = {
      period_in_secs = var.monitoring_notification_pubsub_rate_limit_in_minutes * 60,
      channel_name   = var.monitoring_pubsub_channel_name,
    },
  })
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

resource "google_pubsub_subscription" "command" {
  name                       = "${google_cloud_run_service.yaas.name}_command_http_push_subscription"
  topic                      = var.pubsub_command_id
  ack_deadline_seconds       = var.run_timeout
  message_retention_duration = "${var.pubsub_subscription_retention_in_sec}s"
  push_config {
    push_endpoint = local.pubsub_command_url
    oidc_token {
      service_account_email = var.run_sa_email
      audience              = local.run_service_url
    }
  }
  retry_policy {
    minimum_backoff = "${var.pubsub_subscription_min_retry_backoff_in_sec}s"
  }
}

resource "google_pubsub_subscription" "enact_standard_request" {
  name                       = "${google_cloud_run_service.yaas.name}_enact_standard_http_push_subscription"
  topic                      = var.pubsub_enact_standard_request_id
  ack_deadline_seconds       = var.run_timeout
  message_retention_duration = "${var.pubsub_subscription_retention_in_sec}s"
  push_config {
    push_endpoint = local.pubsub_enact_standard_url
    oidc_token {
      service_account_email = var.run_sa_email
      audience              = local.run_service_url
    }
  }
  retry_policy {
    minimum_backoff = "${var.pubsub_subscription_min_retry_backoff_in_sec}s"
  }
}

resource "google_pubsub_subscription" "enact_gcs_request" {
  name                       = "${google_cloud_run_service.yaas.name}_enact_gcs_batch_http_push_subscription"
  topic                      = var.pubsub_enact_gcs_batch_request_id
  ack_deadline_seconds       = var.run_timeout
  message_retention_duration = "${var.pubsub_subscription_retention_in_sec}s"
  push_config {
    push_endpoint = local.pubsub_enact_gcs_url
    oidc_token {
      service_account_email = var.run_sa_email
      audience              = local.run_service_url
    }
  }
  retry_policy {
    minimum_backoff = "${var.pubsub_subscription_min_retry_backoff_in_sec}s"
  }
}

///////////////
// Cloud Run //
///////////////

resource "google_cloud_run_service" "yaas" {
  project                    = var.project_id
  location                   = var.region
  name                       = var.run_name
  autogenerate_revision_name = true
  template {
    spec {
      container_concurrency = var.run_container_concurrency
      timeout_seconds       = var.run_timeout
      service_account_name  = var.run_sa_email
      containers {
        image = var.image_name_uri
        env {
          name  = "LOG_LEVEL"
          value = var.log_level
        }
        env {
          name  = "CONFIG_BUCKET_NAME"
          value = var.bucket_name
        }
        env {
          name  = "CONFIG_OBJECT_PATH"
          value = var.config_path
        }
        resources {
          limits = {
            cpu    = var.run_cpu
            memory = var.run_mem
          }
          requests = {
            cpu    = var.run_cpu
            memory = var.run_mem
          }
        }
      }
    }
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = var.run_min_instances
        "autoscaling.knative.dev/maxScale" = var.run_max_instances
      }
    }
  }
  traffic {
    percent         = 100
    latest_revision = true
  }
  metadata {
    annotations = {
      "run.googleapis.com/ingress" = "internal-and-cloud-load-balancing"
    }
  }
  lifecycle {
    ignore_changes = [
      template[0].spec[0].containers[0].image,
    ]
  }
}

// service SA

resource "google_cloud_run_service_iam_member" "run_agent" {
  service  = google_cloud_run_service.yaas.name
  location = var.region
  role     = "roles/run.serviceAgent"
  member   = local.run_sa_email_member
}

// pubsub SA

resource "google_cloud_run_service_iam_member" "run_pubsub_invoker" {
  service  = google_cloud_run_service.yaas.name
  location = var.region
  role     = "roles/run.invoker"
  member   = local.pubsub_sa_member
}

/////////////////////////////
// Monitoring and Alerting //
/////////////////////////////

resource "google_monitoring_alert_policy" "alert_error_log" {
  for_each     = local.monitoring_alert_policies_error_log
  display_name = "${google_cloud_run_service.yaas.name}-${each.key}-error-monitoring"
  documentation {
    content   = "Alerts for ${google_cloud_run_service.yaas.name} execution errors - ${each.key}"
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
    display_name = "Log severity >= ${var.monitoring_alert_severity} for cloud run service ${google_cloud_run_service.yaas.name}"
    condition_matched_log {
      filter = "resource.type=\"cloud_run_revision\"\nresource.labels.service_name=\"${google_cloud_run_service.yaas.name}\"\nseverity>=\"${var.monitoring_alert_severity}\""
    }
  }
  notification_channels = [each.value.channel_name]
}
