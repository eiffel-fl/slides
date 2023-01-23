#!/bin/bash

kubectl delete ns demo || true
kubectl create ns demo
