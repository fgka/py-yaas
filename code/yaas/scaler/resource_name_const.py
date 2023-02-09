# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""
Default values related to Cloud Run.
"""
import re


######################
# Cloud Run Resource #
######################

FQN_CLOUD_RUN_TARGET_RESOURCE_REGEX: re.Pattern = re.compile(
    pattern=r"^projects/([^/\s]+)/locations/([^/\s]+)/services/([^/\s]+)$",
    flags=re.IGNORECASE,
)
"""
Input example::
    projects/my_project/locations/europe-west3/services/my_service
Groups on matching are::
    project, location, service = _FQN_CLOUD_RUN_TARGET_RESOURCE_REGEX.match(line).groups()
"""
# pylint: disable=anomalous-backslash-in-string
SIMPLE_CLOUD_RUN_TARGET_RESOURCE_REGEX: re.Pattern = re.compile(
    pattern=r"^CloudRun\.?\s*\.?\s*"
    + r"\s+"  # separator <space>
    + r"([^@\s]+)"  # service
    + r"\s*\.?\s*@\.?\s*"  # separator @
    + r"([^\s]+)"  # project
    + r"\s*\.?\s+\.?\s*"  # separator <space>
    + r"([^\s]+)$",  # region
    flags=re.IGNORECASE,
)
# pylint: enable=anomalous-backslash-in-string
"""
Input example::
    CloudRun my_service @ my_project europe-west3
Groups on matching are::
    service, project, location = _SIMPLE_CLOUD_RUN_TARGET_RESOURCE_REGEX.match(line).groups()
"""
CLOUD_RUN_RESOURCE_NAME_TMPL: str = "projects/{}/locations/{}/services/{}"


######################
# Cloud SQL Resource #
######################

FQN_CLOUD_SQL_TARGET_RESOURCE_REGEX: re.Pattern = re.compile(
    pattern=r"^([^:\s]+):([^:\s]+):([^:\s]+)$",
    flags=re.IGNORECASE,
)
"""
Input example::
    my_project:europe-west3:my_instance
Groups on matching are::
    project, location, instance = _FQN_CLOUD_RUN_TARGET_RESOURCE_REGEX.match(line).groups()
"""
# pylint: disable=anomalous-backslash-in-string
SIMPLE_CLOUD_SQL_TARGET_RESOURCE_REGEX: re.Pattern = re.compile(
    pattern=r"^CloudSQL\.?\s*\.?\s*"
    + r"\s+"  # separator <space>
    + r"([^@\s]+)"  # instance
    + r"\s*\.?\s*@\.?\s*"  # separator @
    + r"([^\s]+)"  # project
    + r"\s*\.?\s+\.?\s*"  # separator <space>
    + r"([^\s]+)$",  # region
    flags=re.IGNORECASE,
)
# pylint: enable=anomalous-backslash-in-string
"""
Input example::
    CloudSql my_instance @ my_project europe-west3
Groups on matching are::
    instance, project, location = _SIMPLE_CLOUD_SQL_TARGET_RESOURCE_REGEX.match(line).groups()
"""
CLOUD_SQL_RESOURCE_NAME_TMPL: str = "{}:{}:{}"
