import sys

from . import api

import maintainers_and_authors.api

def main(args=sys.argv[1:]) -> int:

    sender_name = args[0]
    min_python_version = maintainers_and_authors.api.version_tuple_from_str(args[1]) if len(args) >= 1 else ()
    project_name = maintainers_and_authors.api.version_tuple_from_str() if len(args) >= 2 else None

    api.send_email_to_all_dependents(
        sender_name,
        min_python_version,
        project_name,
    )

    return 0