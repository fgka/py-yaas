# Using Terraform to deploy all

> :hand: *ALL* commands are assumed to be executed from this folder: `./terraform`

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

Please set them properly:

```bash
export NOTIFICATION_EMAIL="${USER}@$(uname -n)"
export GITHUB_OWNER="${USER}"

export GITHUB_REPO=$(basename `git rev-parse --show-toplevel`)
export GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
```

For CalDAV:

```bash
export GMAIL_USERNAME="YOUR_USERNAME@gmail.com"
```
e
Packages and versions:

```bash
YAAS_PIP_PACKAGES="["
unset PKGS
PKGS=("core" "service")
for P in ${PKGS[@]}; do
  pushd ../code/${P}
  poetry version --no-ansi | read PKG_NAME PKG_VERSION
  YAAS_PIP_PACKAGES+="\"${PKG_NAME}>=${PKG_VERSION}\","
  popd
done
YAAS_PIP_PACKAGES=${YAAS_PIP_PACKAGES%%,}
YAAS_PIP_PACKAGES+="]"
export YAAS_PIP_PACKAGES=${YAAS_PIP_PACKAGES}
```

Calendar ID:

```bash
export CALENDAR_ID="YOUR_GOOGLE_CALENDAR_ID"
```

Check:

```bash
echo "Main project: ${PROJECT_ID}@${REGION}"
echo "Notification Email: ${NOTIFICATION_EMAIL}"
echo "CalDAV Email: ${GMAIL_USERNAME}"
echo "YAAS python packages: ${YAAS_PIP_PACKAGES}"
echo "Github: ${GITHUB_OWNER}@${GITHUB_REPO}:${GIT_BRANCH}"
echo "Google Calendar ID: ${CALENDAR_ID}"
```

Because macOS does not adopt gnu-sed:

```bash
export SED="sed"
if [[ "Darwin" == $(uname -s) ]]; then
  export SED="gsed"
fi
echo "sed = '${SED}'"
```

## [Bootstrap](./bootstrap/README.md)

**NOTE:** You should need this only once.

```bash
export TF_DIR="./bootstrap"
```

### Create ``terraform.tfvars`` (only once)

```bash
cp -f ${TF_DIR}/terraform.tfvars.tmpl ${TF_DIR}/terraform.tfvars

${SED} -i \
  -e "s/@@PROJECT_ID@@/${PROJECT_ID}/g" \
  -e "s/@@REGION@@/${REGION}/g" \
  ${TF_DIR}/terraform.tfvars
```

### Init

```bash
terraform -chdir=${TF_DIR} init -upgrade
```

### Plan

```bash
TMP=$(mktemp)
terraform -chdir=${TF_DIR} plan \
  -out ${TMP} \
  -var-file=terraform.tfvars
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
echo "Terraform state bucket name: '${TF_STATE_BUCKET}'"
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
      ACTUAL_FILENAME="${TF_DIR}/${FILENAME}"
      MODULE=${FILENAME##*.}; \
      OUTPUT="./${MODULE}/${TARGET_FILENAME}"; \
      echo "Copying: '${ACTUAL_FILENAME}' to '${OUTPUT}'"; \
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
echo "Copying: '${SOURCE}' to '${TARGET}'"
rm -f ${OUT_JSON}
```

**NOTE**: Please commit the new template, if necessary, in the `cicd` module.

## [CI/CD](./cicd/README.md)

```bash
export TF_DIR="./cicd"
```

### Create ``terraform.tfvars`` (only once)

