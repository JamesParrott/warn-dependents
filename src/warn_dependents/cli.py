import sys

from . import api

import maintainers_and_authors.api

def main(args=sys.argv[1:]) -> int:

    sender_name = args[0]
    project_name = args[1]
    min_python_version = maintainers_and_authors.api.version_tuple_from_str(args[2]) if len(args) >= 3 else (3,9)

    api.send_email_to_all_dependents(
        sender_name,
        min_python_version,
        project_name,
    )

    return 0