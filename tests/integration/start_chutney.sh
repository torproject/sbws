#!/bin/bash
set -x

CURRENT_DIR=`pwd`
CHUTNEY_DIR=${1:-./chutney}

# If chutney dir already exists, this will fail but it doesn't matter.
git clone https://git.torproject.org/chutney.git $CHUTNEY_DIR

cp tests/integration/chutney_data/bwscanner $CHUTNEY_DIR/networks
cp tests/integration/chutney_data/*.tmpl $CHUTNEY_DIR/torrc_templates

cd $CHUTNEY_DIR
# In case it wasn't cloned recently, pull.
# Since this is run only for the tests, it's ok if the tests fail with a newer
# chutney version, so that we can detect it early.
git pull

# Stop chutney network if it is already running
./chutney stop networks/bwscanner
./chutney configure networks/bwscanner
./chutney start networks/bwscanner
./chutney status networks/bwscanner
./chutney wait_for_bootstrap networks/bwscanner

# temporal workaround for https://gitlab.torproject.org/tpo/core/chutney/-/issues/40016
sleep 60
cd $CURRENT_DIR
