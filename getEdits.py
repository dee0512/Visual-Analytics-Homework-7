from bs4 import BeautifulSoup
import requests

url = "https://en.wikipedia.org/w/index.php?title=2016%E2%80%9317_Kashmir_unrest&offset=20160803211638&limit=500&action=history"
response = requests.get(url)

soup = BeautifulSoup(response.content, "html.parser")

print(soup.get_text())

f = open('scrapedData3.txt','w')
f.write(soup.get_text())
f.close()