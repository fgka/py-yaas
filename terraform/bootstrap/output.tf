/////////////
// Modules //
/////////////

output "tf_state_bucket" {
  value = module.tf_state_bucket.bucket
}

output "backend_tf" {
  value = local.output_filenames
}

output "build_pipeline_backend_tf_tmpl" {
  value = local.build_pipeline_backend_tf_tmpl
}
