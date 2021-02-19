#!/bin/bash

set -x

CURRENT_DIR=`pwd`
CHUTNEY_DIR=${1:-./chutney}
cd $CHUTNEY_DIR
# Stop chutney network if it is already running
./chutney stop networks/bwscanner
cd $CURRENT_DIR
