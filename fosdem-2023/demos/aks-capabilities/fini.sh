#!/bin/bash

source $(dirname ${BASH_SOURCE})/../util.sh

nginx_yaml=$(relative nginx.yaml)
kubectl delete -f $nginx_yaml
kubectl delete ns demo || true
