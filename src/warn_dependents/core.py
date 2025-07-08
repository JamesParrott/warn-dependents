import pathlib
from typing import Iterator

import nameutils
from sparkpost import SparkPost

import maintainers_and_authors.api


def _python_version_clauses(meta_data: dict[str, str]) -> Iterator[tuple[str, str]]:
    clauses = meta_data.get("requires_python")
    if clauses:
        for clause in clauses.split(","):
            clause = clause.strip().replace(" ", "")

            if clause.startswith("==="):
                yield "===", clause[3:]
                continue

            if clause[1] != "=":
                assert clause[0] in "<>"
                yield clause[0], clause[1:]
                continue

            assert clause[0] in "<~!=>", (
                f"Non-compliant clause: {clause} in project: {meta_data['name']}"
            )

            yield clause[:2], clause[2:]


def _python_version_classifiers(
    meta_data: dict[str, str],
) -> Iterator[tuple[str, tuple]]:
    if "classifier" in meta_data:
        for entry in meta_data["classifier"]:
            if not entry.startswith("Programming Language :: Python ::"):
                continue
            category = (
                entry.removeprefix("Programming Language :: Python ::")
                .partition("::")[0]
                .strip()
            )
            try:
                version = maintainers_and_authors.api.version_tuple_from_str(category)
            except ValueError:
                continue
            if version == (3,):
                continue
            yield entry, version


def _given_names(full_name: str) -> str:
    nameparts = nameutils.nameparts(full_name)[1:]

    if not nameparts:
        return full_name

    if len(nameparts) == 1:
        return nameparts[0]

    return " ".join(nameparts[1:])


def _make_email_payload(
    to: frozenset[str],
    sender_name: str,
    sender_email: str,
    min_python_version: tuple,
    upstream_project_name: str,
    discussion_link: str,
    projects_data: dict,
    subject: str | None = None,
    **kwargs,
):
    first_project_name, first_project = next(iter(projects_data.items()))

    full_names_for_emails = dict(zip(*first_project["maintainers_and_authors"]))

    upstream_project_name = upstream_project_name.capitalize()
    min_python_version_str = ".".join(str(x) for x in min_python_version)
    maintainers_and_authors_given_names = ", ".join(
        _given_names(full_names_for_emails[email]) for email in to
    )

    subject = subject or (
        f"{upstream_project_name} to drop support for "
        f"Pythons older than {min_python_version_str}. "
    )

    message_body = f"""\
Dear {maintainers_and_authors_given_names or "Sir/Madam"},

The developers of {upstream_project_name} (including myself) are considering dropping 
support for Pythons older than version {min_python_version_str}.  Any feedback 
about this is most welcome on our discussions page:
{discussion_link}
particularly if it would have adverse effects for your projects: {", ".join(projects_data)}.

No projects will be broken, as no old versions of {upstream_project_name} will be yanked.  This
decision would just mean your own users, that use older Python versions, would 
not be able to install the latest version of {upstream_project_name}.  If new bugs in older versions
of {upstream_project_name} for older Pythons are found, the default advice would become "upgrade Python to 
a supported version".

Thanks for using {upstream_project_name}!

{sender_name}.

    
P.S. You have received this email because all of the following conditions have been met:
i) Your projects: {", ".join(projects_data)} are listed as reverse dependencies of {upstream_project_name} on Wheelodex.
ii) For a Python version we propose to drop, no clause was found to prevent installation of each of these projects.   
iii) For each of these projects, either there were no Python version trove classifiers, or they included a 
Python version we propose to drop.  
Further details below:\
"""

    for project_name, project_data in projects_data.items():
        message_body = f"""{message_body}
Project: {project_name}
Python version constraints (all enforced by pip) {project_data["requires_python_clauses"]}
"""
        classifiers_info = (
            f"""\
Python version trove classifiers: 
{"\n".join(project_data["unsupported_trove_classifiers"])}
"""
            if project_data["trove_classifiers"]
            else """
No Python version trove classifiers found."""
        )

        message_body = f"{message_body}{classifiers_info}"

    html = f'<div dir="ltr">\n{message_body}</div>\n\n'.replace("\n", "<br>\n")

    kwargs.update(
        to=list(to),
        subject=subject,
        text=message_body,
        html=html,
        sender=sender_email,
        # tag = 'deprecation_announcement', #f'Feedback request re: {upstream_project_name} dropping old Python versions.'
        # "subscribed": # Defaults to False,
        # "name": None, # Sender name.  Defaults to project name
        # "from": defaults to verified email address,
        # "reply": defaults to verified email address,
        # headers = {},
        # message_stream='broadcast',
    )

    return kwargs


EMAILS_FILE = pathlib.Path("emails.txt")


sp = SparkPost()  # uses environment variable SPARKPOST_API_KEY


