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

Code dependant:

```bash
pushd ../code
export PIP_PACKAGE="$(python3 ./setup.py --name)>=$(python3 ./setup.py --version)"
popd
```

Please set them properly:

```bash
export NOTIFICATION_EMAIL="${USER}@$(uname -n)"
export GITHUB_OWNER="${USER}"
export GITHUB_REPO="py-yaas-playground"
export GIT_BRANCH="main"
```

Check:

```bash
echo "Main project: ${PROJECT_ID}@${REGION}"
echo "Email: ${NOTIFICATION_EMAIL}"
echo "PIP: ${PIP_PACKAGE}"
echo "Github: ${GITHUB_OWNER}@${GITHUB_REPO}/${GIT_BRANCH}"
```

## Enable APIs

```bash
gcloud services enable \
  artifactregistry.googleapis.com \
  calendar-json.googleapis.com \
  cloudapis.googleapis.com \
  cloudbuild.googleapis.com \
  cloudfunctions.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  pubsub.googleapis.com \
  run.googleapis.com \
  secretmanager.googleapis.com \
  servicemanagement.googleapis.com \
  serviceusage.googleapis.com \
  storage.googleapis.com \
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
  -var "region=${REGION}" \
  -var "build_monitoring_email_address=${NOTIFICATION_EMAIL}" \
  -var "github_owner=${GITHUB_OWNER}" \
  -var "github_repo_name=${GITHUB_REPO}" \
  -var "github_branch=${GIT_BRANCH}" \
  -var "yaas_pip_package=${PIP_PACKAGE}"
```

## Apply

```bash
terraform apply ${TMP} && rm -f ${TMP}
```
