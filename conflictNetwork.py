import numpy as np
import pandas
import re
from bokeh.plotting import figure
from bokeh.io import output_notebook, output_file, show, install_notebook_hook
from bokeh.models import ColumnDataSource, Select, LabelSet, HoverTool, DatetimeAxis, TapTool, CustomJS, BoxZoomTool, \
    PanTool, LinearColorMapper, BasicTicker, ColorBar
from bokeh.models import WheelZoomTool, UndoTool, RedoTool, ResetTool, ZoomInTool, ZoomOutTool, Axis, Text, Circle,\
    MultiLine
import nltk
import re
from nltk.stem.snowball import SnowballStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans, DBSCAN
import pprint
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from bokeh.models.widgets import DataTable, TableColumn, Div, RangeSlider, Slider, Select
from bokeh.layouts import Row, widgetbox, Column
from sklearn.manifold import MDS
from sklearn.decomposition import TruncatedSVD
from bokeh.application.handlers import FunctionHandler
from bokeh.application import Application
from bokeh.palettes import Category10
import math
from collections import Counter
import networkx as nx
from bokeh.models.graphs import from_networkx, NodesAndLinkedEdges, EdgesAndLinkedNodes
import copy
import sklearn.cluster as cluster
from bokeh.palettes import inferno
from bokeh.io import curdoc

red = "#C91E17"
green = "#17C957"
grey = "#877C77"


def getDefaultTools():
    return [BoxZoomTool(), PanTool(), WheelZoomTool(), UndoTool(), RedoTool(), ResetTool(), ZoomInTool()]


def findWholeWord(w):
    "find whole word in text"
    return re.compile(r'\b({0})\b'.format(w), flags=re.IGNORECASE).search


def appendRow(row, dataframe):
    "add row to dataframe"
    dataframeLength = len(dataframe)
    for key, value in row[1].iteritems():
        dataframe.loc[dataframeLength, key] = value


bots = ['BakBOT', 'SilviaBot', 'Chkbot']

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
previousPageLength = 0
previousEdit = -1
for index, row in data.iterrows():
    data.loc[index, 'previousEdit'] = previousEdit
    previousEdit = row['ID']
    if (row['pageLength'] == -1):
        data.loc[index, 'editDiff'] = 0
    else:
        data.loc[index, 'editDiff'] = row['pageLength'] - previousPageLength
        previousPageLength = row['pageLength']

bigEdits = data.loc[abs(data['editDiff']) > 60000]
bigEdits = bigEdits[1:]

bigEdits = bigEdits[bigEdits.user != 'BakBOT']
bigEdits.is_copy = False
for index, row in bigEdits.iterrows():
    if (row['editDiff'] < 0):
        bigEdits.loc[index, 'faction'] = 'negative'
    else:
        bigEdits.loc[index, 'faction'] = 'positive'

usernames = list(set(list(data['user'])))

smallEdits = data.loc[abs(data['editDiff']) <= 60000]
conflictRows = pandas.DataFrame(columns=list(data.columns.values))
conflictRowsUserMentions = pandas.DataFrame(columns=list(data.columns.values))
conflictRowsNoUserMentions = pandas.DataFrame(columns=list(data.columns.values))

for row in smallEdits.iterrows():
    rowAdded = False
    for user in usernames:
        if (findWholeWord(user)(row[1]['comment'])):
            appendRow(row, conflictRows)
            appendRow(row, conflictRowsUserMentions)
            rowAdded = True
            break
    if (rowAdded == False):
        if (findWholeWord("rv")(row[1]['comment']) or findWholeWord("rv.")(row[1]['comment']) or findWholeWord("undid")(
                row[1]['comment'])):
            appendRow(row, conflictRows)
            appendRow(row, conflictRowsNoUserMentions)

conflictRows = conflictRows.loc[~conflictRows['user'].isin(bots)]

ignoredIds = [785, 784, 530, 534, 488, 489, 336, 260, 80]
ignoredComments = data.loc[data['ID'].isin(ignoredIds)]
conflictRows = conflictRows.loc[~conflictRows['ID'].isin(ignoredIds)]

weights = {'revert': -3, 'accusation': -1, 'node': 10, 'vandalism': -2, 'for': 20, 'goodFaith': 3}

undidRows = pandas.DataFrame(columns=list(conflictRows.columns.values))
for row in conflictRows.iterrows():
    if (findWholeWord('undid')(row[1]['comment']) or findWholeWord('undo')(row[1]['comment'])):
        appendRow(row, undidRows)

edges = []


def addEdge(user1, user2, weight, edit=None):
    global edges
    if (user1 in bots or user2 in bots):
        return
    edgeFound = False
    for edge in edges:
        if ((edge[0] == user1 and edge[1] == user2) or (edge[0] == user2 and edge[1] == user1)):
            edge[2] += weight
            edge[3].append(edit)
            edgeFound = True
    if (not edgeFound):
        edges.append([user1, user2, weight, [edit]])


