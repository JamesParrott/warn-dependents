import os
import pathlib
import string
from typing import Iterator

import requests
import nameutils

import maintainers_and_authors.api




def _python_version_clauses(meta_data: dict[str, str]) -> Iterator[tuple[str, str]]:
    
    if 'requires_python' in meta_data:

        for clause in meta_data['requires_python'].split(','):

            clause = clause.strip().replace(' ','')

            if clause.startswith('==='):
                yield '===', clause[3:]
                continue

            if clause[1] != '=':
                assert clause[0] in '<>'
                yield clause[0], clause[1:]
                continue

            assert clause[0] in '<~!=>', f'Non-compliant clause: {clause} in project: {meta_data["name"]}'

            yield clause[:2], clause[2:]


def _python_version_classifiers(meta_data: dict[str, str]) -> Iterator[tuple[str, tuple]]:
    if 'classifier' in meta_data:
        older_supported_versions = []
        for entry in meta_data['classifier']:
            if not entry.startswith('Programming Language :: Python ::'):
                continue
            category = entry.removeprefix('Programming Language :: Python ::').partition('::')[0].strip()
            try:
                version = maintainers_and_authors.api.version_tuple_from_str(category)
            except ValueError:
                pass
            else:
                yield entry, version


def _given_names(full_name: str) -> str:
    nameparts = nameutils.nameparts(full_name)[1:]
    
    if not nameparts:
        return full_name

    if len(nameparts) == 1:
        return nameparts[0]
    
    return ' '.join(nameparts[1:])




def _make_email_payload(
    to: frozenset[str],
    sender_name: str,
    min_python_version: tuple,
    upstream_project_name: str,
    projects_data: dict, 
    subject: str | None = None,
    **kwargs
    ):

    first_project_name, first_project = next(iter(projects_data.items()))

    project_names = list(projects_data)

    first_project_full_names = next(iter(projects_data.values()))['maintainers_and_authors']

    upstream_project_name = upstream_project_name.capitalize()
    min_python_version_str = ".".join(str(x) for x in min_python_version)
    maintainers_and_authors_given_names = ', '.join(
                    _given_names(full_name)
                    for full_name in next(iter(projects_data.values()))['maintainers_and_authors'][1]
                    )

    subject = subject or (f'{upstream_project_name} to drop support for '
                          f'Pythons older than {min_python_version_str}. '
                         )



    message_body = f"""\
    Dear {maintainers_and_authors_given_names or 'fellow project developer(s)'},

    The developers of {upstream_project_name}, are considering dropping 
    support for Pythons older than version {min_python_version_str}.  Please
    post any feedback regarding this decision on our discussions page:
    http://www.github.com/{kwargs.get('Github_organisation', 'GeospatialPython')}/{upstream_project_name}/discussions
    particularly if it would have adverse effects for your projects: {', '.join(projects_data)}.

    No projects will be broken, as no old versions of {upstream_project_name} will be yanked.  This
    decision would just mean users that use older Python versions, that use your projects, would 
    not be able to install the latest version of {upstream_project_name}.  If new bugs in older versions
    of {upstream_project_name} for older Pythons are found, the default advice would become "upgrade Python to 
    a supported version".
    
    Thanks for using {upstream_project_name}!

    {sender_name}.

    
    P.S. You have received this email because all of the following conditions have been met:
         i) Your projects: {', '.join(projects_data)} are listed as reverse dependencies of {upstream_project_name} on Wheelodex.
         ii) For a Python version we propose to drop, no clause was found to prevent installation of each of these projects.   
         iii) For each of these projects, either there were no Python version trove classifiers, or they included a 
         Python version we propose to drop.  
         Further details below:\
"""

    for project_name, project_data in projects_data.items():
        meta_data = project_data['meta_data']

        message_body = f"""{message_body}

         Project: {project_name}
         Python version constraints (all enforced by pip) {project_data['requires_python_clauses']}
"""
        classifiers_info = f"""\
         Python version trove classifiers: {('\n' + ' '*43).join(project_data['unsupported_trove_classifiers'])}\
""" if project_data['trove_classifiers'] else """
         No Python version trove classifiers found."""
        
        message_body = f"{message_body}{classifiers_info}"

    # https://docs.useplunk.com/api-reference/transactional/send
    kwargs.update(
        to = list(to),
        subject = subject,
        body = message_body,
        name = sender_name,
        # "subscribed": # Defaults to False,
        # "name": None, # Sender name.  Defaults to project name
        # "from": defaults to verified email address,
        # "reply": defaults to verified email address,
        headers = {},
    )

    return kwargs


EMAILS_FILE = pathlib.Path("emails.txt")

def _send_email(email_address, email_payload):

    with EMAILS_FILE.open('at') as f:
        f.write(f'Sending mail to: {email_address}\n subject: {email_payload["subject"]}\n message: {email_payload["body"]}\n')

    # url = "https://api.useplunk.com/v1/send/"

    # headers = {
    #     "Content-Type": "application/json",
    #     "Authorization": f"Bearer {os.getenv('PLUNK_API_KEY')}",
    # }

    # return requests.post(url, json=email_payload, headers=headers)


def _send_email_to_all_dependents(
    sender_name: str,
    min_python_version: tuple,
    upstream_project_name: str | None = None,
    make_email_payload = _make_email_payload,
    send_email = _send_email,
    **kwargs
    ) -> None:


    def excludes_unsupported_versions(
        comparison_operator: str,
        version_identifier: tuple,
        ) -> bool:
        
        
        if comparison_operator in {
            '>', # Misses '>' highest released version  below min_python_version, 
                 # e.g. > 3.1.9999999 would work just fine with >= 3.2
                 # unless the patch version has exceeded 10 million.
            '>=',
            '==',  # Could miss an exclusion. Wild cards not processed.
            '===',
            '~=',  # Could miss an exclusion.  
            } and maintainers_and_authors.api.version_tuple_from_str(version_identifier) >= min_python_version:
            return True

        # Misses an exhaustive list of version exclusions of earlier versions with '!='


        return False
    maintnrs_and_authors_meta_data = maintainers_and_authors.api.email_addresses(min_python_version)


    for email_addresses, projects_data in maintnrs_and_authors_meta_data.items():

        project_names = list(projects_data)

        for project_name in project_names:
            project_data = projects_data[project_name]

            meta_data = project_data['meta_data']

            clauses = list(_python_version_clauses(meta_data))

            if any(excludes_unsupported_versions(*clause)
                for clause in clauses):
                #
                projects_data.pop(project_name)
                continue

            classifiers = list(_python_version_classifiers(meta_data))

            classifiers_older_than_min_supported = [
                entry
                for entry, version in classifiers
                if version < min_python_version
            ]

            if classifiers and not classifiers_older_than_min_supported:
                projects_data.pop(project_name)
                continue

            project_data['requires_python_clauses'] = clauses
            project_data['trove_classifiers'] = classifiers
            project_data['unsupported_trove_classifiers'] = classifiers_older_than_min_supported


        if not projects_data:
            continue

        email_payload = make_email_payload(
            to=email_addresses,
            sender_name=sender_name,
            min_python_version=min_python_version,
            upstream_project_name=upstream_project_name,
            projects_data=projects_data,
            **kwargs
            )

        send_email(email_addresses, email_payload)

