import sys

from . import api

import maintainers_and_authors.api


def main(args=sys.argv[1:]) -> int:
    sender_name = args[0]
    sender_email = args[1]

    project_name = args[2]
    discussion_link = args[3]
    min_python_version = (
        maintainers_and_authors.api.version_tuple_from_str(args[4])
        if len(args) >= 5
        else (3, 9)
    )

    api.send_email_to_all_dependents(
        sender_name,
        sender_email,
        min_python_version,
        project_name,
        discussion_link,
    )

    return 0
