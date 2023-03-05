# Using Terraform to deploy all

It is assumed you ran the [bootstrap](../bootstrap/README.md) instructions first.

## Definitions

Manually set:

```bash
export PROJECT_ID=$(gcloud config get-value core/project)
export REGION="europe-west3"
```

Code dependant:

```bash
pushd ../../code
export PIP_PACKAGE="$(python3 ./setup.py --name)>=$(python3 ./setup.py --version)"
popd
```

Please set them properly:

```bash
export NOTIFICATION_EMAIL="${USER}@$(uname -n)"
export GITHUB_OWNER="${USER}"

export GITHUB_REPO=$(basename `git rev-parse --show-toplevel`)
export GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
```

Calendar ID:

```bash
export CALENDAR_ID="YOUR_GOOGLE_CALENDAR_ID"
```

Check:

```bash
echo "Main project: ${PROJECT_ID}@${REGION}"
echo "Email: ${NOTIFICATION_EMAIL}"
echo "PIP: ${PIP_PACKAGE}"
echo "Github: ${GITHUB_OWNER}@${GITHUB_REPO}:${GIT_BRANCH}"
echo "Google Calendar ID: ${CALENDAR_ID}"
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
  -var "project_id=${PROJECT_ID}" \
  -var "region=${REGION}" \
  -var "terraform_bucket_name=${TF_STATE_BUCKET}" \
  -var "build_monitoring_email_address=${NOTIFICATION_EMAIL}" \
  -var "monitoring_email_address=${NOTIFICATION_EMAIL}" \
  -var "github_owner=${GITHUB_OWNER}" \
  -var "github_repo_name=${GITHUB_REPO}" \
  -var "github_branch=${GIT_BRANCH}" \
  -var "calendar_id=${CALENDAR_ID}" \
  -var "yaas_pip_package=${PIP_PACKAGE}"
```

## Apply

```bash
terraform apply ${TMP} && rm -f ${TMP}
```

## Trigger Build

Get trigger name:

```bash
OUT_JSON=$(mktemp)
terraform output -json > ${OUT_JSON}
echo "Terraform output in ${OUT_JSON}"

CICD_TF_TRIGGER_NAME=$(jq -c -r ".cicd_build.value.tf_build_trigger.name" ${OUT_JSON})
echo "CI/CD Terraform trigger name: <${CICD_TF_TRIGGER_NAME}>"

rm -f ${OUT_JSON}
```

Trigger build:

```bash
TMP=$(mktemp)
gcloud builds triggers run ${CICD_TF_TRIGGER_NAME} \
  --branch=${GIT_BRANCH} \
  --region=${REGION} \
  --format=json \
  > ${TMP}

BUILD_ID=$(jq -r -c ".metadata.build.id" ${TMP})
echo "Build ID: <${BUILD_ID}>"

rm -f ${TMP}
```

Stream logs:

```bash
gcloud builds log ${BUILD_ID} --region=${REGION} --stream
```

Status:

```bash
gcloud builds describe ${BUILD_ID} --region=${REGION}
```

