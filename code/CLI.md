# CLI usage

## Definitions

```bash
export PROJECT_ID=$(gcloud config get-value core/project)
export PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
```

## Refresh/Reset Calendar Credentials

Define:

```bash
export CALENDAR_ID="YOUR_GOOGLE_CALENDAR_ID"
export SECRET_NAME="YOUR_SECRET_NAME"
export INITIAL_CREDENTIALS_JSON="YOUR_GOOGLE_CALENDAR_CREDENTIALS_JSON"
```

Secret full name:

```bash
export SECRET_FULL_NAME="projects/${PROJECT_NUMBER}/secrets/${SECRET_NAME}"
```

Check:

```bash
echo "Calendar ID: ${CALENDAR_ID}"
echo "Secret: ${SECRET_FULL_NAME}"
echo "Initial credentials: ${INITIAL_CREDENTIALS_JSON}"
```

Refresh credentials:

```bash
python -m yaas.main update-calendar-credentials \
  --calendar-id ${CALENDAR_ID} \
  --secret-name ${SECRET_FULL_NAME} \
  --credentials-json ${INITIAL_CREDENTIALS_JSON}
```
