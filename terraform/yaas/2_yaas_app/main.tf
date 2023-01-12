////////////////////
// Global/General //
////////////////////

locals {
  // service accounts
  run_sa_email_member = "serviceAccount:${var.run_sa_email}"
  pubsub_sa_member    = "serviceAccount:${var.pubsub_sa_email}"
  // scheduler
  scheduler_cache_refresh_url        = "${google_cloud_run_service.yaas.status[0].url}${var.service_path_update_cache}"
  scheduler_request_url              = "${google_cloud_run_service.yaas.status[0].url}${var.service_path_request_emission}"
  scheduler_cron_entry_cache_refresh = "${var.scheduler_cache_refresh_cron_entry_triggering_minute} */${var.scheduler_cache_refresh_rate_in_hours} * * *"
  scheduler_cron_entry_request       = "*/${var.scheduler_request_rate_in_minutes} * * * *"
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
    cache_update     = 2 * var.scheduler_cache_refresh_rate_in_hours * 60 * 60
    request_emission = 2 * var.scheduler_request_rate_in_minutes * 60
  })
  monitoring_alert_policies_not_executed = flatten([
    for method, period_in_sesc in local.monitoring_not_executed_align_period_in_seconds : [
      for type, channel in local.monitoring_alert_channel_type_to_name : {
        channel_type         = type
        channel_name         = channel
        duration_in_secs     = local.monitoring_alert_policies_error_log[type].period_in_secs
        invoke_method        = method
        align_period_in_secs = period_in_sesc
      }
    ]
  ])
}

data "google_project" "project" {
  project_id = var.project_id
}

///////////////////////////
// Pub/Sub Subscriptions //
///////////////////////////

resource "google_pubsub_subscription" "run" {
  name                       = "${google_cloud_run_service.yaas.name}_http_push_subscription"
  topic                      = var.pubsub_topic_id
  ack_deadline_seconds       = var.run_timeout
  message_retention_duration = "${var.pubsub_subscription_retention_in_sec}s"
  push_config {
    push_endpoint = google_cloud_run_service.yaas.status[0].url
    oidc_token {
      service_account_email = var.run_sa_email
      audience              = google_cloud_run_service.yaas.status[0].url
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

///////////////////////
// Scheduler/Cronjob //
///////////////////////

resource "google_cloud_scheduler_job" "cache_refresh" {
  name        = var.scheduler_cache_refresh_name
  description = "Cronjob to trigger YAAS calendar cache refresh."
  schedule    = local.scheduler_cron_entry_cache_refresh
  time_zone   = var.scheduler_cron_timezone
  http_target {
    http_method = "POST"
    uri         = local.scheduler_cache_refresh_url
    oidc_token {
      service_account_email = var.scheduler_sa_email
    }
  }
}

resource "google_cloud_scheduler_job" "request_emission" {
  name        = var.scheduler_request_name
  description = "Cronjob to trigger YAAS scaling request emission."
  schedule    = local.scheduler_cron_entry_request
  time_zone   = var.scheduler_cron_timezone
  http_target {
    http_method = "POST"
    uri         = local.scheduler_request_url
    oidc_token {
      service_account_email = var.scheduler_sa_email
    }
  }
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
