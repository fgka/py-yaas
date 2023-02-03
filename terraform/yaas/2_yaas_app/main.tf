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
  local_config_json         = "${local.terraform_module_root_dir}/${var.config_json_tmpl}.local"
  // cloud run
  run_service_url = google_cloud_run_service.yaas.status[0].url
  // pubsub endpoints
  pubsub_calendar_credentials_refresh_url = "${local.run_service_url}${var.service_path_update_calendar_credentials}"
  pubsub_cache_refresh_url                = "${local.run_service_url}${var.service_path_update_cache}"
  pubsub_request_url                      = "${local.run_service_url}${var.service_path_request_emission}"
  pubsub_enact_url                        = "${local.run_service_url}${var.service_path_enact_request}"
  // monitoring
  monitoring_auto_close_in_seconds = var.monitoring_notification_auto_close_in_days * 24 * 60
  monitoring_alert_channel_type_to_name = tomap({
    email  = var.monitoring_email_channel_name,
    pubsub = var.monitoring_pubsub_channel_name
  })
  monitoring_alert_policies_error_log = tomap({
    email = {
      period_in_secs = var.monitoring_notification_email_rate_limit_in_minutes * 60,
      channel_name   = local.monitoring_alert_channel_type_to_name["email"]
    },
    pubsub = {
      period_in_secs = var.monitoring_notification_pubsub_rate_limit_in_minutes * 60,
      channel_name   = local.monitoring_alert_channel_type_to_name["pubsub"]
    },
  })
  // let at least 1 fail, therefore the '2 *' prefix
  monitoring_not_executed_align_period_in_seconds = tomap({
    calendar_credentials_refresh = var.monitoring_not_executed_align_period_in_seconds.calendar_credentials_refresh
    cache_refresh                = var.monitoring_not_executed_align_period_in_seconds.cache_refresh
    send_request                 = var.monitoring_not_executed_align_period_in_seconds.send_request
  })
  monitoring_alert_policies_not_executed = flatten([
    for method, period_in_sec in local.monitoring_not_executed_align_period_in_seconds : [
      for type, channel in local.monitoring_alert_channel_type_to_name : {
        channel_type         = type
        channel_name         = channel
        duration_in_secs     = local.monitoring_alert_policies_error_log[type].period_in_secs
        invoke_method        = method
        align_period_in_secs = period_in_sec
      }
    ]
  ])
}

data "google_project" "project" {
  project_id = var.project_id
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
    PUBSUB_TOPIC_ENACT_STANDARD = var.pubsub_enact_request_id
  })
  filename = local.local_config_json
}

resource "google_storage_bucket_object" "config_json" {
  name   = var.config_path
  source = local_file.config_json.filename
  bucket = var.bucket_name
}

///////////////////////////
// Pub/Sub Subscriptions //
///////////////////////////

resource "google_pubsub_subscription" "cal_creds_refresh" {
  name                       = "${google_cloud_run_service.yaas.name}_cal_creds_http_push_subscription"
  topic                      = var.pubsub_cal_creds_refresh_id
  ack_deadline_seconds       = var.run_timeout
  message_retention_duration = "${var.pubsub_subscription_retention_in_sec}s"
  push_config {
    push_endpoint = local.pubsub_calendar_credentials_refresh_url
    oidc_token {
      service_account_email = var.run_sa_email
      audience              = local.pubsub_calendar_credentials_refresh_url
    }
  }
  retry_policy {
    minimum_backoff = "${var.pubsub_subscription_min_retry_backoff_in_sec}s"
  }
}

resource "google_pubsub_subscription" "cache_refresh" {
  name                       = "${google_cloud_run_service.yaas.name}_cache_http_push_subscription"
  topic                      = var.pubsub_cache_refresh_id
  ack_deadline_seconds       = var.run_timeout
  message_retention_duration = "${var.pubsub_subscription_retention_in_sec}s"
  push_config {
    push_endpoint = local.pubsub_cache_refresh_url
    oidc_token {
      service_account_email = var.run_sa_email
      audience              = local.run_service_url
    }
  }
  retry_policy {
    minimum_backoff = "${var.pubsub_subscription_min_retry_backoff_in_sec}s"
  }
}

resource "google_pubsub_subscription" "send_request" {
  name                       = "${google_cloud_run_service.yaas.name}_send_http_push_subscription"
  topic                      = var.pubsub_send_request_id
  ack_deadline_seconds       = var.run_timeout
  message_retention_duration = "${var.pubsub_subscription_retention_in_sec}s"
  push_config {
    push_endpoint = local.pubsub_request_url
    oidc_token {
      service_account_email = var.run_sa_email
      audience              = local.run_service_url
    }
  }
  retry_policy {
    minimum_backoff = "${var.pubsub_subscription_min_retry_backoff_in_sec}s"
  }
}

resource "google_pubsub_subscription" "enact_request" {
  name                       = "${google_cloud_run_service.yaas.name}_enact_http_push_subscription"
  topic                      = var.pubsub_enact_request_id
  ack_deadline_seconds       = var.run_timeout
  message_retention_duration = "${var.pubsub_subscription_retention_in_sec}s"
  push_config {
    push_endpoint = local.pubsub_enact_url
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
      template.0.spec.0.containers.0.image,
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
    display_name = "Log severity >= ${var.monitoring_alert_severity} for function ${google_cloud_run_service.yaas.name}"
    condition_matched_log {
      filter = "resource.labels.function_name=\"${google_cloud_run_service.yaas.name}\"\nseverity>=\"${var.monitoring_alert_severity}\""
    }
  }
  notification_channels = [each.value.channel_name]
}

// TODO
resource "google_monitoring_alert_policy" "alert_not_executed" {
  for_each     = { for index, val in local.monitoring_alert_policies_not_executed : index => val }
  display_name = "${google_cloud_run_service.yaas.name}-${each.value.invoke_method}-${each.value.channel_type}-not-executed-monitoring"
  documentation {
    content   = "Alert if Cloud Run service ${google_cloud_run_service.yaas.name} is not executed - ${each.value.invoke_method}-${each.value.channel_type}"
    mime_type = "text/markdown"
  }
  combiner = "OR"
  conditions {
    display_name = "Executions for ${google_cloud_run_service.yaas.name} [COUNT]"
    condition_threshold {
      filter          = "metric.type=\"cloudfunctions.googleapis.com/function/execution_count\" resource.type=\"cloud_function\" resource.label.\"function_name\"=\"${google_cloud_run_service.yaas.name}\""
      threshold_value = 1
      trigger {
        count = 1
      }
      duration   = "${each.value.duration_in_secs}s"
      comparison = "COMPARISON_LT"
      aggregations {
        alignment_period     = "${each.value.align_period_in_secs}s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_COUNT"
      }
    }
  }
  notification_channels = [each.value.channel_name]
}
