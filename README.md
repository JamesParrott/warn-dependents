# warn_dependents
Email the authors and maintainers of all projects using a PyPi project (e.g. yours) downstream.  By default, warn them it is intended to drop support for old Python versions.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [License](#license)

## Installation

```console
uv tool install warn-dependents
```

## Usage

The user interface deliberately reads from stdin (via maintainers-and-authors).

echo project_name | warn-dependents <sender_name> <sender_email> <project_name> <discussion_link> <Python_version>


## Usage

Breaking the steps down allows checks that all the required APIs are working,and double checking the list of recipients of the emails before hitting "send":

Bash
```console
rev-deps project_name > revdeps.txt
cat revdeps.txt | maintainers-and-authors > emails.txt
SPARKPOST_API_KEY=_____________ 
cat revdeps.txt | warn_dependents "Your name" yourself@example.com project_name https://www.github.com/user_or_org/project_name/discussions 3.14
```

Cmd.exe
```console
rev-deps project_name > revdeps.txt
type revdeps.txt | maintainers-and-authors > emails.txt
set SPARKPOST_API_KEY=_____________ 
type revdeps.txt | warn_dependents "Your name" yourself@example.com project_name https://www.github.com/user_or_org/project_name/discussions 3.14
```

To live dangerously and do it all on one line:
```
SPARKPOST_API_KEY=_____________ && echo project_name | warn-dependents "Your name" yourself@example.com project_name https://www.github.com/user_or_org/project_name/discussions 3.14
```

## License
AGPL3

