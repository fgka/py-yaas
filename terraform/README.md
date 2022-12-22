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

## Enable APIs

Main project:

```bash
gcloud services enable \
  calendar-json.googleapis.com \
  cloudbuild.googleapis.com \
  cloudfunctions.googleapis.com \
  iam.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  --project="${PROJECT_ID}"
```

## Init

```bash
terraform init
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
