////////////////////
// Global/General //
////////////////////

locals {
  terraform_module_root_dir = path.module
  request_body_tmpl         = "${local.terraform_module_root_dir}/${var.request_body_tmpl}"
  request_body              = "${local.terraform_module_root_dir}/${var.request_body}"
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

////////////////
// Networking //
////////////////

resource "google_compute_network" "private_network" {
  provider = google-beta
  name     = "private-network"
}

resource "google_compute_global_address" "private_ip_address" {
  provider      = google-beta
  name          = "private-ip-address"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.private_network.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  provider                = google-beta
  network                 = google_compute_network.private_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
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
    ip_configuration {
      ipv4_enabled    = false
      require_ssl     = true
      private_network = google_compute_network.private_network.id
    }
  }
  // This is very important to let YAAS change the scaling params
  lifecycle {
    ignore_changes = [
      settings.0.tier,
    ]
  }
}

////////////////////////
// YAAS: request body //
////////////////////////

resource "local_file" "request_body" {
  content = templatefile(local.request_body_tmpl, {
    RUN_ID            = google_cloud_run_service.main.id,
    RUN_MIN_INSTANCES = google_cloud_run_service.main.template[0].metadata[0].annotations["autoscaling.knative.dev/minScale"],
    RUN_MAX_INSTANCES = google_cloud_run_service.main.template[0].metadata[0].annotations["autoscaling.knative.dev/maxScale"],
    RUN_CONCURRENCY   = google_cloud_run_service.main.template[0].spec[0].container_concurrency,
    SQL_ID            = google_sql_database_instance.main.connection_name,
    SQL_INSTANCE_TYPE = google_sql_database_instance.main.settings[0].tier,
  })
  filename = local.request_body
}
