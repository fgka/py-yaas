/////////////
// Modules //
/////////////

output "tf_state_bucket" {
  value = module.tf_state_bucket.bucket
}

output "backend_tf" {
  value = local.output_filenames
}