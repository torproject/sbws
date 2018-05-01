#!/usr/bin/env bash
set -e
function cleanup {
	kill $(jobs -p)
	echo -n ''
}
trap cleanup EXIT

function list_of_nets {
	find . -mindepth 2 -maxdepth 2 -type f -name '.net' |\
		xargs dirname | sort -u | xargs
}

function usage {
	echo "Usage: $0 <net>"
	echo "Where <net> is one of: $(list_of_nets)"
}

[ "$1" == "" ] && usage && exit 1 || net="$1"
[ ! -d "$net" ] && usage && exit 1
[ ! -f "$net/.net" ] && usage && exit 1

pushd $net
./01-gen-configs.sh
./02-start-network.sh
sleep 5
num_relays=$(ls -ld {auth,relay,exit}* | wc -l)
echo "Waiting until network of $num_relays relays is ready ..."
time ./03-network-in-ready-state.py auth* relay* exit* --size $num_relays
echo 'All ready!'

#sbws -d . server > debug.server.log &
#sleep 1
sbws -d . scanner > debug.scanner.log &

run_time="45"
echo "Running for $run_time seconds ..."
sleep $run_time

sbws -d . generate | tee generate.log
sbws -d . stats | tee stats.log

./04-stop-network.sh
