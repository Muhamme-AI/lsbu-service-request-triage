"""Service-request triage prototype.

A small, dependency-free (standard library only) engine that:

* reads service requests from a CSV file,
* checks required information is present,
* categorises each request with simple keyword rules,
* drafts an acknowledgement (template, optionally refined by an AI model),
* flags requests that need human review, and
* writes CSV / JSON / Markdown outputs.

Run ``python -m triage --help`` for the command line interface.
"""

__version__ = "1.0.0"
