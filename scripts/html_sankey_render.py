from typing import List

from call_graph_defs import *

class GraphFileHtmlSankeyRender(object):

  html_header = """
  <html>                                                                                     
    <body>                                                                                   
    <script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>  

    <div id="sankey_multiple" style="width: 900px; height: 300px;"></div>                    

    <script type="text/javascript">
      google.charts.load("current", {packages:["sankey"]});
      google.charts.setOnLoadCallback(drawChart);
      function drawChart() {
        var data = new google.visualization.DataTable();
        data.addColumn('string', 'From');
        data.addColumn('string', 'To');
        data.addColumn('number', 'Weight');
        data.addRows([
  """

  html_footer = """
    ]);

      // Set chart options
      var options = {
        width: 2048,
        height: 1024,
        sankey: {
          node: {
            label: {
              fontSize: 12
            }
          }
        },
      };

      // Instantiate and draw our chart, passing in some options.
      var chart = new google.visualization.Sankey(document.getElementById('sankey_multiple'));
      chart.draw(data, options);
    }
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

    self.generate_callee_row(graph.root)
    self.generate_caller_row(graph.root)  

    self.graph_write_html_footer()
    self.file.close()

  def graph_write_html_header(self):
    self.file.write(GraphFileHtmlSankeyRender.html_header)

  def graph_write_html_footer(self):
    self.file.write(GraphFileHtmlSankeyRender.html_footer)

  def get_available_dst_symbol(self, symbol: str):
    dst_symbol = symbol
    while dst_symbol in self.sources:
      dst_symbol = dst_symbol + "~"
    
    return dst_symbol

  def generate_one_row(self, source: CallGraphNode, target: CallGraphNode, weight: int):
    src_symbol = source.symbol
    dst_symbol = target.symbol

    if src_symbol not in self.sources:
      self.sources.append(src_symbol)

    dst_symbol = self.get_available_dst_symbol(dst_symbol)
    target.symbol = dst_symbol

    self.file.write(f"        ['{src_symbol}', '{dst_symbol}', {weight}],\n")

  def generate_callee_row(self, root: CallGraphNode):
    callees = root.callees

    for item in callees:
      if root.cycles / item.cycles > 1000:
         continue
      self.generate_one_row(item, root, item.cycles)
      self.generate_callee_row(item)
      self.sources.clear()

  def generate_caller_row(self, root: CallGraphNode):
    callers = root.callers

    for item in callers:
      if root.cycles / item.cycles > 1000:
        continue
      self.generate_one_row(root, item, item.cycles)
      self.generate_caller_row(item)
      self.sources.clear()