```bash
cp -f ${TF_DIR}/terraform.tfvars.tmpl ${TF_DIR}/terraform.tfvars

${SED} -i \
  -e "s/@@PROJECT_ID@@/${PROJECT_ID}/g" \
  -e "s/@@REGION@@/${REGION}/g" \
  -e "s/@@TF_STATE_BUCKET@@/${TF_STATE_BUCKET}/g" \
  -e "s/@@NOTIFICATION_EMAIL@@/${NOTIFICATION_EMAIL}/g" \
  -e "s/@@GITHUB_OWNER@@/${GITHUB_OWNER}/g" \
  -e "s/@@GITHUB_REPO@@/${GITHUB_REPO}/g" \
  -e "s/@@GIT_BRANCH@@/${GIT_BRANCH}/g" \
  -e "s/@@CALENDAR_ID@@/${CALENDAR_ID}/g" \
  -e "s/@@YAAS_PIP_PACKAGE@@/${YAAS_PIP_PACKAGES}/g" \
  -e "s/@@GMAIL_USERNAME@@/${GMAIL_USERNAME}/g" \
  ${TF_DIR}/terraform.tfvars

cat ${TF_DIR}/terraform.tfvars
```

### Init

```bash
terraform -chdir=${TF_DIR} init -upgrade
```

### Plan

```bash
TMP=$(mktemp)
terraform -chdir=${TF_DIR} plan \
  -out ${TMP} \
  -var-file=terraform.tfvars
```

### Apply

```bash
terraform -chdir=${TF_DIR} apply ${TMP} && rm -f ${TMP}
```

### (Only Once) Give Build Service Account Permission To State Bucket

Since the bucket is created without any extra permissions, you need to grant the build SA access.

Service account email:

```bash
OUT_JSON=$(mktemp)
terraform -chdir=${TF_DIR} output -json > ${OUT_JSON}
echo "Terraform output in ${OUT_JSON}"

BUILD_SA_MEMBER_EMAIL=$(jq -c -r ".cicd_infra.value.tf_build_service_account.member" ${OUT_JSON})
echo "Build Service Account member email: '${BUILD_SA_MEMBER_EMAIL}'"

rm -f ${OUT_JSON}
```

Grant permissions:

```bash
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member=${BUILD_SA_MEMBER_EMAIL} \
  --role="roles/storage.admin"
```

### Trigger Build

Get trigger name:

```bash
OUT_JSON=$(mktemp)
terraform -chdir=${TF_DIR} output -json > ${OUT_JSON}
echo "Terraform output in ${OUT_JSON}"

CICD_TF_TRIGGER_NAME=$(jq -c -r ".cicd_build.value.tf_build_trigger.name" ${OUT_JSON})
echo "CI/CD Terraform trigger name: '${CICD_TF_TRIGGER_NAME}'"

rm -f ${OUT_JSON}
```

Trigger build:

```bash
TMP=$(mktemp)
gcloud builds triggers run ${CICD_TF_TRIGGER_NAME} \
  --project=${PROJECT_ID} \
  --region=${REGION} \
  --branch=${GIT_BRANCH} \
  --format=json \
  > ${TMP}

BUILD_ID=$(jq -r -c ".metadata.build.id" ${TMP})
echo "Build ID: '${BUILD_ID}'"

rm -f ${TMP}
```

Stream logs:

```bash
gcloud builds log ${BUILD_ID} \
  --project=${PROJECT_ID} \
  --region=${REGION} \
  --stream
```

Status:

```bash
gcloud builds describe ${BUILD_ID} \
  --project=${PROJECT_ID} \
  --region=${REGION}
```

## Check Your YAAS Configuration

```bash
export TF_DIR="./yaas"
OUT_JSON=$(mktemp)
terraform -chdir=${TF_DIR} output -json > ${OUT_JSON}
echo "Terraform output in ${OUT_JSON}"

GS_CONFIG_JSON=$(jq -c -r ".yaas_build.value.gcs_config_json" ${OUT_JSON})
echo "Google storage URI for config JSON: '${GS_CONFIG_JSON}'"

rm -f ${OUT_JSON}

gsutil cat ${GS_CONFIG_JSON}
```

## (Only If Manual Deployment Is Required) [YAAS](./yaas/README.md)

**NOTE:** This should not be required at all, use the Cloud Build triggers.
