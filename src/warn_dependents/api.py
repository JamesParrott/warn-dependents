from . import core


def send_email_to_all_dependents(
    sender_name: str,
    sender_email: str,
    min_python_version: tuple,
    project_name: str,
    discussion_link: str,
) -> None:
    return core._send_email_to_all_dependents(
        sender_name,
        sender_email,
        min_python_version,
        project_name,
        discussion_link,
    )
