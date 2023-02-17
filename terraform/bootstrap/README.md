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

## Copy generated `backend.tf` over

Get file name:

```bash
OUT_JSON=$(mktemp)
terraform output -json > ${OUT_JSON}
echo "Terraform output in ${OUT_JSON}"

jq -c -r ".backend_tf.value[]" ${OUT_JSON} \
  | while read FILENAME; \
    do \
      local TARGET=$(basename ${FILENAME}); \
      TARGET=${TARGET%.*}; \
      local MODULE=${FILENAME##*.}; \
      local OUTPUT="../${MODULE}/${TARGET}"; \
      echo "Copying: <${FILENAME}> to <${OUTPUT}>"; \
      cp ${FILENAME} ${OUTPUT}; \
    done
rm -f ${OUT_JSON}
```

Copy over:

```bash
cp ${BACKEND_TF} ../cicd/
cp ${BACKEND_TF} ../yaas/
```

