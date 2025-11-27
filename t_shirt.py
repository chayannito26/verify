import json
import collections
with open('./registrants.json', 'r') as file:
    registrations = json.load(file)
tshirt_sizes = collections.Counter(i.get('tshirt_size') for i in registrations if i['gender'] == "Female")
print(tshirt_sizes)