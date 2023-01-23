DEMO_LIST ?= $(shell find . -mindepth 1 -type d)

export PATH := $(PATH):/home/francis/Codes/kinvolk:/home/francis/.local/bin:$(shell pwd)

all: $(addsuffix /demo.gif,$(DEMO_LIST))

%/demo.gif: %/*.sh
	@echo "Demo $*"
	rm -f $*/demo.cast $*/demo.gif
	@echo "Demo $*: initialization"
	[ ! -x "$*/init.sh" ] || $*/init.sh
	DEMO_AUTO_RUN=1 TERM=tmux asciinema rec -c "bash $*/demo.sh" $*/demo.cast
	@echo "Demo $*: finalization"
	[ ! -x "$*/fini.sh" ] || $*/fini.sh
	cat $*/demo.cast
	@echo "Demo $*: converting cast file to gif"
	agg $*/demo.cast $*/demo.gif
	ls -lh $*/demo.gif

.PHONY: list
list:
	@echo $(DEMO_LIST)

clean:
	rm -f */*.cast */*.gif
