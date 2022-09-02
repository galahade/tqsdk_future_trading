from pymongo import MongoClient
from pprint import pprint
from random import randint
import uuid


# logging.basicConfig(level=logging.INFO)

class Test:

    def __init__(self, config: dict):
        self._rules = config['long']
        self._mains = config['main_list']

    def get_current_month(self):
        return 10

    def get_current_year(self):
        return 22


def createData(client):
    uid = str(uuid.uuid4())
    db = client.get_database(uid)
    # db = client.uid
    # db = client.future_trade_
    names = ['Kitchen', 'Animal', 'State', 'Tastey', 'Big', 'City', 'Fish',
             'Pizza', 'Goat', 'Salty', 'Sandwich', 'Lazy', 'Fun']
    company_type = ['LLC', 'Inc', 'Company', 'Corporation']
    company_cuisine = ['Pizza', 'Bar Food', 'Fast Food', 'Italian', 'Mexican',
                       'American', 'Sushi Bar', 'Vegetarian']
    for x in range(1, 501):
        business = {
            'name': names[randint(0, (len(names)-1))] + ' ' +
            names[randint(0, (len(names)-1))] + ' ' +
            company_type[randint(0, (len(company_type)-1))],
            'rating': randint(1, 5),
            'cuisine': company_cuisine[randint(0, (len(company_cuisine)-1))]
        }
        # Step 3: Insert business object directly into MongoDB via insert_one
        result = db.reviews.insert_one(business)
        # Step 4: Print to the console the ObjectID of the new document
        print('Created {0} of 500 as {1}'.format(x, result.inserted_id))
    # Step 5: Tell us that you are done
    print('finished creating 500 business reviews')


def find5star(db):
    fivestar = db.reviews.find_one({'rating': 5})
    print(fivestar)


def count5star(db):
    fivestarcount = db.reviews.find({'rating': 5}).count()
    print(fivestarcount)


def starGroup(db):
    stargroup = db.reviews.aggregate(
        [
            {'$group':
                {'_id': "$rating",
                 'count': {'$sum': 1}
                 }
             },
            {'$sort': {'_id': 1}}
        ])
    for group in stargroup:
        pprint(group)


def updateDocument(db):
    AsingleReview = db.reviews.find_one({})
    print('A sample document:')
    pprint(AsingleReview)
    result = db.reviews.update_one({'_id': AsingleReview.get('_id')},
                                   {'$inc': {'likes': 1}})
    print('Number of documents modified: ' + str(result.modified_count))

    UpdateDocument = db.reviews.find_one({'_id': AsingleReview.get('_id')})
    print("The updated document:")
    pprint(UpdateDocument)


if __name__ == '__main__':

    client = MongoClient('mongodb://root:example@localhost:27017/')
    # db = client.admin
    # serverStatusResult = db.command("serverStatus")
    # pprint(serverStatusResult)
    db = client.uid
    # find5star(db)
    # count5star(db)
    # starGroup(db)
    updateDocument(db)
