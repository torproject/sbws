#!/bin/bash
# The test networks for sbws use IP addresses in the 127.10/16 space and OS X
# only seems to give lo0 127.0.0.1/32. This adds 127.10.0.1-20 to lo0.
for ((i=1;i<20;i++))
do
    sudo ifconfig lo0 alias 127.10.0.$i up
done

