---
theme           : "gaia"
transition      : "slide"
highlightTheme  : "monokai"
title           : "Introduction to Perf Script"
marp            : true
---

# Introduction to Perf Script
#### tianyou.li@intel.com

---

## Agenda
* Why need perf script
* What is perf script
* Built-in scripts
* Write your own scripts  

---

## Why need perf script

_Example 1_:

```bash
# collect c2c data for unixbench spawn case
perf c2c record -a -g ./spawn 10000

# collect c2c data together with instructions/cycles event
perf record -e "cpu/mem-loads,ldlat=30/P,cpu/mem-stores/P,cycles:pp,instructions:pp" -W -d --phys-data --sample-cpu -a -g ./spawn 10000
```

I want to know how severe my program has the c2c issues. For example, when I ran spawn with argument set to 100 or 10000, the total counts of the Rmt HITM might different, but what if the cycles of Rmt HITM / total cycles are the same? Absolute number sometimes not quite useful. 

--- 

## Why need perf script

_Example 2_:

```bash
# collect cycle, instructions, L1/L2 misses can see overhead for a group of functions
perf record -e "instructions:pp,cycles:pp,L1-dcache-load-misses,L1-dcache-loads,LLC-load-misses, LLC-loads" -a -g ./spawn 10000
```

I want to calculate the percentage of potential intermediate cache layer's penalty per function grouped by a particular set of processes. 

---

## What is perf script

_Example_:

```bash
perf script -s python:../scripts/cccost.py -i perf.data.spawn report
```
```python
def trace_begin():
  pass

def trace_end():
  eview = EventView(events)
  eview.print_summary()

def trace_unhandled(event_name, context, event_fields_dict, perf_sample_dict):
  print(get_dict_as_string(event_fields_dict))
  print('Sample: {'+get_dict_as_string(perf_sample_dict['sample'], ', ')+'}')
```

---

## What is perf script

```python
def process_event(param_dict):
  global events
  
  event = create_event_with_more_info(param_dict)
  if event.name not in events:
    events[event.name] = {"total":event.sample["period"], "el": [event]}
  else:
    events[event.name]["total"] += event.sample["period"]
    events[event.name]["el"].append(event)
```

---

## What is perf script

_How?_

<div class="mermaid">
    graph LR
        perf_script --> perf_tool --> process_sample_event --> scripting_ops --> process_event
</div>

---

```c
static int process_sample_event(struct perf_tool *tool,
				union perf_event *event,
				struct perf_sample *sample,
				struct evsel *evsel,
				struct machine *machine)
{
	struct perf_script *scr = container_of(tool, struct perf_script, tool);
	struct addr_location al;
	struct addr_location addr_al;
	int ret = 0;

	/* Set thread to NULL to indicate addr_al and al are not initialized */
	addr_al.thread = NULL;
	al.thread = NULL;
        ...
        ...
	if (scripting_ops) {
		struct addr_location *addr_al_ptr = NULL;

		if ((evsel->core.attr.sample_type & PERF_SAMPLE_ADDR) &&
		    sample_addr_correlates_sym(&evsel->core.attr)) {
			if (!addr_al.thread)
				thread__resolve(al.thread, &addr_al, sample);
			addr_al_ptr = &addr_al;
		}
		scripting_ops->process_event(event, sample, evsel, &al, addr_al_ptr);
	} else {
		process_event(scr, sample, evsel, &al, &addr_al, machine);
	}

out_put:
	if (al.thread)
		addr_location__put(&al);
	return ret;
}
```

---

```c
struct scripting_ops python_scripting_ops = {
	.name			= "Python",
	.dirname		= "python",
	.start_script		= python_start_script,
	.flush_script		= python_flush_script,
	.stop_script		= python_stop_script,
	.process_event		= python_process_event,
	.process_switch		= python_process_switch,
	.process_auxtrace_error	= python_process_auxtrace_error,
	.process_stat		= python_process_stat,
	.process_stat_interval	= python_process_stat_interval,
	.process_throttle	= python_process_throttle,
	.generate_script	= python_generate_script,
};
```

