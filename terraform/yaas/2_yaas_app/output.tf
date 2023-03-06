///////////////
// Cloud Run //
///////////////

output "yaas_sched" {
  value = module.yaas_sched
}

output "yaas_scaler" {
  value = module.yaas_scaler
}

/////////////////
// Config JSON //
/////////////////

output "local_config_json" {
  value = local_file.config_json.filename
}

output "gcs_config_json" {
  value = "gs://${google_storage_bucket_object.config_json.bucket}/${google_storage_bucket_object.config_json.output_name}"
}

//////////////////////
// Topic to Pub/Sub //
//////////////////////

output "gcs_topic_to_pubsub" {
  value = "gs://${google_storage_bucket_object.topic_to_pubsub_gcs.bucket}/${google_storage_bucket_object.topic_to_pubsub_gcs.output_name}"
}
