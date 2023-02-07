////////////////////
// Global/General //
////////////////////

locals {
}

data "google_project" "project" {
  project_id = var.project_id
}

///////////////
// Cloud Run //
///////////////

resource "google_cloud_run_service" "hello" {
  project                    = var.project_id
  location                   = var.region
  name                       = var.run_name
  autogenerate_revision_name = true
  template {
    spec {
      containers {
        image = var.image_name_uri
      }
    }
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = 0
        "autoscaling.knative.dev/maxScale" = 100
      }
    }
  }
  traffic {
    percent         = 100
    latest_revision = true
  }
  metadata {
    annotations = {
      "run.googleapis.com/ingress" = "internal"
    }
  }
  // This is very important to let YAAS change the scaling params
  lifecycle {
    ignore_changes = [
      template.0.metadata.0.annotations,
    ]
  }
}