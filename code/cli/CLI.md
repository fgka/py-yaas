# CLI usage

> :hand: *ALL* commands are assumed to be executed from this folder: `./code/cli`

## Definitions

```bash
export PROJECT_ID=$(gcloud config get-value core/project)
export PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
```

## Test CalDAV access

If you are coming from the [INSTALL.md](../../INSTALL.md#add-proper-calendar-credentials) you only need:

```bash
export CALENDAR_ID="YOUR_GOOGLE_CALENDAR_ID"
export GMAIL_USERNAME="YOUR_USER@gmail.com"
```

Define:

```bash
export CALENDAR_ID="YOUR_GOOGLE_CALENDAR_ID"
export GMAIL_USERNAME="YOUR_USER@gmail.com"
export SECRET_NAME="YOUR_SECRET_NAME"
```

Secret full name:

```bash
export SECRET_FULL_NAME="projects/${PROJECT_NUMBER}/secrets/${SECRET_NAME}"
```

Check:

```bash
echo "Calendar ID: ${CALENDAR_ID}"
echo "Email: ${GMAIL_USERNAME}"
echo "Secret: ${SECRET_FULL_NAME}"
```

(If you have never done it before) Install cycle:

```bash
poetry install
```

Read calendar entries:

```bash
poetry run cli list-events \
  --calendar-id ${CALENDAR_ID} \
  --email ${GMAIL_USERNAME} \
  --secret-name ${SECRET_FULL_NAME}
```


## Refresh/Reset Calendar Credentials

If you are coming from the [INSTALL.md](../../INSTALL.md#add-proper-calendar-credentials) you only need:

```bash
export CALENDAR_ID="YOUR_GOOGLE_CALENDAR_ID"
```

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

(If you have never done it before) Install cycle:

```bash
poetry install
```

Refresh credentials:

```bash
poetry run cli update-calendar-credentials \
  --calendar-id ${CALENDAR_ID} \
  --secret-name ${SECRET_FULL_NAME} \
  --credentials-json ${INITIAL_CREDENTIALS_JSON}
```

### Authorization Steps

This will open a browser window to authorize YAAS to access the calendar.
Just accept all.

#### Visually

<details>
<summary>Click me</summary>

Select account:

![select](../doc/calendar/authorize/1-calendar-authorize-select-account.png)

Continue:

![continue](../doc/calendar/authorize/2-calendar-authorize-continue.png)

Confirm:

![confirm](../doc/calendar/authorize/3-calendar-authorize-confirm.png)

Confirmation:

![confirmation](../doc/calendar/authorize/4-calendar-authorize-confirmation.png)

</details>

## [Disclaimer On Authorization Token](../../OAUTH.md)
