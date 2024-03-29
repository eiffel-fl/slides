#!/bin/bash
source $(dirname ${BASH_SOURCE})/../util.sh


sleep 25
run "docker run --rm --name nginx-container -p 8081:80 -d nginx"
run "curl localhost:8081"
desc "We can now stop our container, it will stop local-gadget too!"
run "docker stop nginx-container"

clear
desc "Let's compare the generated seccomp profile to the one we used previously:"
profile_json=$(relative profile.json)
profile_gadget_json=$(relative profile_gadget.json)
run "diff -u $profile_json $profile_gadget_json"
desc "Hum... It seems we forgot a syscall in the seccomp profile we wrote by hand!"

desc "Let's create again the container with the seccomp profile generated by local-gadget!"
run "docker run --rm --name nginx-container -p 8081:80 -d --security-opt seccomp=$profile_gadget_json nginx"
run "curl localhost:8081"

sleep 5
