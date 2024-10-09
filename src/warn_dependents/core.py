import os
import string

import requests

import maintainers_and_authors.api


def _make_email_payload(
    to: str,
    sender_name: str,
    min_python_version: tuple,
    upstream_project_name: str,
    projects_meta_data: dict, 
    subject: str | None = None,
    ,**kwargs):

    subject = subject or (f'{upstream_project_name.capitalize()} to drop support '
                          f' for Pythons older than '
                          f'{".".join(str(x) for x in min_python_version)}. '
    )

    message_body = """\
    Wubalubadubdub!!!

    This is a test email, sent from Python via Plunk's REST API.

    """


    # https://docs.useplunk.com/api-reference/transactional/send
    kwargs.update(
        to = to,
        subject = subject,
        body = message_body,
        name = sender_name,
        # "subscribed": # Defaults to False,
        # "name": None, # Sender name.  Defaults to project name
        # "from": defaults to verified email address,
        # "reply": defaults to verified email address,
        "headers": {},
    )

    return kwargs
    
def _send_email(email_address, email_payload):

    url = "https://api.useplunk.com/v1/send/"

    headers = {
        "Content-Type": "application/json",
        f"Authorization": "Bearer {os.getenv('PLUNK_API_KEY')}",
    }

    return requests.post(url, json=email_payload, headers=headers)


def _send_email_to_all_dependents(
    sender_name: str,
    min_python_version: tuple,
    upstream_project_name: str | None = None,
    make_email_payload = _make_email_payload,
    send_email = _send_email,
    **kwargs
    ) -> None:

    maintnrs_and_authors_meta_data = maintainers_and_authors.api.email_addresses(min_python_version)

    for email_address, projects_meta_data in maintnrs_and_authors_meta_data.items():

        email_payload = make_email_payload(
            to=email_address,
            sender_name=sender_name,
            min_python_version=min_python_version,
            upstream_project_name=upstream_project_name,
            projects_meta_data=projects_meta_data,
            **kwargs
            )

        send_email(email_address, email_payload)

