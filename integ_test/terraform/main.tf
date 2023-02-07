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

resource "google_cloud_run_service" "main" {
  project                    = var.project_id
  location                   = var.region
  name                       = var.run_name
  autogenerate_revision_name = true
  template {
    spec {
      container_concurrency = 80
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
  metadata {
    annotations = {
      "run.googleapis.com/ingress" = "internal"
    }
  }
  // This is very important to let YAAS change the scaling params
  lifecycle {
    ignore_changes = [
      template.0.spec.0.container_concurrency,
      template.0.metadata.0.annotations["autoscaling.knative.dev/minScale"],
      template.0.metadata.0.annotations["autoscaling.knative.dev/maxScale"],
    ]
  }
}

///////////////
// Cloud SQL //
///////////////

resource "google_sql_database_instance" "main" {
  project          = var.project_id
  region           = var.region
  name             = var.sql_name
  database_version = var.sql_database_version

  settings {
    tier = "db-f1-micro"
  }
  // This is very important to let YAAS change the scaling params
  lifecycle {
    ignore_changes = [
      settings.0.tier,
    ]
  }
}