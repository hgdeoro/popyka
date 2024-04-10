# Steps for releasing  a new version

### Prepare & checks

    pre-commit run --all-files
    tox
    # check fixmes
    # check README

### Release

    make [release-patch | release-minor]
    # create release in gitlab
