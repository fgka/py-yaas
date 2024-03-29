////////////////////
// Global/General //
////////////////////

locals {
  // service accounts
  run_sa_email_member = "serviceAccount:${var.run_sa_email}"
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

///////////////
// Cloud Run //
///////////////

resource "google_cloud_run_v2_service" "default" {
  project  = var.project_id
  location = var.region
  name     = var.run_name
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
  template {
    timeout                          = "${var.run_timeout}s"
    service_account                  = var.run_sa_email
    max_instance_request_concurrency = var.run_container_concurrency
    scaling {
      min_instance_count = var.run_min_instances
      max_instance_count = var.run_max_instances
    }
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
          "cpu"    = var.run_cpu
          "memory" = var.run_mem
        }
      }
    }
  }
  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }
  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
    ]
  }
}


// service SA

resource "google_cloud_run_v2_service_iam_member" "run_agent" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.default.name
  role     = "roles/run.serviceAgent"
  member   = local.run_sa_email_member
}

/////////////////////////////
// Monitoring and Alerting //
/////////////////////////////

resource "google_monitoring_alert_policy" "alert_error_log" {
  for_each     = local.monitoring_alert_policies_error_log
  display_name = "${google_cloud_run_v2_service.default.name}-${each.key}-error-monitoring"
  documentation {
    content   = "Alerts for ${google_cloud_run_v2_service.default.name} execution errors - ${each.key}"
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
    display_name = "Log severity >= ${var.monitoring_alert_severity} for cloud run service ${google_cloud_run_v2_service.default.name}"
    condition_matched_log {
      filter = "resource.type=\"cloud_run_revision\"\nresource.labels.service_name=\"${google_cloud_run_v2_service.default.name}\"\nseverity>=\"${var.monitoring_alert_severity}\""
    }
  }
  notification_channels = [each.value.channel_name]
}
