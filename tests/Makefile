all: perf

spawn: 
	gcc -O2 -g -o spawn spawn.c

hierarchylock:
	g++ -O2 -g -Wall -O3  -std=c++2a -lpthread -o hierarchylock hierarchylock.cpp

perf: spawn hierarchylock
#	perf record -e "cpu/mem-loads,ldlat=30/P,cpu/mem-stores/P,cycles:pp,instructions:pp" -W -d --phys-data --sample-cpu -a -g --call-graph dwarf -F99 -o perf.data.spawn -- ./spawn 10000
	perf record -e "cpu/mem-loads,ldlat=30/P,cpu/mem-stores/P,cycles:P,instructions:P" -W -d --phys-data --sample-cpu -a -g --call-graph dwarf -F99 -o perf.data.lock -- ./hierarchylock -t 160 -l 1 -i 100000

clean: clean_binary clean_perf

clean_perf:
	rm perf.data* -rf

clean_binary:
	rm spawn -rf
	rm hierarchylock -rf


test: 
	perf script -s python:../scripts/perf_script_function_call_graph.py -i perf.data.lock
debug:
	perf script -s python:../scripts/flamegraph.py -i perf.data.lock -- -d -l 10.239.147.41 -p 5678 -i perf.data.lock

