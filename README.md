# Export content of a Ryver account

This exports all the content of a Ryver account that an authenticated user can
access.
Private data that are not reachable by the authenticated user *will not* be
exported.

## Install

This requires [Python](https://www.python.org) and [Poetry](https://python-poetry.org/docs/#installation):

1. Install Python
1. Install [Poetry](https://python-poetry.org/docs/#installation)
1. Run: `poetry install`

## Usage

```
poetry run ./ryver.py \
  export-dir \
  my-domain.ryver.com \
  jon@example.com \
  secret123 \
    --ignore team=42 \
    --ignore forum=78 \
    --ignore user=456 \
  --messages-quantity=2000
```

This takes a while, be patient!
