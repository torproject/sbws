#!/usr/bin/env bash

function finish {
	[ -f "./chutney" ] && ./chutney stop $NETWORK
	popd &>/dev/null
}
trap finish EXIT

function usage {
	echo "$0 CHUTNEY_DIR BW_START BW_INC"
}

NETWORK="networks/sbws"

CHUTNEY_DIR=${1:-$HOME/src/chutney}
shift
BW_START=${1:-1024}
shift
BW_INC=${1:-1024}
shift

[ ! -d "$CHUTNEY_DIR" ] && echo "$CHUTNEY_DIR does not exist" && usage && exit 1
[ ! -f "$CHUTNEY_DIR/chutney" ] && echo "$CHUTNEY_DIR does not seem to contain chutney" && usage && exit 1

pushd "$CHUTNEY_DIR"
./chutney configure $NETWORK

bw="${BW_START}"
for node in net/nodes/*r
do
	torrc=${node}/torrc
	echo "BandwidthRate $bw KBytes" >> "$torrc"
	bw=$((bw+BW_INC))
	echo "BandwidthBurst $bw KBytes" >> "$torrc"
done

./chutney start $NETWORK
sleep 5
