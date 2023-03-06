# Using Terraform to deploy all

It is assumed you ran the [bootstrap](../bootstrap/README.md) instructions first.

## Definitions (only once)

Manually set:

```bash
export PROJECT_ID=$(gcloud config get-value core/project)
export REGION="europe-west3"
```

Please set them properly:

```bash
export CALENDAR_ID="YOUR_GOOGLE_CALENDAR_ID"
export NOTIFICATION_EMAIL="${USER}@$(uname -n)"
```

Check:

```bash
echo "Main project: ${PROJECT_ID}@${REGION}"
echo "Email: ${NOTIFICATION_EMAIL}"
echo "Google Calendar ID: ${CALENDAR_ID}"
```

## Create ``terraform.tfvars`` (only once)

Because macOS does not adopt gnu-sed:

```bash
export SED="sed"
if [[ "Darwin" == $(uname -s) ]]; then
  export SED="gsed"
fi
echo "sed = <${SED}>"
```

Create:

```bash
cp -f terraform.tfvars.tmpl terraform.tfvars

${SED} -i \
  -e "s/@@PROJECT_ID@@/${PROJECT_ID}/g" \
  -e "s/@@REGION@@/${REGION}/g" \
  -e "s/@@NOTIFICATION_EMAIL@@/${NOTIFICATION_EMAIL}/g" \
  -e "s/@@CALENDAR_ID@@/${CALENDAR_ID}/g" \
  terraform.tfvars
```

Check:

```bash
cat terraform.tfvars
```

## Init

```bash
terraform init -upgrade
```

## Plan

```bash
TMP=$(mktemp)
terraform plan \
  -out ${TMP} \
  -var-file=terraform.tfvars
```

## Apply

```bash
terraform apply ${TMP} && rm -f ${TMP}
```

