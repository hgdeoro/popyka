# Steps for releasing a new DEV version

### Prepare & checks

    $ pre-commit run --all-files
    $ make tox-quick
    $ make test-system
    $ make version-incr-dev


# Steps for releasing a new STABLE version

### Prepare & checks

    $ pre-commit run --all-files
    $ make tox
    $ python tox2badge.py
    $ make test-system
    # update README with output of `tox2badge.py`
    # check fixmes
    # check README

### Release

    $ make [release-patch | release-minor]
    # create release in gitlab
    # update Makefile: `DOCKER_IMAGE_TAG_RELEASE`


# Appendix

### How hatch works with dev versions

When work is done, use `release`:

    $ hatch version release
    Old: 0.2.0.dev0
    New: 0.2.0

When work start, use `patch,dev`:

    $ hatch version patch,dev
    Old: 0.2.0
    New: 0.2.1.dev0