def _send_email_via_sparkpost(email_payload):
    with open(EMAILS_FILE, "at") as f:
        f.write(
            f"Sending email to: {email_payload['to']}\n Subject: {email_payload['subject']}\n {email_payload['html']} \n\n"
        )

    # return None

    return sp.transmissions.send(
        recipients=email_payload.pop("to"),
        from_email=email_payload.pop("sender"),
        **email_payload,
    )

    # https://github.com/SparkPost/python-sparkpost?tab=readme-ov-file#send-a-message
    # return sp.transmissions.send(
    #     recipients=['test@example.com'],
    #     html='<p>Hello world</p>',
    #     from_email='you@mail.example.com',
    #     subject='Hello from python-sparkpost'
    # )


def _send_email_to_all_dependents(
    sender_name: str,
    sender_email: str,
    min_python_version: tuple,
    upstream_project_name: str,
    discussion_link: str,
    make_email_payload=_make_email_payload,
    # send_email = _send_email,
    maintnrs_and_authors_meta_data: dict | None = None,
    **kwargs,
) -> None:
    def excludes_unsupported_versions(
        comparison_operator: str,
        version_identifier: tuple,
    ) -> bool:
        if (
            comparison_operator
            in {
                ">",  # Misses '>' highest released version  below min_python_version,
                # e.g. > 3.1.9999999 would work just fine with >= 3.2
                # unless the patch version has exceeded 10 million.
                ">=",
                "==",  # Could miss an exclusion. Wild cards not processed.
                "===",
                "~=",  # Could miss an exclusion.
            }
            and maintainers_and_authors.api.version_tuple_from_str(version_identifier)
            >= min_python_version
        ):
            return True

        # Misses an exhaustive list of version exclusions of earlier versions with '!='

        return False

    if maintnrs_and_authors_meta_data is None:
        # Reads from stdin.  Pipe project names from file or rev-deps.
        maintnrs_and_authors_meta_data = maintainers_and_authors.api.email_addresses(
            min_python_version
        )

    # context = ssl.create_default_context()
    # with smtplib.SMTP('smtp.useplunk.com',587) as smtp:
    #     smtp.starttls(context=context)
    #     smtp.login('plunk', os.getenv('PLUNK_API_KEY'))

    # payloads = []

    for email_addresses, projects_data in maintnrs_and_authors_meta_data.items():
        project_names = list(projects_data)

        for project_name in project_names:
            project_data = projects_data[project_name]

            meta_data = project_data["meta_data"]

            clauses = list(_python_version_clauses(meta_data))
            # clauses = meta_data.get('requires_python',[])

            if any(excludes_unsupported_versions(*clause) for clause in clauses):
                #
                projects_data.pop(project_name)
                continue

            classifiers = list(_python_version_classifiers(meta_data))

            classifiers_older_than_min_supported = [
                entry for entry, version in classifiers if version < min_python_version
            ]

            if classifiers and not classifiers_older_than_min_supported:
                projects_data.pop(project_name)
                continue

            project_data["requires_python_clauses"] = clauses
            project_data["trove_classifiers"] = classifiers
            project_data["unsupported_trove_classifiers"] = (
                classifiers_older_than_min_supported
            )

        if not projects_data:
            # None of the projects support the versions of Python to be dropped,
            # so there is no need to warn their authors and maint.
            continue

        email_payload = make_email_payload(
            to=email_addresses,
            sender_name=sender_name,
            sender_email=sender_email,
            min_python_version=min_python_version,
            upstream_project_name=upstream_project_name,
            discussion_link=discussion_link,
            projects_data=projects_data,
            **kwargs,
        )

        # payloads.append(email_payload)

        # smtp.sendmail(
        #     'test@example.com',
        #     ', '.join(email_addresses),
        #     f"Subject: {email_payload['subject']}\n\n{email_payload['body']}",
        #     )

        _send_email_via_sparkpost(email_payload)

    # >>> with open('pyshp_rev_deps.txt','at') as f, open('rdepends.json','rt') as j:
    # ...     f.write('\n'.join(entry["name"].lower().replace('_','-') for entry in json.load(j)['items']))
    #

    # EMAILS_FILE.write_text(json.dumps(payloads))

    # with open(EMAILS_FILE, 'at') as f:
    #     for payload in payloads:
    #         f.write(f'Sending email to: {payload["to"]}\n From: {payload["sender"]}\nSubject: {payload["subject"]}\n {payload["html"]} \n\n')

    # return None

    # response = pystmark.send_batch([pystmark.Message(**payload)
    #                                 for payload in payloads
    #                                ],
    #                                api_key=os.getenv('POSTMARK_API_KEY')
    #                               )

    # print(f'{response.status_code=}')
    # print(f'{response.text=}')

    # return response
