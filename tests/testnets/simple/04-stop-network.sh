#!/usr/bin/env bash

kill -INT $(cat {auth,relay,exit}*/tor.pid)
