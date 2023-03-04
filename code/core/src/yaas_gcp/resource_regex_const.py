# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""Default values related to Cloud Run."""
import re
from typing import Tuple

######################
# Cloud Run Resource #
######################

FQN_CLOUD_RUN_RESOURCE_REGEX_ORDER: Tuple[int, int, int] = (0, 1, 2)
FQN_CLOUD_RUN_RESOURCE_REGEX: re.Pattern = re.compile(
    pattern=r"^projects/([^/\s]+)/locations/([^/\s]+)/services/([^/\s]+)$",
    flags=re.IGNORECASE,
)
"""
Input example::
    projects/my_project/locations/europe-west3/services/my_service
Groups on matching are::
    project, location, service = FQN_CLOUD_RUN_RESOURCE_REGEX.match(line).groups()
"""

FQN_CLOUD_RUN_TERRAFORM_RESOURCE_REGEX_ORDER: Tuple[int, int, int] = (1, 0, 2)
FQN_CLOUD_RUN_TERRAFORM_RESOURCE_REGEX: re.Pattern = re.compile(
    pattern=r"^locations/([^/\s]+)/namespaces/([^/\s]+)/services/([^/\s]+)$",
    flags=re.IGNORECASE,
)
"""
Input example::
    locations/europe-west3/namespaces/my_project/services/my_service
Groups on matching are::
    location, project, service = FQN_CLOUD_RUN_TERRAFORM_RESOURCE_REGEX.match(line).groups()
"""

SIMPLE_CLOUD_RUN_RESOURCE_REGEX_ORDER: Tuple[int, int, int] = (1, 2, 0)
SIMPLE_CLOUD_RUN_RESOURCE_REGEX: re.Pattern = re.compile(
    pattern=r"^CloudRun\.?\s*\.?\s*"
    + r"\s+"  # separator <space>
    + r"([^@\s]+)"  # service
    + r"\s*\.?\s*@\.?\s*"  # separator @
    + r"([^\s]+)"  # project
    + r"\s*\.?\s+\.?\s*"  # separator <space>
    + r"([^\s]+)$",  # region
    flags=re.IGNORECASE,
)
"""
Input example::
    CloudRun my_service @ my_project europe-west3
Groups on matching are::
    service, project, location = SIMPLE_CLOUD_RUN_RESOURCE_REGEX.match(line).groups()
"""


######################
# Cloud SQL Resource #
######################

FQN_CLOUD_SQL_RESOURCE_REGEX_ORDER: Tuple[int, int, int] = (0, 1, 2)
FQN_CLOUD_SQL_RESOURCE_REGEX: re.Pattern = re.compile(
    pattern=r"^([^:\s]+):([^:\s]+):([^:\s]+)$",
    flags=re.IGNORECASE,
)
"""
Input example::
    my_project:europe-west3:my_instance
Groups on matching are::
    project, location, instance = FQN_CLOUD_SQL_RESOURCE_REGEX.match(line).groups()
"""

SIMPLE_CLOUD_SQL_RESOURCE_REGEX_ORDER: Tuple[int, int, int] = (1, 2, 0)
SIMPLE_CLOUD_SQL_RESOURCE_REGEX: re.Pattern = re.compile(
    pattern=r"^CloudSQL\.?\s*\.?\s*"
    + r"\s+"  # separator <space>
    + r"([^@\s]+)"  # instance
    + r"\s*\.?\s*@\.?\s*"  # separator @
    + r"([^\s]+)"  # project
    + r"\s*\.?\s+\.?\s*"  # separator <space>
    + r"([^\s]+)$",  # region
    flags=re.IGNORECASE,
)
"""
Input example::
    CloudSql my_instance @ my_project europe-west3
Groups on matching are::
    instance, project, location = SIMPLE_CLOUD_SQL_RESOURCE_REGEX.match(line).groups()
"""

##############################
# Canonical format templates #
##############################

CLOUD_RUN_RESOURCE_NAME_TMPL: str = "projects/{0:}/locations/{1:}/services/{2:}"
CLOUD_SQL_RESOURCE_NAME_TMPL: str = "{0:}:{1:}:{2:}"