<!-- BEGINNING OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.2.5 |
| <a name="requirement_google"></a> [google](#requirement\_google) | >= 4.44.0 |
| <a name="requirement_google-beta"></a> [google-beta](#requirement\_google-beta) | >= 4.44.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_google"></a> [google](#provider\_google) | 4.55.0 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_yaas_app"></a> [yaas\_app](#module\_yaas\_app) | ./2_yaas_app | n/a |
| <a name="module_yaas_infra"></a> [yaas\_infra](#module\_yaas\_infra) | ./1_yaas_infra | n/a |

## Resources

| Name | Type |
|------|------|
| [google_project.project](https://registry.terraform.io/providers/hashicorp/google/latest/docs/data-sources/project) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_bucket_name_prefix"></a> [bucket\_name\_prefix](#input\_bucket\_name\_prefix) | Prefix to name the YAAS artefacts bucket, the suffix is the project numerical ID. | `string` | `"yaas-app"` | no |
| <a name="input_cache_refresh_range_in_days"></a> [cache\_refresh\_range\_in\_days](#input\_cache\_refresh\_range\_in\_days) | How many days, in the future, to cache events for. | `number` | `3` | no |
| <a name="input_calendar_id"></a> [calendar\_id](#input\_calendar\_id) | YAAS Google Calendar ID to use | `string` | n/a | yes |
| <a name="input_log_level"></a> [log\_level](#input\_log\_level) | YAAS Cloud Run log level. | `string` | `"INFO"` | no |
| <a name="input_monitoring_alert_severity"></a> [monitoring\_alert\_severity](#input\_monitoring\_alert\_severity) | Severity, included, above which it should generate an alert. | `string` | `"ERROR"` | no |
| <a name="input_monitoring_email_address"></a> [monitoring\_email\_address](#input\_monitoring\_email\_address) | When there is a failure, it needs to send the alert to a specific email. | `string` | n/a | yes |
| <a name="input_monitoring_email_channel_name"></a> [monitoring\_email\_channel\_name](#input\_monitoring\_email\_channel\_name) | Runtime monitoring channel name to email. | `string` | `"yaas-build-email-monitoring-channel"` | no |
| <a name="input_monitoring_pubsub_channel_name"></a> [monitoring\_pubsub\_channel\_name](#input\_monitoring\_pubsub\_channel\_name) | Runtime monitoring channel name. | `string` | `"yaas-build-pubsub-monitoring-channel"` | no |
| <a name="input_project_id"></a> [project\_id](#input\_project\_id) | Project ID where to deploy and source of data. | `string` | n/a | yes |
| <a name="input_pubsub_command_name"></a> [pubsub\_command\_name](#input\_pubsub\_command\_name) | Name of the Pub/Sub topic to send commands to. | `string` | `"yaas-command"` | no |
| <a name="input_pubsub_enact_gcs_batch_request_name"></a> [pubsub\_enact\_gcs\_batch\_request\_name](#input\_pubsub\_enact\_gcs\_batch\_request\_name) | Name of the Pub/Sub topic to send GCS based batch scaling requests. | `string` | `"yaas-enact-gcs-batch-request"` | no |
| <a name="input_pubsub_enact_standard_request_name"></a> [pubsub\_enact\_standard\_request\_name](#input\_pubsub\_enact\_standard\_request\_name) | Name of the Pub/Sub topic to send specific scaling requests. | `string` | `"yaas-enact-standard-request"` | no |
| <a name="input_pubsub_notification_topic_name"></a> [pubsub\_notification\_topic\_name](#input\_pubsub\_notification\_topic\_name) | Name of the Pub/Sub topic to send runtime notification about errors. | `string` | `"yaas-notifications"` | no |
| <a name="input_pubsub_service_account_name"></a> [pubsub\_service\_account\_name](#input\_pubsub\_service\_account\_name) | Service account to be used by Pub/Sub to trigger YAAS. | `string` | `"yaas-pubsub-sa"` | no |
| <a name="input_region"></a> [region](#input\_region) | Default region where to create resources. | `string` | `"us-central1"` | no |
| <a name="input_run_scaler_name"></a> [run\_scaler\_name](#input\_run\_scaler\_name) | YAAS Scaler Cloud Run name. | `string` | `"yaas-scaler"` | no |
| <a name="input_run_scaler_service_account_name"></a> [run\_scaler\_service\_account\_name](#input\_run\_scaler\_service\_account\_name) | YAAS Cloud Run Service Account identity for Scaler | `string` | `"yaas-run-scaler-sa"` | no |
| <a name="input_run_scaler_service_account_roles"></a> [run\_scaler\_service\_account\_roles](#input\_run\_scaler\_service\_account\_roles) | All admin roles required to let YAAS manage resources | `list(string)` | <pre>[<br>  "roles/compute.instanceAdmin.v1",<br>  "roles/cloudfunctions.admin",<br>  "roles/cloudsql.admin",<br>  "roles/run.admin",<br>  "roles/iam.serviceAccountUser"<br>]</pre> | no |
| <a name="input_run_sched_name"></a> [run\_sched\_name](#input\_run\_sched\_name) | YAAS Scheduler Cloud Run name. | `string` | `"yaas-sched"` | no |
| <a name="input_run_sched_service_account_name"></a> [run\_sched\_service\_account\_name](#input\_run\_sched\_service\_account\_name) | YAAS Cloud Run Service Account identity for Scheduler | `string` | `"yaas-run-sched-sa"` | no |
| <a name="input_run_sched_service_account_roles"></a> [run\_sched\_service\_account\_roles](#input\_run\_sched\_service\_account\_roles) | All roles required by YAAS Scheduler | `list(string)` | <pre>[<br>  "roles/iam.serviceAccountUser"<br>]</pre> | no |
| <a name="input_scaler_image_name_uri"></a> [scaler\_image\_name\_uri](#input\_scaler\_image\_name\_uri) | YAAS Scaler docker application image URI. E.g.: LOCATION-docker.pkg.dev/PROJECT\_ID/yaas-docker/yaas\_sched:latest | `string` | `"us-docker.pkg.dev/cloudrun/container/hello"` | no |
| <a name="input_sched_image_name_uri"></a> [sched\_image\_name\_uri](#input\_sched\_image\_name\_uri) | YAAS Scheduler docker application image URI. E.g.: LOCATION-docker.pkg.dev/PROJECT\_ID/yaas-docker/yaas\_sched:latest | `string` | `"us-docker.pkg.dev/cloudrun/container/hello"` | no |
| <a name="input_scheduler_cache_refresh_cron_entry_triggering_minute"></a> [scheduler\_cache\_refresh\_cron\_entry\_triggering\_minute](#input\_scheduler\_cache\_refresh\_cron\_entry\_triggering\_minute) | YAAS calendar cache refresh triggering minute. Please only change if you know what you are doing. | `number` | `17` | no |
| <a name="input_scheduler_cache_refresh_name"></a> [scheduler\_cache\_refresh\_name](#input\_scheduler\_cache\_refresh\_name) | Name of the Cloud Scheduler that triggers YAAS calendar cache refresh | `string` | `"yaas-cache-refresh"` | no |
| <a name="input_scheduler_cache_refresh_rate_in_hours"></a> [scheduler\_cache\_refresh\_rate\_in\_hours](#input\_scheduler\_cache\_refresh\_rate\_in\_hours) | YAAS calendar cache refresh rate in hours, i.e., how many hours after a refresh to repeat it. | `number` | `6` | no |
| <a name="input_scheduler_calendar_credentials_refresh_cron_entry_triggering_minute"></a> [scheduler\_calendar\_credentials\_refresh\_cron\_entry\_triggering\_minute](#input\_scheduler\_calendar\_credentials\_refresh\_cron\_entry\_triggering\_minute) | YAAS calendar calendar credentials refresh triggering minute. Please only change if you know what you are doing. | `number` | `13` | no |
| <a name="input_scheduler_calendar_credentials_refresh_name"></a> [scheduler\_calendar\_credentials\_refresh\_name](#input\_scheduler\_calendar\_credentials\_refresh\_name) | Name of the Cloud Scheduler that triggers YAAS calendar credentials refresh | `string` | `"yaas-calendar-credentials-refresh"` | no |
| <a name="input_scheduler_calendar_credentials_refresh_rate_in_hours"></a> [scheduler\_calendar\_credentials\_refresh\_rate\_in\_hours](#input\_scheduler\_calendar\_credentials\_refresh\_rate\_in\_hours) | YAAS calendar credentials refresh rate in hours, i.e., how many hours after a refresh to repeat it. | `number` | `4` | no |
| <a name="input_scheduler_cron_timezone"></a> [scheduler\_cron\_timezone](#input\_scheduler\_cron\_timezone) | Crontab entry timezone. | `string` | `"Etc/UTC"` | no |
| <a name="input_scheduler_request_name"></a> [scheduler\_request\_name](#input\_scheduler\_request\_name) | Name of the Cloud Scheduler that triggers YAAS request emission. | `string` | `"yaas-request-emission"` | no |
| <a name="input_scheduler_request_rate_in_minutes"></a> [scheduler\_request\_rate\_in\_minutes](#input\_scheduler\_request\_rate\_in\_minutes) | YAAS calendar cache refresh rate in hours, i.e., how many hours after a refresh to repeat it. | `number` | `30` | no |
| <a name="input_secrets_calendar_credentials_file"></a> [secrets\_calendar\_credentials\_file](#input\_secrets\_calendar\_credentials\_file) | File with the secret content for Google calendar credentials | `string` | `null` | no |
| <a name="input_secrets_calendar_credentials_name"></a> [secrets\_calendar\_credentials\_name](#input\_secrets\_calendar\_credentials\_name) | Secret name where the Google calendar credentials are stored | `string` | `"yaas_calendar_credentials"` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_yaas_build"></a> [yaas\_build](#output\_yaas\_build) | n/a |
| <a name="output_yaas_infra"></a> [yaas\_infra](#output\_yaas\_infra) | n/a |
<!-- END OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