for index, row in undidRows.iterrows():
    tokens = re.split(" ", row['comment'])
    edgeAdded = False
    for token in tokens:
        for user in usernames:
            if (user.lower() in token.lower()):
                addEdge(row['user'], user, weights['revert'], undidRows.iloc[index])
                if (findWholeWord('pov')(row['comment'])):
                    addEdge(row['user'], user, weights['accusation'])
                edgeAdded = True
                break
        if (edgeAdded):
            break
    if (not edgeAdded):
        previousEdit = data.loc[data['ID'] == row['previousEdit']]
        addEdge(row['user'], previousEdit['user'].item(), weights['revert'], undidRows.iloc[index])
        if (findWholeWord('pov')(row['comment'])):
            addEdge(row['user'], previousEdit['user'].item(), weights['accusation'])

revertRows = pandas.DataFrame(columns=list(conflictRows.columns.values))
for row in conflictRows.iterrows():
    if ((findWholeWord('reverted')(row[1]['comment']) or
             findWholeWord('revert')(row[1]['comment']) or
             findWholeWord('rv')(row[1]['comment']) or
             findWholeWord('rvt')(row[1]['comment']) or
             findWholeWord('reverting')(row[1]['comment'])) and
            not findWholeWord('undid')(row[1]['comment'])):
        appendRow(row, revertRows)

for index, row in revertRows.iterrows():
    tokens = re.split(" ", row['comment'])
    revertFound = False
    toFound = False
    editsReverted = 0
    forUser = ''
    againstUser = ''
    for tokenIndex, token in enumerate(tokens):
        if (not revertFound):
            if ('revert' in token.lower() or 'rv' != token.lower()[0:2]):
                revertFound = True
            else:
                for user in usernames:
                    if (user.lower() in token.lower()):
                        againstUser = user
        else:
            if ('to' == token):
                toFound = True
            elif (re.compile("^[0-9]+$").match(token)):
                if (tokenIndex < len(tokens) - 1):
                    if ('edit' in tokens[tokenIndex + 1].lower()):
                        editsReverted = int(token)
            else:
                for user in usernames:
                    if (user.lower() in token.lower()):
                        if (toFound and forUser == ''):
                            forUser = user
                        elif (againstUser == ''):
                            againstUser = user
    if (againstUser == ''):
        if (forUser == ''):
            toEdit = data.loc[data['ID'] == (row['ID'] + 2)]
            removedEdit = data.loc[data['ID'] == (row['ID'] + 1)]
            if (findWholeWord('vandalism')(row['comment'])):
                addEdge(row['user'], removedEdit['user'].item(), weights['vandalism'])
            if (findWholeWord('pov')(row['comment']) or findWholeWord('unsourced')(row['comment'])):
                addEdge(row['user'], removedEdit['user'].item(), weights['accusation'])
            addEdge(row['user'], removedEdit['user'].item(), weights['revert'], revertRows.iloc[index])
            if (row['pageLength'] == toEdit['pageLength'].item()):
                addEdge(row['user'], toEdit['user'].item(), weights['for'], revertRows.iloc[index])
        else:
            previousCommitsByForUser = data.loc[
                (data['ID'] > row['ID']) & (data['user'] == forUser) & (data['pageLength'] == row['pageLength'])]
            previousCommitIndex = previousCommitsByForUser['ID'].min()
            commitsInBetween = data.loc[(data['ID'] > row['ID']) & (data['ID'] < previousCommitIndex)]
            for user in list(commitsInBetween['user']):
                if (findWholeWord('vandalism')(row['comment'])):
                    addEdge(row['user'], user, weights['vandalism'])
                if (findWholeWord('pov')(row['comment']) or findWholeWord('unsourced')(row['comment'])):
                    addEdge(row['user'], user, weights['accusation'])
                addEdge(row['user'], user, weights['revert'], revertRows.iloc[index])
            addEdge(row['user'], forUser, weights['for'], revertRows.iloc[index])
    elif (forUser == ''):
        if (editsReverted != 0):
            toEdit = data.loc[data['ID'] == (row['ID'] + 1 + editsReverted)]
            forUser = toEdit['user'].item()
            if (findWholeWord('vandalism')(row['comment'])):
                addEdge(row['user'], againstUser, weights['vandalism'] * editsReverted)
            if (findWholeWord('pov')(row['comment']) or findWholeWord('unsourced')(row['comment'])):
                addEdge(row['user'], againstUser, weights['accusation'] * editsReverted)
            addEdge(row['user'], againstUser, weights['revert'] * editsReverted, revertRows.iloc[index])
            addEdge(row['user'], forUser, weights['for'], revertRows.iloc[index])
        else:
            toEdit = data.loc[data['ID'] == (row['ID'] + 2)]
            if ('good faith' in row['comment']):
                addEdge(row['user'], againstUser, weights['goodFaith'])
            if (findWholeWord('vandalism')(row['comment'])):
                addEdge(row['user'], againstUser, weights['vandalism'])
            if (findWholeWord('pov')(row['comment']) or findWholeWord('unsourced')(row['comment'])):
                addEdge(row['user'], againstUser, weights['accusation'])
            addEdge(row['user'], againstUser, weights['revert'], revertRows.iloc[index])
            if (row['pageLength'] == toEdit['pageLength'].item()):
                addEdge(row['user'], toEdit['user'].item(), weights['for'], revertRows.iloc[index])
    else:
        if (editsReverted != 0):
            if (findWholeWord('vandalism')(row['comment'])):
                addEdge(row['user'], againstUser, weights['vandalism'] * editsReverted)
            if (findWholeWord('pov')(row['comment']) or findWholeWord('unsourced')(row['comment'])):
                addEdge(row['user'], againstUser, weights['accusation'] * editsReverted)
            addEdge(row['user'], againstUser, weights['revert'] * editsReverted, revertRows.iloc[index])
            addEdge(row['user'], forUser, weights['for'], revertRows.iloc[index])
        else:
            if (findWholeWord('vandalism')(row['comment'])):
                addEdge(row['user'], againstUser, weights['vandalism'])
            if (findWholeWord('pov')(row['comment']) or findWholeWord('unsourced')(row['comment'])):
                addEdge(row['user'], againstUser, weights['accusation'])
            addEdge(row['user'], againstUser, weights['revert'], revertRows.iloc[index])
            addEdge(row['user'], forUser, weights['for'], revertRows.iloc[index])

