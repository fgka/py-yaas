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

Please set them properly:

```bash
export NOTIFICATION_EMAIL="${USER}@$(uname -n)"
```

Check:

```bash
echo "Main project: ${PROJECT_ID}@${REGION}"
echo "Email: ${NOTIFICATION_EMAIL}"
```

## Enable APIs

```bash
gcloud services enable \
  calendar-json.googleapis.com \
  cloudscheduler.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  pubsub.googleapis.com \
  run.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
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
  -var "region=${REGION}" \
  -var "monitoring_email_address=${NOTIFICATION_EMAIL}"
```

## Apply

```bash
terraform apply ${TMP} && rm -f ${TMP}
```
