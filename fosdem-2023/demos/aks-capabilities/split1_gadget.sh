#!/bin/bash
source $(dirname ${BASH_SOURCE})/../util.sh


run "kubectl gadget trace capabilities -n demo"
