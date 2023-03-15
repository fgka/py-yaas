# YAAS Cloud Run Module

<!-- BEGINNING OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
## Requirements

No requirements.

## Providers

| Name | Version |
|------|---------|
| <a name="provider_google"></a> [google](#provider\_google) | 4.55.0 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [google_cloud_run_v2_service.default](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/cloud_run_v2_service) | resource |
| [google_cloud_run_v2_service_iam_member.run_agent](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/cloud_run_v2_service_iam_member) | resource |
| [google_monitoring_alert_policy.alert_error_log](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/monitoring_alert_policy) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_bucket_name"></a> [bucket\_name](#input\_bucket\_name) | YAAS artefacts bucket name. | `string` | n/a | yes |
| <a name="input_config_path"></a> [config\_path](#input\_config\_path) | YAAS configuration object path in the bucket. E.g.: yaas/config.json | `string` | `"yaas/config.json"` | no |
| <a name="input_image_name_uri"></a> [image\_name\_uri](#input\_image\_name\_uri) | YAAS docker application image URI. E.g.: LOCATION-docker.pkg.dev/PROJECT\_ID/yaas-docker/yaas:latest | `string` | `"us-docker.pkg.dev/cloudrun/container/hello"` | no |
| <a name="input_log_level"></a> [log\_level](#input\_log\_level) | YAAS Cloud Run log level. | `string` | `"INFO"` | no |
| <a name="input_monitoring_alert_severity"></a> [monitoring\_alert\_severity](#input\_monitoring\_alert\_severity) | Severity, included, above which it should generate an alert. | `string` | `"ERROR"` | no |
| <a name="input_monitoring_email_channel_name"></a> [monitoring\_email\_channel\_name](#input\_monitoring\_email\_channel\_name) | Runtime monitoring channel name to email. | `string` | n/a | yes |
| <a name="input_monitoring_notification_auto_close_in_days"></a> [monitoring\_notification\_auto\_close\_in\_days](#input\_monitoring\_notification\_auto\_close\_in\_days) | For how many days to keep an alert alive before closing due to lack of reaction to it. | `number` | `7` | no |
| <a name="input_monitoring_notification_email_rate_limit_in_minutes"></a> [monitoring\_notification\_email\_rate\_limit\_in\_minutes](#input\_monitoring\_notification\_email\_rate\_limit\_in\_minutes) | For how many minutes to wait for until sending the next email notification. | `number` | `60` | no |
| <a name="input_monitoring_notification_pubsub_rate_limit_in_minutes"></a> [monitoring\_notification\_pubsub\_rate\_limit\_in\_minutes](#input\_monitoring\_notification\_pubsub\_rate\_limit\_in\_minutes) | For how many minutes to wait for until sending the next Pub/Sub notification. | `number` | `5` | no |
| <a name="input_monitoring_pubsub_channel_name"></a> [monitoring\_pubsub\_channel\_name](#input\_monitoring\_pubsub\_channel\_name) | Runtime monitoring channel name. | `string` | n/a | yes |
| <a name="input_project_id"></a> [project\_id](#input\_project\_id) | Project ID where to deploy and source of data. | `string` | n/a | yes |
| <a name="input_region"></a> [region](#input\_region) | Default region where to create resources. | `string` | `"us-central1"` | no |
| <a name="input_run_container_concurrency"></a> [run\_container\_concurrency](#input\_run\_container\_concurrency) | Cloud Run request concurrency per container, mind thread-safety. | `number` | `80` | no |
| <a name="input_run_cpu"></a> [run\_cpu](#input\_run\_cpu) | Cloud Run CPU request/limit. | `string` | `"1000m"` | no |
| <a name="input_run_max_instances"></a> [run\_max\_instances](#input\_run\_max\_instances) | Cloud Run yaas maximum instances. | `number` | `10` | no |
| <a name="input_run_mem"></a> [run\_mem](#input\_run\_mem) | Cloud Run Memory request/limit. | `string` | `"512Mi"` | no |
| <a name="input_run_min_instances"></a> [run\_min\_instances](#input\_run\_min\_instances) | Cloud Run minimum instances. | `number` | `0` | no |
| <a name="input_run_name"></a> [run\_name](#input\_run\_name) | YAAS Cloud Run name. | `string` | n/a | yes |
| <a name="input_run_sa_email"></a> [run\_sa\_email](#input\_run\_sa\_email) | YAAS Scheduler Cloud Run Service Account identity email | `string` | n/a | yes |
| <a name="input_run_timeout"></a> [run\_timeout](#input\_run\_timeout) | Cloud Run timeout in seconds. | `number` | `540` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_alert_policy_error_log"></a> [alert\_policy\_error\_log](#output\_alert\_policy\_error\_log) | n/a |
| <a name="output_service"></a> [service](#output\_service) | n/a |
| <a name="output_service_url"></a> [service\_url](#output\_service\_url) | n/a |
<!-- END OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
