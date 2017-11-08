#nltk.download('stopwords')

import pandas
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.corpus import stopwords


file = open('data/Paraiso Edits.txt','r', errors='ignore')
lines = file.readlines()

#remove the first line
lines = lines[3:-1]
# (cur) (last) 23:44, 15 January 2007 Alonzo (Talk | contribs) m (100,571 bytes) (?Scientific criticism of Paraiso beliefs - link)\n
data = pandas.DataFrame(columns=['timestamp','user','minorEdit','pageLength','comment','entireEdit'])

for line in lines:
        entireEdit = line
        tokens = re.split('\(|\)',line)
        timestampAndName = tokens[4]
        timestampAndName = timestampAndName.split(' ')
        name = timestampAndName[-2]
        timestamp = " ".join(timestampAndName[0:-2])
        timestamp = pandas.to_datetime(timestamp)
        m = tokens[6]
        m = True if (m==' m ') else False
        pageLength = tokens[7].split(' ')[0]
        if(len(tokens) >= 10):
            comment = tokens[9]
        else:
            comment = ""
        data.loc[len(data)]=[timestamp,name,m,pageLength,comment,entireEdit]


uniqueUsers = set(data['user'])
userMentionIndices = []
for index,row in data.iterrows():
    tokens = row['comment'].split(' ')
    for token in tokens:
        if(token in uniqueUsers):
            userMentionIndices.append(index)

userMentions = data.loc[userMentionIndices]

stopwords = stopwords.words('english') + list(uniqueUsers)
vectorizer = TfidfVectorizer(stop_words = stopwords, token_pattern = '(?![0-9]+$)[a-zA-Z0-9]{2,}$')
tfIdfMatrix = vectorizer.fit_transform(list(userMentions["comment"]))
print(vectorizer.get_feature_names())


