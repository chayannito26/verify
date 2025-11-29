import json
import collections
with open('./registrants.json', 'r') as file:
    registrations = json.load(file)
tshirt_sizes_female = collections.Counter(i.get('tshirt_size') for i in registrations if i['gender'] == "Female")
tshirt_sizes_male = collections.Counter(i.get('tshirt_size') for i in registrations if i['gender'] == "Male")
print("Meyeder Shirt size:")
for x,y in tshirt_sizes_female.items():
    print(f"{y} ta {x}")
print("Total shirts:", sum(tshirt_sizes_female.values()))
print("\nCheleder Genji size:")
for x,y in tshirt_sizes_male.items():
    print(f"{y} ta {x}")
print("Total t-shirts:", sum(tshirt_sizes_male.values()))