# Using Terraform to deploy all

## Authenticate

```bash
gcloud auth application-default login
```

### Set default project

```bash
gcloud init
```

## Definitions

Manually set:

```bash
export PROJECT_ID=$(gcloud config get-value core/project)
export REGION="europe-west3"
```

Check:

```bash
echo "Main project: ${PROJECT_ID}@${REGION}"
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
  -out ${TMP} \
  -var "project_id=${PROJECT_ID}" \
  -var "region=${REGION}"
```

## Apply

```bash
terraform apply ${TMP} && rm -f ${TMP}
```

## Export bucket name

```bash
OUT_JSON=$(mktemp)
terraform output -json > ${OUT_JSON}
echo "Terraform output in ${OUT_JSON}"

export TF_STATE_BUCKET=$(jq -c -r ".tf_state_bucket.value.name" ${OUT_JSON})
echo "Terraform state bucket name: <${TF_STATE_BUCKET}>"
rm -f ${OUT_JSON}
```

## Copy generated `backend.tf` over to each module

```bash
TARGET_FILENAME="backend.tf"
OUT_JSON=$(mktemp)
terraform output -json > ${OUT_JSON}
echo "Terraform output in ${OUT_JSON}"

jq -c -r ".backend_tf.value[]" ${OUT_JSON} \
  | while read FILENAME; \
    do \
      local MODULE=${FILENAME##*.}; \
      local OUTPUT="../${MODULE}/${TARGET_FILENAME}"; \
      echo "Copying: <${FILENAME}> to <${OUTPUT}>"; \
      cp ${FILENAME} ${OUTPUT}; \
    done
rm -f ${OUT_JSON}
```

## Copy generated `backend.tf.tmpl` over CI/CD template directory

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

