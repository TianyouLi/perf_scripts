qall: perf

spawn: 
	gcc -O2 -g -o spawn spawn.c

perf: spawn
	perf record -e "cpu/mem-loads,ldlat=30/P,cpu/mem-stores/P,cycles:pp,instructions:pp" -W -d --phys-data --sample-cpu -a -g -o perf.data.spawn ./spawn 10000 

clean: clean_spawn clean_perf

clean_perf:
	rm perf.data* -rf

clean_spawn:
	rm spawn -rf


test: 
	perf script -s python:../scripts/cccost.py -i perf.data.spawn report 

