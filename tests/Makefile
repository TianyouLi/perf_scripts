all: perf

spawn: 
	gcc -O2 -g -o spawn spawn.c

perf: spawn
	perf record -e "cpu/mem-loads,ldlat=30/P,cpu/mem-stores/P,cycles:pp,instructions:pp" -a -g ./spawn 100

clean: clean_spawn clean_perf

clean_perf:
	rm perf.data* -rf

clean_spawn:
	rm spawn -rf


test: 
	perf script -s python:../scripts/cccost.py report

