#!/usr/bin/env bash
set -e
function cleanup {
	kill -INT $(cat {auth,relay,exit}*/tor.pid)
}
trap cleanup EXIT


for A in {auth,relay,exit}*
do
	tor -f $A/torrc --quiet &
done

echo 'Waiting (press enter to stop everything) ...'
read B
