
terraform {
  required_version = ">= 1.2.5"
  required_providers {
    google      = ">= 4.44.0"
    google-beta = ">= 4.44.0"
    local = {
      source  = "hashicorp/local"
      version = ">= 1.2.5"
    }
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