---

```c
static void python_process_event(union perf_event *event,
				 struct perf_sample *sample,
				 struct evsel *evsel,
				 struct addr_location *al,
				 struct addr_location *addr_al)
{
	struct tables *tables = &tables_global;

	scripting_context__update(scripting_context, event, sample, evsel, al, addr_al);

	switch (evsel->core.attr.type) {
	case PERF_TYPE_TRACEPOINT:
		python_process_tracepoint(sample, evsel, al, addr_al);
		break;
	/* Reserve for future process_hw/sw/raw APIs */
	default:
		if (tables->db_export_mode)
			db_export__sample(&tables->dbe, event, sample, evsel, al, addr_al);
		else
			python_process_general_event(sample, evsel, al, addr_al);
	}
}
```

---

```c
static void python_process_general_event(struct perf_sample *sample,
					 struct evsel *evsel,
					 struct addr_location *al,
					 struct addr_location *addr_al)
{
	PyObject *handler, *t, *dict, *callchain;
	static char handler_name[64];
	unsigned n = 0;

	snprintf(handler_name, sizeof(handler_name), "%s", "process_event");

	handler = get_handler(handler_name);
	if (!handler)
		return;

	/*
	 * Use the MAX_FIELDS to make the function expandable, though
	 * currently there is only one item for the tuple.
	 */
	t = PyTuple_New(MAX_FIELDS);
	if (!t)
		Py_FatalError("couldn't create Python tuple");

	/* ip unwinding */
	callchain = python_process_callchain(sample, evsel, al);
	dict = get_perf_sample_dict(sample, evsel, al, addr_al, callchain);

	PyTuple_SetItem(t, n++, dict);
	if (_PyTuple_Resize(&t, n) == -1)
		Py_FatalError("error resizing Python tuple");

	call_object(handler, t, handler_name);

	Py_DECREF(t);
}
```
---

## Built-in Scripts

```bash
[tli7@linux-pnp-server-27 tests]$ perf script -l
List of available trace scripts:
  failed-syscalls [comm]               system-wide failed syscalls
  rw-by-file <comm>                    r/w activity for a program, by file
  rw-by-pid                            system-wide r/w activity
  rwtop [interval]                     system-wide r/w top
  wakeup-latency                       system-wide min/max/avg wakeup latency
  compaction-times [-h] [-u] [-p|-pv] [-t | [-m] [-fs] [-ms]] [pid|pid-range|comm-regex] display time taken by mm compaction  
  event_analyzing_sample               analyze all perf samples
  export-to-postgresql [database name] [columns] [calls] export perf data to a postgresql database
  export-to-sqlite [database name] [columns] [calls] export perf data to a sqlite3 database
  failed-syscalls-by-pid [comm]        system-wide failed syscalls, by pid
  flamegraph                           create flame graphs
  futex-contention                     futext contention measurement
  intel-pt-events                      print Intel PT Events including Power Events and PTWRITE
  mem-phys-addr                        resolve physical address samples
  net_dropmonitor                      display a table of dropped frames
  netdev-times [tx] [rx] [dev=] [debug] display a process of packet and processing time
  powerpc-hcalls
  sched-migration                      sched migration overview
  sctop [comm] [interval]              syscall top
  stackcollapse                        produce callgraphs in short form for scripting use
  syscall-counts-by-pid [comm]         system-wide syscall counts, by pid
  syscall-counts [comm]                system-wide syscall counts
```

---

```bash
[tli7@linux-pnp-server-27 tests]$ perf script record rw-by-file ls
Makefile  perf.data  perf.data.old  perf.data.spawn  spawn  spawn.c
[ perf record: Woken up 2 times to write data ]
[ perf record: Captured and wrote 0.018 MB perf.data (18 samples) ]
[tli7@linux-pnp-server-27 tests]$ perf script report rw-by-file ls
file read counts for ls:

    fd     # reads  bytes_requested
------  ----------  -----------
     3          17       15488

file write counts for ls:

    fd    # writes  bytes_written
------  ----------  -----------
     1           1          68
```

---

## Q & A