#!/bin/bash
source $(dirname ${BASH_SOURCE})/../util.sh


nginx_yaml=$(relative nginx.yaml)
run "kubectl delete -f ${nginx_yaml}"
run "kubectl apply -f ${nginx_yaml}"
sleep 5

tmux kill-pane -t 1
desc "CHOWN was denied... Let's add this capabilities to our deployment file"
run "kubectl delete -f ${nginx_yaml}"
run "nano ${nginx_yaml}"
run "kubectl apply -f ${nginx_yaml}"
run "kubectl wait -n demo --for=condition=ready deployment/nginx-deployment"

desc "Everything is ready! Let's try to curl the webserver!"
run "kubectl get service -n demo"
ip=$(kubectl get service -n demo --no-headers | awk '{ print $4 }')
run "curl ${ip}"

sleep 5
