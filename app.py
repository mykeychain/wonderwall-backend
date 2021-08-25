from flask import Flask, request, jsonify
from flask_cors import CORS
import requests, zipfile, io
from helpers import url_constructor, extract_and_parse, sort_func

app = Flask(__name__)

CORS(app)


@app.route("/api/CAISO", methods=["POST"])
def get_zip_file(): 
    """ Gets zip file from CAISO API. """

    caiso_url = url_constructor(request.json["data"])
    include_totals = 'Caiso_Totals' in request.json["data"].values()
    
    # make request to CAISO
    resp = requests.get(caiso_url)

    # stream file contents and get file name
    file = zipfile.ZipFile(io.BytesIO(resp.content))
    fileName = file.namelist()[0]

    # extract and parse file
    report = extract_and_parse(file, fileName, include_totals)
    report = sort_func(report)

    return jsonify(report)