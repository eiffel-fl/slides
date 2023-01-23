#!/bin/bash
# Copyright 2016 The Kubernetes Authors.
# Copyright 2022 The Inspektor Gadget authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
source $(dirname ${BASH_SOURCE})/../util.sh


desc "Let's start an nginx web server using some capabilities"
nginx_yaml=$(relative nginx.yaml)
run "grep -A 9 capabilities ${nginx_yaml}"
run "kubectl apply -f ${nginx_yaml}"
run "kubectl get pod -n demo"
desc "Hum... The pod is not ready, let's take a look at its logs"
nginx_pod=$(kubectl get pod --no-headers -n demo | cut -d' ' -f1)
run "kubectl logs -n demo ${nginx_pod}"

desc "\"Operation not permitted\", let's trace the capabilities to see what can be wrong"
sleep 5

tmux new -d -s demo-session \
	"$(dirname ${BASH_SOURCE})/split1_kubectl.sh" \; \
	split-window -d "$(dirname $BASH_SOURCE)/split1_gadget.sh" \; \
	attach \;
