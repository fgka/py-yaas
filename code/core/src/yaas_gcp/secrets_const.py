# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""Default values related to Cloud Run."""
from typing import List

###################
#  Resource name  #
###################

SECRET_NAME_TOKENS: List[str] = ["projects", "secrets", "versions"]

VERSION_SUB_STR: str = "/versions/"
LATEST_VERSION_SUFFIX: str = f"{VERSION_SUB_STR}latest"

###########################
#  Update Request: paths  #
###########################

GCP_SECRET_NAME_TMPL: str = "projects/{project_id}/secrets/{secret_id}/versions/{version}"
DEFAULT_GCP_SECRET_VERSION: str = "latest"
