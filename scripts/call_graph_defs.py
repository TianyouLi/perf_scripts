import cxxfilt

from typing import List
from enum import Enum

class CallGraphNode(object):
  def __init__(self, symbol: str, cycles: int, level: int):
    self.symbol: str = symbol
    self.cycles: int = cycles
    self.level: int = level
    self.callers: List[CallGraphNode] = []
    self.callees: List[CallGraphNode] = []

  def __str__(self):
    if len(self.callers) > 0:
      caller_str = "\n".join([str(caller) for caller in self.callers])
    else:
      caller_str = ""
    if len(self.callees) > 0:
      callee_str = "\n".join([str(callee) for callee in self.callees])
    else:
      callee_str = ""

    return callee_str + "  " * self.level + cxxfilt.demangle(self.symbol) + ":" + str(self.cycles) + "\n" + caller_str 

  def __repr__(self):
    return str(self) 

  def find_caller(self, symbol: str) -> 'CallGraphNode':
    for node in self.callers:
      if node.symbol == symbol:
        return node
    return None
  
  def add_caller(self, symbol: str, cycles: int) -> 'CallGraphNode':
    caller = self.find_caller(symbol)
    if caller is None:
      caller = CallGraphNode(symbol, cycles, self.level +1)
      self.callers.append(caller)
    else:
      caller.cycles += cycles
    
    return caller

  def find_callee(self, symbol: str) -> 'CallGraphNode':
    for node in self.callees:
      if node.symbol == symbol:
        return node
    return None
  
  def add_callee(self, symbol: str, cycles: int) -> 'CallGraphNode':
    callee = self.find_callee(symbol)
    if callee is None:
      callee = CallGraphNode(symbol, cycles, self.level +1)
      self.callees.append(callee)
    else:
      callee.cycles += cycles
    
    return callee

class CallGraph(object):
  def __init__(self, symbol: str):
    self.symbol: str = symbol
    self.root: CallGraphNode = None
  
  def __str__(self):
    return f"Symbol: {self.symbol}\n"+ str(self.root)

  def find_symbol_index_in_callchain(self, event) -> List[int]:
    result: List[int] = []
    for index, item in enumerate(event.callchain):
      if 'sym' in item and item['sym'] is not None:
        symbol = item['sym']['name']
      else:
        symbol = hex(item['ip'])

      if symbol == self.root.symbol:
        result.append(index)
    return result

  def add_caller_nodes(self, comm, dso, callerchain: List, cycles: int):
    node: CallGraphNode = self.root
    for item in callerchain:
      if 'sym' in item and item['sym'] is not None:
        symbol = item['sym']['name']
      else:
        symbol = hex(item['ip'])
      node = node.add_caller(symbol, cycles)
    node.add_caller(comm,cycles).add_caller(dso, cycles)

  def add_callee_nodes(self, calleechain: List, cycles: int):
    node: CallGraphNode = self.root
    for item in reversed(calleechain):
      if 'sym' in item and item['sym'] is not None:
        symbol = item['sym']['name']
      else:
        symbol = hex(item['ip'])
      node = node.add_callee(symbol, cycles)  

  def create_or_update_root(self, event):
    if self.root is None:
      self.root = CallGraphNode(event.symbol, event.cycles, 0)
    else:
      self.root.cycles += event.cycles

  # Suppose A is the symbol event, generate call tree with B A B F A C D as
  # A -> B
  #   <- B <- F <- A <- C <- D
  # Usually the function B could be the interrupt hanlder, event symbol is A
  # but the callchain not start with A  
  def generate_direct_call_tree(self, event):
    self.create_or_update_root(event)

    symbol_indexes = self.find_symbol_index_in_callchain(event)
    first_index = symbol_indexes[0]

    # add callee  
    calleechain = event.callchain[0:first_index]
    self.add_callee_nodes(calleechain, event.cycles)
    # add caller
    callerchain = event.callchain[first_index+1:]
    self.add_caller_nodes(event.comm, event.dso, callerchain, event.cycles)

  # Suppose A is the symbol event, generate call tree with B A B F A C D as
  # A -> B
  #   <- B <- F
  #   <- C <- D
  def generate_merged_call_tree(self, event):
    self.create_or_update_root(event)

    symbol_indexes = self.find_symbol_index_in_callchain(event)
    if len(symbol_indexes) == 1:
      symbol_indexes.append(len(event.callchain) +1)

    prev_index = 0 
    cur_index = symbol_indexes[0]
    for i, cur_index in enumerate(symbol_indexes):
      if i < (len(symbol_indexes) -1):
        next_index = symbol_indexes[i+1]
      else:
        next_index = len(event.callchain) +1
      # add caller
      callerchain = event.callchain[cur_index+1:next_index-1]
      self.add_caller_nodes(event.comm, event.dso, callerchain, event.cycles)
      if prev_index == 0:
        # add callee
        calleechain = event.callchain[prev_index:cur_index]
        self.add_callee_nodes(calleechain, event.cycles)
      prev_index = cur_index +1

class CallGraphType(Enum):
  DIRECT = 1
  MERGED = 2
