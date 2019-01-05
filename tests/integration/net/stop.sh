#!/usr/bin/env bash

cd $(dirname $0)
kill -INT $(cat {auth,relay,exit}*/tor.pid)