revertIds = list(revertRows['ID'])
vandalismRows = pandas.DataFrame(columns=list(conflictRows.columns.values))
for row in conflictRows.iterrows():
    if (findWholeWord('vandalism')(row[1]['comment']) and row[1]['ID'] not in revertIds):
        currentRow = len(vandalismRows)
        for key, value in row[1].iteritems():
            vandalismRows.loc[currentRow, key] = value

for index, row in vandalismRows.iterrows():
    tokens = re.split(" ", row['comment'])
    for token in tokens:
        for user in usernames:
            if (user.lower() in token.lower()):
                addEdge(row['user'], user, weights['revert'] + weights['vandalism'], vandalismRows.iloc[index])

undidIds = list(undidRows['ID'])
povRows = pandas.DataFrame(columns=list(conflictRows.columns.values))
for row in conflictRows.iterrows():
    if (findWholeWord('pov')(row[1]['comment']) and row[1]['ID'] not in revertIds and row[1]['ID'] not in undidIds):
        currentRow = len(povRows)
        for key, value in row[1].iteritems():
            povRows.loc[currentRow, key] = value

for index, row in povRows.iterrows():
    tokens = re.split(" ", row['comment'])
    for token in tokens:
        for user in usernames:
            if (user.lower() in token.lower()):
                addEdge(row['user'], user, weights['revert'] + weights['accusation'], povRows.iloc[index])


def wrapText(text):
    return "<p>" + text + "</p>"


def selectUser(user, dropdown):
    global graphRenderer
    entireText = ""
    entireText += "<h3>" + user + '</h3>'
    for edge in edges:
        if (user == edge[1] or user == edge[0]):
            if (user == edge[1]):
                otherUser = edge[0]
            else:
                otherUser = edge[1]
            entireText += "<div style='border:1px solid grey; padding:10px'>"
            entireText += wrapText("<b>Relationship with " + otherUser + ": </b>")
            entireText += wrapText("<b>Weight:</b> " + str(edge[2]))
            for edit in edge[3]:
                if (type(edit) != type(None)):
                    entireText += wrapText("<b>user:</b> " + edit['user'])
                    tokens = re.split(" ", edit['comment'])
                    comment = ""
                    for token in tokens:
                        tokenAdded = False
                        for username in usernames:
                            if (username in token):
                                comment += " <span style='background:#9EFFB7'>" + token + "</span>"
                                tokenAdded = True
                                break
                        if (not tokenAdded):
                            if (token.lower() == 'undid' or
                                        token.lower() == 'undo' or
                                        token.lower() == 'reverted' or
                                        token.lower() == 'revert' or
                                        token.lower() == 'rv' or
                                        token.lower() == 'rvt' or
                                        token.lower() == 'reverting'):
                                comment += " <span style='background:#FFD6E1'>" + token + "</span>"
                            elif (token.lower() == 'vandalism' or token.lower() == 'pov'):
                                comment += " <span style='background:#B0E8FF'>" + token + "</span>"
                            else:
                                comment += " " + token

                    entireText += wrapText("<b>comment:</b> " + comment)
            entireText += "</div>"
        div.text = entireText
    if (dropdown):
        userIndex = graphRenderer.node_renderer.data_source.data['index'].index(user)
        edgeIndices = []
        for index, username in enumerate(graphRenderer.edge_renderer.data_source.data['start']):
            if (username == user):
                edgeIndices.append(index)
        for index, username in enumerate(graphRenderer.edge_renderer.data_source.data['end']):
            if (username == user):
                edgeIndices.append(index)

        edgeIndices.sort()
        edgeObject = {}
        for edgeIndex in edgeIndices:
            edgeObject[str(edgeIndex)] = [0]

        if (len(graphRenderer.node_renderer.data_source.selected['1d']['indices']) == 0 or
                    graphRenderer.node_renderer.data_source.selected['1d']['indices'][0] != userIndex):
            graphRenderer.edge_renderer.data_source.selected['0d'] = {'glyph': None, 'get_view': {}, 'indices': []}
            graphRenderer.edge_renderer.data_source.selected['1d']['indices'] = []
            graphRenderer.edge_renderer.data_source.selected['2d']['indices'] = edgeObject

            graphRenderer.node_renderer.data_source.selected['1d']['indices'] = [userIndex]
            copy.copy(graphRenderer.edge_renderer.data_source.selected)
            copy.copy(graphRenderer.node_renderer.data_source.selected)  # triggers change for some reason
    else:
        if (userDropdown.value != user):
            userDropdown.value = user

