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

## [Bootstrap](./bootstrap/README.md)

**NOTE:** You should need this only once.

```bash
export TF_DIR="./bootstrap"
```

```bash
terraform -chdir=${TF_DIR} init -upgrade
```

### Plan

```bash
TMP=$(mktemp)
terraform -chdir=${TF_DIR} plan \
  -out ${TMP} \
  -var "project_id=${PROJECT_ID}" \
  -var "region=${REGION}"
```

### Apply

```bash
terraform -chdir=${TF_DIR} apply ${TMP} && rm -f ${TMP}
```

### Export bucket name

```bash
OUT_JSON=$(mktemp)
terraform -chdir=${TF_DIR} output -json > ${OUT_JSON}
echo "Terraform output in ${OUT_JSON}"

export TF_STATE_BUCKET=$(jq -c -r ".tf_state_bucket.value.name" ${OUT_JSON})
echo "Terraform state bucket name: <${TF_STATE_BUCKET}>"
rm -f ${OUT_JSON}
```

### Copy generated `backend.tf` over to each module

```bash
TARGET_FILENAME="backend.tf"
OUT_JSON=$(mktemp)
terraform -chdir=${TF_DIR} output -json > ${OUT_JSON}
echo "Terraform output in ${OUT_JSON}"

jq -c -r ".backend_tf.value[]" ${OUT_JSON} \
  | while read FILENAME; \
    do \
      local ACTUAL_FILENAME="${TF_DIR}/${FILENAME}"
      local MODULE=${FILENAME##*.}; \
      local OUTPUT="./${MODULE}/${TARGET_FILENAME}"; \
      echo "Copying: <${ACTUAL_FILENAME}> to <${OUTPUT}>"; \
      cp ${ACTUAL_FILENAME} ${OUTPUT}; \
    done
rm -f ${OUT_JSON}
```

## Copy generated `backend.tf.tmpl` over CI/CD template directory

```bash
TARGET="./cicd/2_cicd_build/templates/backend.tf.tmpl"
OUT_JSON=$(mktemp)
terraform -chdir=${TF_DIR} output -json > ${OUT_JSON}
echo "Terraform output in ${OUT_JSON}"

SOURCE=${TF_DIR}/$(jq -c -r ".build_pipeline_backend_tf_tmpl.value" ${OUT_JSON})
echo "Copying: <${SOURCE}> to <${TARGET}>"
rm -f ${OUT_JSON}
```

**NOTE**: Please commit the new template, if necessary, in the `cicd` module.

## [CI/CD](./cicd/README.md)

```bash
export TF_DIR="./cicd"
```

```bash
terraform -chdir=${TF_DIR} init -upgrade
```

### Plan

```bash
TMP=$(mktemp)
terraform -chdir=${TF_DIR} plan \
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

### Apply

```bash
terraform -chdir=${TF_DIR} apply ${TMP} && rm -f ${TMP}
```

### Trigger Build

Get trigger name:

```bash
OUT_JSON=$(mktemp)
terraform -chdir=${TF_DIR} output -json > ${OUT_JSON}
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

## (Only If Manual Deployment Is Required) [YAAS](./yaas/README.md)

**NOTE:** This should not be required at all, use the Cloud Build triggers.
