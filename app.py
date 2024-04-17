import json
from datetime import datetime
import os
from flask import Flask, render_template, request
from azure.storage.blob import BlobServiceClient
import azure.cosmos.cosmos_client as cosmos_client
import azure.cosmos.exceptions as exceptions
import uuid

a = 1

app = Flask(__name__)
UPLOAD_FOLDER ='./static/images'
CONN_KEY= os.getenv('APPSETTING_CONN_KEY')
storage_account = os.getenv('APPSETTING_STORAGE_ACCOUNT')
images_container = "images"

COSMOS_URL = os.getenv('APPSETTING_COSMOS_URL')
MasterKey = os.getenv('APPSETTING_MasterKey')
DATABASE_ID='lab5messagesdb'
CONTAINER_ID='lab5messages'

blob_service_client = BlobServiceClient(account_url="https://"+storage_account+".blob.core.windows.net/",credential=CONN_KEY)
cosmos_db_client = cosmos_client.CosmosClient(COSMOS_URL, {'masterKey': MasterKey})
cosmos_db = cosmos_db_client.get_database_client(DATABASE_ID)
container = cosmos_db.get_container_client(CONTAINER_ID)

def read_messages_from_file():
    """ Read all messages from a JSON file"""
    with open('data.json') as messages_file:
        return json.load(messages_file)

def read_cosmos():

    messages = list(container.read_all_items(max_item_count=10))
    return {'messages': messages}


def insert_cosmos(img_path, content):

    data = read_messages_from_file()
    new_message = {
        'content': content,
        'img_path': img_path,
        'id': str(uuid.uuid4()),
        'timestamp': datetime.now().isoformat(" ", "seconds")
    }

    data['messages'].append(new_message)

    with open('data.json', mode='w') as messages_file:
        json.dump(data, messages_file)

    try:
        container.create_item(body=new_message)
    except exceptions.CosmosResourceExistsError:
        print("Resource already exists, didn't insert message.")

def insert_blob(img_path):
    filename = (img_path).split('/')[-1]
    blob_client = blob_service_client.get_blob_client(container=images_container, blob=filename)
    with open(file=img_path, mode="rb") as data:
        blob_client.upload_blob(data,overwrite=True)


def append_message_to_file(img_path, content):
    """ Read the contents of JSON file, add this message to it's contents, then write it back to disk. """
    data = read_messages_from_file()
    new_message = {
        'content': content,
        'img_path': img_path,
        'timestamp': datetime.now().isoformat(" ", "seconds")
    }

    data['messages'].append(new_message)

    with open('data.json', mode='w') as messages_file:
        json.dump(data, messages_file)




# The Flask route, defining the main behaviour of the webserver:
@app.route("/handle_message", methods=['POST'])
def handleMessage():
    new_message = request.form['msg']
    img_path = ""


    if new_message:
       print("message", new_message)
       if('file' in request.files and request.files['file']):
          print("file here")
          image = request.files['file']
          img_path = os.path.join(UPLOAD_FOLDER, image.filename)
          image.save(img_path)
          insert_blob(img_path)

       blob_path = 'https://'+storage_account+'.blob.core.windows.net/'+images_container+'/'+image.filename
       insert_cosmos(blob_path, new_message)

    return render_template('handle_message.html', message=new_message)



# The Flask route, defining the main behaviour of the webserver:
@app.route("/", methods=['GET'])
def htmlForm():

    data = read_cosmos()

    # Return a Jinja HTML template, passing the messages as an argument to the template:
    return render_template('home.html', messages=data['messages'])

