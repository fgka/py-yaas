
terraform {
  required_version = ">= 1.2.5"
  required_providers {
    google      = ">= 4.44.0"
    google-beta = ">= 4.44.0"
    local = {
      source = "hashicorp/local"
    }
  }
  backend "gcs" {
    bucket = "yaas-tf-state-245814988234"
    prefix = "terraform/europe-west3/state/cicd"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}