<!-- BEGINNING OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.2.5 |
| <a name="requirement_google"></a> [google](#requirement\_google) | >= 4.44.0 |
| <a name="requirement_google-beta"></a> [google-beta](#requirement\_google-beta) | >= 4.44.0 |
| <a name="requirement_local"></a> [local](#requirement\_local) | >= 1.2.5 |

## Providers

No providers.

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_cicd_build"></a> [cicd\_build](#module\_cicd\_build) | ./2_cicd_build | n/a |
| <a name="module_cicd_infra"></a> [cicd\_infra](#module\_cicd\_infra) | ./1_cicd_infra | n/a |

## Resources

No resources.

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_app_build_trigger_name"></a> [app\_build\_trigger\_name](#input\_app\_build\_trigger\_name) | Cloud Build trigger for Docker image. | `string` | `"yaas-application"` | no |
| <a name="input_build_bucket_name_prefix"></a> [build\_bucket\_name\_prefix](#input\_build\_bucket\_name\_prefix) | Prefix to name the build artefacts bucket, the suffix is the project numerical ID. | `string` | `"yaas-build-artefacts"` | no |
| <a name="input_build_email_monitoring_channel_name"></a> [build\_email\_monitoring\_channel\_name](#input\_build\_email\_monitoring\_channel\_name) | Build monitoring channel name to email. | `string` | `"yaas-build-email-monitoring-channel"` | no |
| <a name="input_build_monitoring_email_address"></a> [build\_monitoring\_email\_address](#input\_build\_monitoring\_email\_address) | When the build fails, it needs to send the alert to a specific email. | `string` | n/a | yes |
| <a name="input_build_monitoring_topic_name"></a> [build\_monitoring\_topic\_name](#input\_build\_monitoring\_topic\_name) | Name of the PubSub topic to send monitoring alerts. | `string` | `"yass-build-notification"` | no |
| <a name="input_build_pubsub_monitoring_channel_name"></a> [build\_pubsub\_monitoring\_channel\_name](#input\_build\_pubsub\_monitoring\_channel\_name) | Build monitoring channel name. | `string` | `"yaas-build-pubsub-monitoring-channel"` | no |
| <a name="input_build_service_account_name"></a> [build\_service\_account\_name](#input\_build\_service\_account\_name) | Service account to build artefacts | `string` | `"yaas-build-sa"` | no |
| <a name="input_calendar_id"></a> [calendar\_id](#input\_calendar\_id) | YAAS Google Calendar ID to use | `string` | n/a | yes |
| <a name="input_docker_artifact_registry_name"></a> [docker\_artifact\_registry\_name](#input\_docker\_artifact\_registry\_name) | Cloud Run YAAS docker image registry name. | `string` | `"yaas-docker"` | no |
| <a name="input_docker_base_image"></a> [docker\_base\_image](#input\_docker\_base\_image) | Docker base image | `string` | `"python:buster"` | no |
| <a name="input_github_branch"></a> [github\_branch](#input\_github\_branch) | GitHub repo branch to track | `string` | `"main"` | no |
| <a name="input_github_owner"></a> [github\_owner](#input\_github\_owner) | GitHub repo owner | `string` | n/a | yes |
| <a name="input_github_repo_name"></a> [github\_repo\_name](#input\_github\_repo\_name) | GitHub repo name | `string` | n/a | yes |
| <a name="input_monitoring_email_address"></a> [monitoring\_email\_address](#input\_monitoring\_email\_address) | When YAAS fails, it needs to send the alert to a specific email. | `string` | n/a | yes |
| <a name="input_object_age_in_days"></a> [object\_age\_in\_days](#input\_object\_age\_in\_days) | How long to keep objects, in days, before automatically remove them. | `number` | `7` | no |
| <a name="input_project_id"></a> [project\_id](#input\_project\_id) | Project ID where to deploy and source of data. | `string` | n/a | yes |
| <a name="input_python_artifact_registry_name"></a> [python\_artifact\_registry\_name](#input\_python\_artifact\_registry\_name) | Python YAAS package registry name. | `string` | `"yaas-py"` | no |
| <a name="input_python_build_trigger_name"></a> [python\_build\_trigger\_name](#input\_python\_build\_trigger\_name) | Cloud Build trigger for Python code. | `string` | `"yaas-py"` | no |
| <a name="input_region"></a> [region](#input\_region) | Default region where to create resources. | `string` | `"us-central1"` | no |
| <a name="input_run_cicd"></a> [run\_cicd](#input\_run\_cicd) | If it is run through Cloud Build. | `bool` | `true` | no |
| <a name="input_run_container_concurrency"></a> [run\_container\_concurrency](#input\_run\_container\_concurrency) | YAAS Cloud Run container concurrency. | `number` | `80` | no |
| <a name="input_run_name"></a> [run\_name](#input\_run\_name) | YAAS Cloud Run name. | `string` | `"yaas-run"` | no |
| <a name="input_secrets_calendar_credentials_file"></a> [secrets\_calendar\_credentials\_file](#input\_secrets\_calendar\_credentials\_file) | File with the secret content for Google calendar credentials | `string` | `""` | no |
| <a name="input_terraform_bucket_name"></a> [terraform\_bucket\_name](#input\_terraform\_bucket\_name) | Bucket name to store terraform states. | `string` | n/a | yes |
| <a name="input_tf_build_ignored_files"></a> [tf\_build\_ignored\_files](#input\_tf\_build\_ignored\_files) | Which files to be ignored in all builds, typically documentation | `list(string)` | <pre>[<br>  "**/*.md",<br>  "**/doc/*"<br>]</pre> | no |
| <a name="input_tf_build_service_account_name"></a> [tf\_build\_service\_account\_name](#input\_tf\_build\_service\_account\_name) | Service account to build terraform | `string` | `"yaas-tf-build-sa"` | no |
| <a name="input_tf_build_trigger_name"></a> [tf\_build\_trigger\_name](#input\_tf\_build\_trigger\_name) | Cloud Build trigger for CI/CD Terraform code. | `string` | `"yaas-tf-cicd"` | no |
| <a name="input_tf_cicd_plan_args"></a> [tf\_cicd\_plan\_args](#input\_tf\_cicd\_plan\_args) | CI/CD Terraform plan args | `map(any)` | `{}` | no |
| <a name="input_tf_infra_plan_args"></a> [tf\_infra\_plan\_args](#input\_tf\_infra\_plan\_args) | YAAS infrastructure Terraform plan args | `map(any)` | `{}` | no |
| <a name="input_tf_yaas_trigger_name"></a> [tf\_yaas\_trigger\_name](#input\_tf\_yaas\_trigger\_name) | Cloud Build trigger for YAAS infrastructure Terraform code. | `string` | `"yaas-tf-infra"` | no |
| <a name="input_yaas_dockerfile"></a> [yaas\_dockerfile](#input\_yaas\_dockerfile) | YAAS application Dockerfile | `string` | `"./docker/Dockerfile"` | no |
| <a name="input_yaas_image_name"></a> [yaas\_image\_name](#input\_yaas\_image\_name) | YAAS docker application image | `string` | `"yaas"` | no |
| <a name="input_yaas_pip_package"></a> [yaas\_pip\_package](#input\_yaas\_pip\_package) | Python package full name with version: "$(python3 ./setup.py --name)>=$(python3 ./setup.py --version)" | `string` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_cicd_build"></a> [cicd\_build](#output\_cicd\_build) | n/a |
| <a name="output_cicd_infra"></a> [cicd\_infra](#output\_cicd\_infra) | n/a |
<!-- END OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
