#!/usr/bin/env bash
set -e
function cleanup {
	#kill -INT $(cat {auth,relay,exit}*/tor.pid)
	#kill -INT $(jobs -p)
	echo -n ''
}
trap cleanup EXIT


cd $(dirname $0)
for A in {auth,relay,exit}*
do
	tor -f $A/torrc --quiet &
done
