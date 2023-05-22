# Using Terraform to deploy all

> :hand: *ALL* commands are assumed to be executed from this folder: `./terraform`

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

## Enable APIs

```bash
gcloud services enable \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  run.googleapis.com \
  servicenetworking.googleapis.com \
  sqladmin.googleapis.com \
  --project="${PROJECT_ID}"
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

## Get the YASS scaling request body

Get the file name:

```bash
OUT_JSON=$(mktemp)
terraform output -json > ${OUT_JSON}
echo "Terraform output in ${OUT_JSON}"

REQUEST_FILENAME=$(jq -c -r ".request_body.value" ${OUT_JSON})
echo "Request body filename: '${REQUEST_FILENAME}'"

rm -f ${OUT_JSON}
```

Get the content:

```bash
cat ${REQUEST_FILENAME}
```

Get destination bucket:

```bash
OUT_JSON=$(mktemp)
pushd ../../terraform/yaas
terraform output -json > ${OUT_JSON}
echo "Terraform output in ${OUT_JSON}"

BUCKET_URI=$(jq -c -r ".yaas_infra.value.bucket.url" ${OUT_JSON})
BUCKET_NAME=$(jq -c -r ".yaas_infra.value.bucket.name" ${OUT_JSON})
echo "Bucket URI: '${BUCKET_URI}'"
popd

rm -f ${OUT_JSON}
```

Upload it:

```bash
OBJ_PATH="yaas/batch/test.deployed"
GCS_URI="${BUCKET_URI}/${OBJ_PATH}"
gsutil cp ${REQUEST_FILENAME} ${GCS_URI}

gsutil cat ${GCS_URI}
```

Create an appointment with:

```bash
echo "gcs | ${BUCKET_NAME} | ${OBJ_PATH}"
```