def userDropdownCallback(attr, old, new):
    selectUser(userDropdown.value, True)

def update(attr, old, new):
    global graphRenderer
    selectedIndex = new['1d']['indices']
    if len(selectedIndex) != 0:
        user = graphRenderer.node_renderer.data_source.data['index'][selectedIndex[0]]
        selectUser(user, False)
    else:
        layout.children[1].children[1] = Div(text="", width=400, height=100)


graph = nx.Graph()
fill_color = []
fill_number = []
size = []
users = list(bigEdits['user'])
for edge in edges:
    users.append(edge[0])
    users.append(edge[1])

users = list(set(users))
dropdownUsers = pandas.DataFrame(columns=['user', 'conflicts'])
for user in users:
    if user in bots:
        continue
    graph.add_node(user)
    conflict_edits = 0
    for edge in edges:
        if user == edge[0] or user == edge[1]:
            conflict_edits += len(edge[3])
    fill_number.append(conflict_edits)
    dropdownUsers.loc[len(dropdownUsers)] = [user, conflict_edits]

fill_color_min = min(fill_number)
for number in fill_number:
    number -= fill_color_min

palette_number = max(fill_number)

for number in fill_number:
    fill_color.append(inferno(palette_number+1)[palette_number - number])



prevUser = 'none'
for row in bigEdits.iterrows():
    if row[1]['faction'] == 'positive':
        graph.add_edge(row[1]['user'], prevUser, weight=weights['revert'])
    prevUser = row[1]['user']

for edge in edges:
    graph.add_edge(edge[0], edge[1], weight=edge[2])

hover = HoverTool(tooltips=[("User", "@index")])
plot = figure(title="Wiki Edits Network with 'Undid' edits", x_range=(-5, 5), y_range=(-5, 5),
              tools=[hover, TapTool()] + getDefaultTools())
graphRenderer = from_networkx(graph, nx.spring_layout, scale=4, iterations=2000)
graphRenderer.node_renderer.data_source.data['fill_color'] = fill_color
graphRenderer.node_renderer.glyph = Circle(size=10, fill_color='fill_color', line_color='fill_color', fill_alpha=0.9,
                                           line_alpha=0.9)

graphRenderer.edge_renderer.glyph = MultiLine(line_color="#CCCCCC", line_alpha=0.8, line_width=1)
graphRenderer.edge_renderer.selection_glyph = MultiLine(line_color="black", line_alpha=1, line_width=1)
graphRenderer.node_renderer.data_source.on_change('selected', update)
graphRenderer.selection_policy = NodesAndLinkedEdges()
color_palette = inferno(palette_number+1)
color_palette.reverse()
color_mapper = LinearColorMapper(palette=color_palette, low=0, high=palette_number)
color_bar = ColorBar(color_mapper=color_mapper, ticker=BasicTicker(desired_num_ticks=5),
                     border_line_color=None, location=(0, 0))
plot.add_layout(color_bar, 'left')
plot.renderers.append(graphRenderer)

div = Div(text="", width=400, height=100)

dropdownUsers = dropdownUsers.sort_values(by='conflicts', ascending=False)

userDropdown = Select(title='select user', options=list(dropdownUsers['user']))
userDropdown.on_change('value', userDropdownCallback)

curdoc().add_root(Column(userDropdown,Row(plot,div)))
