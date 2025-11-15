# Opencast ACL Mirroring Script

This script copies and augments ACLs from one Opencast series to another. It reads the source series ACL, generates new ACL entries based on the target series description, applies them to the source series and all its events, then republishes metadata so the changes take effect.

## Features

- Fetch ACLs for series and events.
- Update ACLs for series and events.
- Search for series interactively.
- Apply updated ACLs to the source series and its events.
- Republish metadata for updated events.

## Requirements

- Python 3.7+
- `requests` library
- Valid Opencast credentials with permissions to read and modify ACLs and start workflows

Install dependencies:

```bash
pip install requests