////////////////////
// Global/General //
////////////////////

locals {
  # Cloud Build SA
  cloud_build_sa_email        = "${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
  cloud_build_sa_email_member = "serviceAccount:${local.cloud_build_sa_email}"
  # backend.tf
  terraform_module_root_dir = path.module
  backend_tf_tmpl           = "${local.terraform_module_root_dir}/${var.backend_tf_tmpl}"
  backend_tf                = "${local.terraform_module_root_dir}/output/${var.backend_tf}"
  output_filenames = [
    for local_filename in local_file.backend_tf : local_filename.filename
  ]
}

data "google_project" "project" {
  project_id = var.project_id
}


//////////
// APIs //
//////////

resource "google_project_service" "project" {
  for_each = toset(var.minimum_apis)
  project  = var.project_id
  service  = each.key
  timeouts {
    create = "30m"
    update = "40m"
  }
  disable_dependent_services = true
  disable_on_destroy         = true
}

//////////////////////
// Service Accounts //
//////////////////////

resource "google_project_iam_member" "cloud_build" {
  for_each = toset([
    "roles/storage.admin",
  ])
  project = var.project_id
  role    = each.key
  member  = local.cloud_build_sa_email_member
}

/////////////
// Buckets //
/////////////

module "tf_state_bucket" {
  source     = "github.com/GoogleCloudPlatform/cloud-foundation-fabric/modules/gcs"
  project_id = var.project_id
  prefix     = var.tf_state_bucket_name_prefix
  name       = data.google_project.project.number
}

////////////////
// backend.tf //
////////////////

resource "local_file" "backend_tf" {
  for_each = toset(var.backend_tf_modules)
  content = templatefile(local.backend_tf_tmpl, {
    BUCKET_NAME = module.tf_state_bucket.bucket.name,
    REGION      = var.region,
    MODULE      = each.key
  })
  filename = "${local.backend_tf}.${each.key}"
}