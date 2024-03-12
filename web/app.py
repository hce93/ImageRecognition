from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt
import numpy as np
import requests
from keras.applications import InceptionV3
from keras.applications.inception_v3 import preprocess_input
from keras.applications import imagenet_utils
# from tensorflow import keras
from keras.preprocessing.image import img_to_array
from PIL import Image
from io import BytesIO


app = Flask(__name__)
api = Api(app)

# load the pre trained model
pretrained_model = InceptionV3(weights="imagenet")

# initialise mongo client
client = MongoClient("mongodb://db:27017")

# create a new db and set the collection
db = client.ImageRecognition
users = db["Users"]

# function to check user alreadyexists
def user_exists(username):
    return  users.count_documents({"Username":username})!=0
        
# resource for user registration
class Register(Resource):
    def post(self):
        posted_data = request.get_json()
        username = posted_data["username"]
        password = posted_data["password"]
        
        # check if user exists
        if user_exists(username):
            retJson = {
                "status":301,
                "message":"Invalid username, user already exists"
            }
            return jsonify(retJson)
            
        # has password of user and store in the database
        hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
        users.insert_one({
            "Username":username,
            "Password":hashed_pw,
            "Tokens":4
        })
        
        retJson = {
            "status":200,
            "message":"You have successfullly registered for the API"
        }
        
        return jsonify(retJson)
    
def generate_return_dictionary(status, msg):
    retJson = {
        "status":status,
        "message":msg    
    }
    
    return retJson
    
def verify_pw(username, password):
    if not user_exists(username):
        return False
    hashed_pw = users.find({"Username":username})[0]["Password"]
    
    return bcrypt.hashpw(password.encode('utf8'), hashed_pw) == hashed_pw
        
def verify_credentials(username, password):
    if not user_exists(username):
        return generate_return_dictionary(301,"Invalid Username"), True
    
    correct_pw = verify_pw(username, password)
    if not correct_pw:
        return generate_return_dictionary(302,"Incorrect Password"), True
    
    return None, False

class Classify(Resource):
    def post(self):
        # get posted data
        posted_data = request.get_json()
        username = posted_data["username"]
        password = posted_data["password"]
        url = posted_data["url"]
        
        # verify user credentials
        retJson, error = verify_credentials(username, password)
        if error:
            return jsonify(retJson)
        
        # check if user has enough tokens
        tokens = users.find({"Username":username})[0]["Tokens"]
        if tokens<=0:
            return jsonify(generate_return_dictionary(303, "Not enough tokens"))
        
        # check if a url s provided
        if not url:
            return jsonify(({"error":"No url provided"}), 400)
        
        # load image from URL
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        
        img = img.resize((299,299))
        img_array = img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = preprocess_input(img_array)
        print(img_array)
        
        prediction = pretrained_model.predict(img_array)
        actual_prediction = imagenet_utils.decode_predictions(prediction, top=5)
        
        # create return json
        retJson = {}
        for pred in actual_prediction[0]:
            retJson[pred[1]] = float(pred[2]*100)
        
        # reduce tokens
        users.update_one({
            "Username":username
        },{
            "$set":{
                "Tokens":tokens-1
            }
        })
        
        return jsonify(retJson)
    
class Refill(Resource):
    def post(self):
        posted_data = request.get_json()
        username = posted_data["username"]
        password = posted_data["admin_pw"]
        amount = posted_data["amount"]
        
        if not user_exists(username):
            return jsonify(generate_return_dictionary(301,"Invalid Username"))
        
        correct_pw = "abc123"
        if not password == correct_pw:
            return jsonify(generate_return_dictionary(302,"Incorrect Password"))
        
        # replace current amount with the new amount
        users.update_one({
            "Username":username
        },{
            "$set":{
                "Tokens":amount
            }
        })
        
        return jsonify(generate_return_dictionary(200,"Refilled"))
    
api.add_resource(Register,'/register')
api.add_resource(Classify,'/classify')
api.add_resource(Refill,'/refill')

if __name__=='__main__':
    app.run(host="0.0.0.0")