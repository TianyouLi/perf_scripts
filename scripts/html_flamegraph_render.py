from call_graph_defs import *

class GraphFileHtmlFlameGraphRender(object):

  html_header = """
    <html>                                                                                     
        <head>
            <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/d3-flame-graph@4.1.3/dist/d3-flamegraph.css">
        </head>
        <body>
            <div id="chart"></div>
            <script type="text/javascript" src="https://d3js.org/d3.v7.js"></script>
            <script type="text/javascript" src="https://cdn.jsdelivr.net/npm/d3-flame-graph@4.1.3/dist/d3-flamegraph.min.js"></script>
            <script type="text/javascript">
                var chart = flamegraph()
                            .width(2048)
                            .height(1024);
                var data = 
  """

  html_footer = """
                ;
                d3.select("#chart")
                        .datum(data)
                        .call(chart);
            </script>
        </body>
    </html>
  """

  def __init__(self, htmlfilename: str):
    self.htmlfilename = htmlfilename  
    self.sources: List[str] = []

  def render(self, graph: CallGraph):
    graphfilename = self.htmlfilename
    graphfile = open(graphfilename, "w")
    self.file = graphfile

    self.graph_write_html_header()

    self.generate_node(graph.root, 10)  

    self.graph_write_html_footer()
    self.file.close()

  def graph_write_html_header(self):
    self.file.write(GraphFileHtmlFlameGraphRender.html_header)

  def graph_write_html_footer(self):
    self.file.write(GraphFileHtmlFlameGraphRender.html_footer)

  def generate_node(self, node: CallGraphNode, level: int):
    self.file.write("  " * level + "{\n")
    
    if node.callers:
        self.file.write("  " * (level +1) + "\"children\": [\n")
        self.generate_caller(node.callers, level+2)
        self.file.write("  " * (level +1) + "],\n")

    self.file.write("  " * (level +1) + f"\"name\": \"{node.symbol}\",\n")
    self.file.write("  " * (level +1) + f"\"value\": {node.cycles}\n")
    self.file.write("  " * level +"}")

  def generate_caller(self, callers: List[CallGraphNode], level):
    if not callers:
      return

    num_of_callers = len(callers)
    for i, item in enumerate(callers):
      self.generate_node(item, level)
      if i == num_of_callers -1:
        self.file.write("  " * level + "\n")
      else:
        self.file.write("  " * level + ",\n")
    
