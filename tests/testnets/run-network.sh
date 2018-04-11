#!/usr/bin/env bash
set -e
function cleanup {
	kill $(jobs -p)
	echo -n ''
}
trap cleanup EXIT

function usage {
	echo "Usage: $0 <net>"
	echo "Where <net> is one of: $(find . -mindepth 1 -maxdepth 1 -type d | xargs )"
}

[ "$1" == "" ] && usage && exit 1 || net="$1"
[ ! -d "$net" ] && usage && exit 1

pushd $net
./01-gen-configs.sh
./02-start-network.sh
sleep 5
echo 'Waiting until network is ready ...'
time ./03-network-in-ready-state.py auth* relay* exit*
echo 'All ready!'

sbws -d . server > debug.server.log &
sleep 1
sbws -d . client > debug.client.log &

run_time="45"
echo "Running for $run_time seconds ..."
sleep $run_time

sbws -d . generate | tee generate.log
sbws -d . stats | tee stats.log

./04-stop-network.sh
