import pandas
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, Select, LabelSet, HoverTool, DatetimeAxis, TapTool, CustomJS, BoxZoomTool, \
    PanTool, LinearColorMapper, BasicTicker, ColorBar, DatetimeTickFormatter, LinearAxis, Range1d
from bokeh.models import WheelZoomTool, UndoTool, RedoTool, ResetTool, ZoomInTool, ZoomOutTool, Axis, Text, Circle,\
    MultiLine
import re
from bokeh.models.widgets import DataTable, TableColumn, Div, RangeSlider, Slider, Select, CheckboxButtonGroup
from bokeh.layouts import Row, widgetbox, Column
import networkx as nx
from bokeh.models.graphs import from_networkx, NodesAndLinkedEdges, EdgesAndLinkedNodes
import copy
from bokeh.palettes import inferno
from bokeh.io import curdoc
import datetime


def getDefaultTools():
    return [BoxZoomTool(), PanTool(), WheelZoomTool(), UndoTool(), RedoTool(), ResetTool(), ZoomInTool(), TapTool()]

file = open('data/Paraiso Edits.txt', 'r', errors='ignore')
lines = file.readlines()
# remove the first line
lines = lines[3:]
data = pandas.DataFrame(columns=['ID', 'timestamp', 'user', 'minorEdit', 'pageLength', 'comment', 'entireEdit'])
id = 0
for line in lines:
    entireEdit = line
    tokens = re.split('\(|\)', line)
    timestampAndName = tokens[4]
    timestampAndName = timestampAndName.split(' ')
    name = timestampAndName[-2]
    timestamp = " ".join(timestampAndName[0:-2])
    timestamp = pandas.to_datetime(timestamp)
    m = tokens[6]
    m = True if (m == ' m ') else False
    pageLength = tokens[7].split(' ')[0]
    pageLength = pageLength.replace(',', '')
    if (pageLength.isdigit()):
        pageLength = int(pageLength)
        if (len(tokens) >= 10):
            comment = tokens[9]
        else:
            comment = ""
    else:
        pageLength = -1
        comment = tokens[7]
    id += 1
    data.loc[len(data)] = [id, timestamp, name, m, pageLength, comment, entireEdit]

data = data.sort_values('timestamp', ascending=True)
# previousPageLength = 0
# previousEdit = -1
# for index, row in data.iterrows():
#     data.loc[index, 'previousEdit'] = previousEdit
#     previousEdit = row['ID']
#     if (row['pageLength'] == -1):
#         data.loc[index, 'editDiff'] = 0
#     else:
#         data.loc[index, 'editDiff'] = row['pageLength'] - previousPageLength
#         previousPageLength = row['pageLength']


prevDate = None
previousPageLength = None
pageLengthDf = pandas.DataFrame(columns=['date', 'pageLength'])
for index, row in data.iterrows():
    if prevDate is None:
        prevDate = row['timestamp'].date()
        previousPageLength = row['pageLength']
    data.loc[index, 'time'] = row['timestamp'].time()
    data.loc[index, 'date'] = row['timestamp'].date()
    if prevDate != row['timestamp'].date():
        pageLengthDf.loc[len(pageLengthDf)] = [prevDate, previousPageLength]
    prevDate = row['timestamp'].date()
    previousPageLength = row['pageLength']

source = ColumnDataSource(data)
source2 = ColumnDataSource({'pageLength': data['pageLength'], 'timestamp': data['timestamp']})

def update(attr, old, new):
    selected_index = source.selected['1d']['indices']
    if len(selected_index):
        selected_index = selected_index[0]
        ID = source.data['ID'][selected_index]
        row = data.loc[data['ID'] == ID]
        text = ""
        text += "<div style='box-shadow:2px 2px 7px rgba(148,144,142,0.3); padding:10px; margin-left:10px;'>"
        text += "<p><b style='font-size:1.1em;'>User: </b>"+source.data['user'][selected_index]+"</p>"
        text += "<p><b style='font-size:1.1em;'>Comment: </b>" + source.data['comment'][selected_index] + "</p>"
        text += "<p><b style='font-size:1.1em;'>Date: </b>" + row['date'].item().strftime("%Y-%m-%d") + "</p>"
        text += "<p><b style='font-size:1.1em;'>Time: </b>" + row['time'].item().strftime("%H:%M:%S") + "</p>"
        text += "<p><b style='font-size:1.1em;'>Edit Size: </b>" + str(source.data['editDiff'][selected_index]) + " Bytes</p>"
        text += "</div>"
    else:
        text = ""
    div.text = text

def userDropdownCallback(attr, old, new):
    global source
    if userDropdown.value == 'All':
        tempSource = ColumnDataSource(data)
    else:
        tempData = data.loc[data['user'] == userDropdown.value]
        tempSource = ColumnDataSource(tempData)
    source.data = tempSource.data


p = figure(title="Edit Frequency", x_axis_type='datetime', y_axis_type='datetime', tools=getDefaultTools(), width=1000, toolbar_location="above")
p.xaxis.axis_label = 'Days'
p.yaxis.axis_label = 'Hour of the Day'
p.yaxis[0].formatter = DatetimeTickFormatter(hours=["%Hh"], days=["%Hh"])
p.circle(x='date', y='time', source=source, size=7, color="#FC4349", legend="Edits")
p.extra_y_ranges = {"pageLength": Range1d(start=0, end=max(list(data['pageLength'])))}
p.add_layout(LinearAxis(y_range_name="pageLength", axis_label="Page Length"), 'right')
p.right[0].formatter.use_scientific = False
p.line(x='timestamp', y='pageLength', line_color="#2C3E50", line_width=2, y_range_name="pageLength", source=source2, legend="Page Length")
p.legend.click_policy = "hide"
source.on_change('selected', update)
div = Div(text='', width=400, height=100)
contributions = data['user'].value_counts()
users = contributions.index.tolist()
users.append('All')
userDropdown = Select(title='select user', options=users, value='All')
userDropdown.on_change('value', userDropdownCallback)
curdoc().add_root(Column(userDropdown, Row(p, div)))