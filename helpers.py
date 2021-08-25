import xml.etree.ElementTree as ET

BASE_URL = "http://oasis.caiso.com/oasisapi/SingleZip?"
OASIS_VERSION = "1"

def url_constructor(form_data):
    """ Given dictionary of params, constructs url for CAISO request.
        Accepts: {
            queryname: "ENE_SLRS",
            tac_zone_name: 
            schedule: 
            market_run_id: "RTM",
            startdatetime: "20210818T07:00-0000"
            enddatetime: 
            } 
            
        Returns: f"{BASE_URL}?queryname=ENE_SLR&market_run_id=RTM..." 
    """

    queries = [f"{key}={form_data[key]}" for key in form_data]
    queries.append(f"version={OASIS_VERSION}")
    query_string = "&".join(queries)

    return BASE_URL + query_string


def extract_and_parse(file, fileName, include_totals): 
    """ Extracts and parses file. Returns dictionary with data.
        Returns: response = {
            header: {
                report: "ENE_SLRS",
                mkt_type: "RTM",
                UOM: "MW"
            },
            reports: {
                Caiso_totals: {
                    ISO_TOT_EXP_MW: [
                        {interval, interval_start_gmt, value},
                        {interval, interval_start_gmt, value},
                        ...
                        ],
                    ISO_TOT_GEN_MW: [
                        {interval, interval_start_gmt, value},
                        {interval, interval_start_gmt, value},
                        ...
                        ]
                }
            }
        }
    
    """

    with file.open(fileName) as my_file:
        tree = ET.parse(my_file)
        root = tree.getroot()
        uri = get_xmlns(root.tag)

        response = {}

        # parses and collects metadata into dict entry 'header'
        response['header'] = {}
        header = response['header']
        for metadata in root.iter(f'{uri}REPORT_HEADER'):
            header["REPORT"] = metadata.find(f'{uri}REPORT').text
            header['MKT_TYPE'] = metadata.find(f'{uri}MKT_TYPE').text
            header['UOM'] = metadata.find(f'{uri}UOM').text

        # parses and collects report data into dict entry 'reports'
        response['reports'] = {}
        reports = response['reports']
        for entry in root.iter(f'{uri}REPORT_DATA'): 
            resource_name = entry.find(f'{uri}RESOURCE_NAME').text

            # if caiso_totals is not to be included, skip any iteration with
            # resource name of "caiso_totals", otherwise, continue
            if not include_totals and resource_name == "Caiso_Totals": 
                continue

            data_item = entry.find(f'{uri}DATA_ITEM').text

            if (resource_name not in reports): 
                reports[resource_name] = {}

            if (data_item not in reports[resource_name]):
                reports[resource_name][data_item] = []
            
            report_data = {}
            report_data["interval_start_gmt"] = entry.find(f'{uri}INTERVAL_START_GMT').text
            report_data["interval"] = entry.find(f'{uri}INTERVAL_NUM').text
            report_data["value"] = entry.find(f'{uri}VALUE').text
            reports[resource_name][data_item].append(report_data)
    
    return response


def get_xmlns(tag): 
    """ Gets and returns xmlns from tag as string. """

    tuple = tag.partition("}")
    uri = tuple[0] + "}"
    return uri


def sort_func(response): 
    """ Sorts data by interval_num. """

    for resource_name in response["reports"]:
        for data_item in response["reports"][resource_name]: 
            response["reports"][resource_name][data_item].sort(key=_sort_criteria)

    return response


def _sort_criteria(e):
    """ Defines sorting criteria. """

    return (e['interval_start_gmt'])