from flask import Flask, request, jsonify
from flask_cors import CORS
from models import CaisoRequest

app = Flask(__name__)
CORS(app)


@app.route('/api/CAISO', methods=['POST'])
def get_zip_file(): 
    """ Gets zip file from CAISO API. """

    caiso_request = CaisoRequest.create_new_request(request.json['data'])
    caiso_request.get_data()
    caiso_request.stream_file()
    response = caiso_request.extract_and_parse()

    return jsonify(response)