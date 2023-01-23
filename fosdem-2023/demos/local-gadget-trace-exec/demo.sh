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

function foo {
	while true; do
		sleep .5
	done
}

desc "Let's create a test container!"
run "docker run --rm --name test-container -d busybox sh -c 'while true; do sleep .3; done'"

foo &

desc "Let's trace new process creation!"
run "sudo execsnoop"

desc "It works but what if we want to focus on container processes? Let's see what local-gadget can do!"
run "sudo local-gadget trace exec --timeout 5"

desc "local-gadget is container aware and focus on them!"
sleep 5