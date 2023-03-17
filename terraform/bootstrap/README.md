# Using Terraform to deploy all

## Authenticate (only once)

```bash
gcloud auth application-default login
```

### Set default project (only once)

```bash
gcloud init
```

## Definitions (only once)

Manually set:

```bash
export PROJECT_ID=$(gcloud config get-value core/project)
export REGION="europe-west3"
```

Check:

```bash
echo "Main project: ${PROJECT_ID}@${REGION}"
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

Without integration test data:

```bash
TMP=$(mktemp)
terraform plan \
  -out=${TMP} \
  -var-file=terraform.tfvars
```

## Apply

```bash
terraform apply ${TMP} && rm -f ${TMP}
```

## Export bucket name (only once)

```bash
OUT_JSON=$(mktemp)
terraform output -json > ${OUT_JSON}
echo "Terraform output in ${OUT_JSON}"

export TF_STATE_BUCKET=$(jq -c -r ".tf_state_bucket.value.name" ${OUT_JSON})
echo "Terraform state bucket name: <${TF_STATE_BUCKET}>"
rm -f ${OUT_JSON}
```

## Copy generated `backend.tf` over to each module (only once)

```bash
TARGET_FILENAME="backend.tf"
OUT_JSON=$(mktemp)
terraform output -json > ${OUT_JSON}
echo "Terraform output in ${OUT_JSON}"

jq -c -r ".backend_tf.value[]" ${OUT_JSON} \
  | while read FILENAME; \
    do \
      MODULE=${FILENAME##*.}; \
      OUTPUT="../${MODULE}/${TARGET_FILENAME}"; \
      echo "Copying: <${FILENAME}> to <${OUTPUT}>"; \
      cp ${FILENAME} ${OUTPUT}; \
    done
rm -f ${OUT_JSON}
```

## Copy generated `backend.tf.tmpl` over CI/CD template directory (only once)

```bash
TARGET="../cicd/2_cicd_build/templates/backend.tf.tmpl"
OUT_JSON=$(mktemp)
terraform output -json > ${OUT_JSON}
echo "Terraform output in ${OUT_JSON}"

SOURCE=$(jq -c -r ".build_pipeline_backend_tf_tmpl.value" ${OUT_JSON})
echo "Copying: <${SOURCE}> to <${TARGET}>"
rm -f ${OUT_JSON}
```

**NOTE**: Please commit the new template, if necessary, in the `cicd` module.

<!-- BEGINNING OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.2.5 |
| <a name="requirement_google"></a> [google](#requirement\_google) | >= 4.44.0 |
| <a name="requirement_google-beta"></a> [google-beta](#requirement\_google-beta) | >= 4.44.0 |
| <a name="requirement_local"></a> [local](#requirement\_local) | >= 1.2.5 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_google"></a> [google](#provider\_google) | 4.55.0 |
| <a name="provider_local"></a> [local](#provider\_local) | 2.3.0 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_tf_state_bucket"></a> [tf\_state\_bucket](#module\_tf\_state\_bucket) | github.com/GoogleCloudPlatform/cloud-foundation-fabric/modules/gcs | n/a |

## Resources

| Name | Type |
|------|------|
| [google_project_iam_member.cloud_build](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/project_iam_member) | resource |
| [google_project_service.project](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/project_service) | resource |
| [local_file.backend_tf](https://registry.terraform.io/providers/hashicorp/local/latest/docs/resources/file) | resource |
| [local_file.build_backend_tf_tmpl](https://registry.terraform.io/providers/hashicorp/local/latest/docs/resources/file) | resource |
| [google_project.project](https://registry.terraform.io/providers/hashicorp/google/latest/docs/data-sources/project) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_backend_tf"></a> [backend\_tf](#input\_backend\_tf) | Where to store backend.tf. Only change if you know what you are doing. | `string` | `"backend.tf"` | no |
| <a name="input_backend_tf_modules"></a> [backend\_tf\_modules](#input\_backend\_tf\_modules) | Modules with their own Terraform state. Only change if you know what you are doing. | `list(string)` | <pre>[<br>  "cicd",<br>  "yaas"<br>]</pre> | no |
| <a name="input_backend_tf_tmpl"></a> [backend\_tf\_tmpl](#input\_backend\_tf\_tmpl) | Template for backend.tf. Only change if you know what you are doing. | `string` | `"templates/backend.tf.tmpl"` | no |
| <a name="input_build_pipeline_backend_tf_tmpl"></a> [build\_pipeline\_backend\_tf\_tmpl](#input\_build\_pipeline\_backend\_tf\_tmpl) | Template for backend.tf to be used in CloudBuild. Only change if you know what you are doing. | `string` | `"cloud_build.backend.tf.tmpl"` | no |
| <a name="input_minimum_apis"></a> [minimum\_apis](#input\_minimum\_apis) | Minimum APIs to activate in the YAAS project. Only change if you know what you are doing. | `list(string)` | <pre>[<br>  "artifactregistry.googleapis.com",<br>  "calendar-json.googleapis.com",<br>  "cloudapis.googleapis.com",<br>  "cloudbuild.googleapis.com",<br>  "cloudresourcemanager.googleapis.com",<br>  "cloudscheduler.googleapis.com",<br>  "iam.googleapis.com",<br>  "iamcredentials.googleapis.com",<br>  "logging.googleapis.com",<br>  "monitoring.googleapis.com",<br>  "pubsub.googleapis.com",<br>  "run.googleapis.com",<br>  "secretmanager.googleapis.com",<br>  "servicemanagement.googleapis.com",<br>  "serviceusage.googleapis.com",<br>  "storage.googleapis.com"<br>]</pre> | no |
| <a name="input_project_id"></a> [project\_id](#input\_project\_id) | Project ID where to deploy and source of data. | `string` | n/a | yes |
| <a name="input_region"></a> [region](#input\_region) | Default region where to create resources. | `string` | `"us-central1"` | no |
| <a name="input_tf_state_bucket_name_prefix"></a> [tf\_state\_bucket\_name\_prefix](#input\_tf\_state\_bucket\_name\_prefix) | Prefix to name the terraform state bucket, the suffix is the project numerical ID. | `string` | `"yaas-terraform"` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_backend_tf"></a> [backend\_tf](#output\_backend\_tf) | n/a |
| <a name="output_build_pipeline_backend_tf_tmpl"></a> [build\_pipeline\_backend\_tf\_tmpl](#output\_build\_pipeline\_backend\_tf\_tmpl) | n/a |
| <a name="output_tf_state_bucket"></a> [tf\_state\_bucket](#output\_tf\_state\_bucket) | n/a |
<!-- END OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
