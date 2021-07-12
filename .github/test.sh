#!/bin/dash

pip install -e /openedx/requirements/eol_vimeo

cd /openedx/requirements/eol_vimeo
cp /openedx/edx-platform/setup.cfg .

cd /openedx/edx-platform
mkdir test_root
cd test_root/
ln -s /openedx/staticfiles .
cd ..
#openedx-assets collect --settings=prod.assets

cd /openedx/requirements/eol_vimeo
pip install pytest-cov genbadge[coverage]
sed -i '/--json-report/c addopts = --nomigrations --reuse-db --durations=20 --json-report --json-report-omit keywords streams collectors log traceback tests --json-report-file=none --cov=/openedx/requirements/eol_vimeo/eol_vimeo/ --cov-report term-missing --cov-report xml:/openedx/requirements/eol_vimeo/reports/coverage/coverage.xml --cov-fail-under 70' setup.cfg

cd /openedx/edx-platform
EDXAPP_TEST_MONGO_HOST=mongodb python -Wd -m pytest --ds=cms.envs.test --junitxml=/openedx/edx-platform/reports/cms/nosetests.xml /openedx/requirements/eol_vimeo/eol_vimeo/tests.py
migrations
cd /openedx/requirements/eol_vimeo
genbadge coverage