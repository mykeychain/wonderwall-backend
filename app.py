from werkzeug.utils import redirect, send_file
from exceptions import NoContentFound
from flask import Flask, request, jsonify
from flask_cors import CORS
from models import CaisoRequest
from exceptions import NoContentFound

app = Flask(__name__)
CORS(app)

@app.errorhandler(NoContentFound)
def no_content_found(e):
    """ Error handler for NoContentFound. Returns 400 error with message. """
    return jsonify(e.to_dict()), e.status_code

@app.errorhandler(ValueError)
def value_error(e): 
    """ Error handler for invalid URL or request. """
    return jsonify(e.message), e.status_code

@app.errorhandler(500)
def server_error(e): 
    """ Catch all error handler. Returns 500 error with message. """
    return jsonify({'message': 'Internal server error'}), 500

@app.route('/api/CAISO', methods=['POST'])
def get_zip_file(): 
    """
    Gets zip file from CAISO API, extracts and parses to construct response,
    returns in JSON.
    Accepts:
        data: {
            queryname: 'ENE_SLRS',
            tac_zone_name: 'TAC_PGE',
            schedule: 'Export',
            market_run_id: 'RTM',
            startdatetime: '20210818T07:00-0000'
            enddatetime: '20210819T07:00-0000'
        }

    Returns:
        report: {
            header: {
                report: 'ENE_SLRS',
                mkt_type: 'RTM',
                UOM: 'MW'
                update_interval: 5,
            },
            reports: {
                Caiso_totals: {
                    Export: [
                        {interval, interval_start_gmt, value},
                        {interval, interval_start_gmt, value},
                        ...
                        ],
                    Generation: [
                        {interval, interval_start_gmt, value},
                        {interval, interval_start_gmt, value},
                        ...
                        ]
                    }
                }
            }
        }
    """

    caiso_request = CaisoRequest.create_new_request(request.json['data'])
    caiso_request.get_data()
    caiso_request.stream_file()
    response = caiso_request.extract_and_parse()

    return jsonify(response)

@app.route('/api/download-xml', methods=['POST'])
def download_xml(): 
    """ Gets data from CAISO and sends file for download. """

    xml_request = CaisoRequest.create_new_request(request.json['data'])
    xml_request.get_data()
    xml_request.stream_file()
    return send_file(xml_request.file, as_attachment=True)