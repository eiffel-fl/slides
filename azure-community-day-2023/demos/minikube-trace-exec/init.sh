#!/bin/bash

kubectl delete ns demo || true
kubectl create ns demo

sleep 5
