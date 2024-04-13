# Steps for releasing  a new version

### Prepare & checks

    pre-commit run --all-files
    tox
    python tox2badge.py
    make test-system
    # update README with output of `tox2badge.py`
    # check fixmes
    # check README

### Release

    make [release-patch | release-minor]
    # create release in gitlab
