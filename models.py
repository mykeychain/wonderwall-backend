import xml.etree.ElementTree as ET
import requests, zipfile, io

BASE_URL = "http://oasis.caiso.com/oasisapi/SingleZip?"
OASIS_VERSION = "1"

class CaisoRequest(): 
    """ Class for Caiso Request. """

    intervals = {
        "RTM": 5 * 60 * 1000,
        "DAM": 60 * 60 * 1000,
        "RTD": 5 * 60 * 1000,
    }

    def __init__(self, url, queryname): 
        """ Constructor for CaisoRequest. """

        self.url = url
        self.report_type = queryname
        self.resp = ''
        self.file = ''
        self.filename = ''


    @staticmethod
    def create_new_request(form_data): 
        """ Creates a new request. """
        
        url = CaisoRequest.url_constructor(form_data)
        return CaisoRequest(url, form_data['queryname'])


    @staticmethod
    def url_constructor(form_data): 
        """ Given dictionary of params, assigns OASIS version depending on
            queryname, constructs url for CAISO request.

        Accepts: {
            queryname: 'ENE_SLRS',
            tac_zone_name: 'TAC_PGE',
            schedule: 'Export',
            market_run_id: 'RTM',
            startdatetime: '20210818T07:00-0000'
            enddatetime: '20210819T07:00-0000'
            } 
            
        Returns: f'{BASE_URL}?queryname=ENE_SLR&market_run_id=RTM...' 
        """

        # check for basic required fields
        required_fields = ['startdatetime', 'enddatetime', 'queryname']
        if not all(field in list(form_data.keys()) for field in required_fields): 
            raise KeyError('Missing start date, end date, or query name')

        # if PRC_LMP and RTM, then replace queryname with appropriate for request
        if (form_data['queryname'] == 'PRC_LMP' 
            and form_data['market_run_id'] == 'RTM'): 
            form_data['queryname'] = 'PRC_INTVL_LMP'

        queries = [f'{key}={form_data[key]}' for key in form_data]

        if (form_data['queryname'] == 'ENE_TRANS_LOSS'): 
            queries.append(f'version=9')
        else: 
            queries.append(f'version={OASIS_VERSION}')

        query_string = '&'.join(queries)

        return BASE_URL + query_string


    def get_data(self): 
        """ Makes request to CAISO API. """

        try: 
            resp = requests.get(self.url)
            self.resp = resp
        except: 
            raise ValueError('Invalid URL received.')


    def stream_file(self): 
        """ Streams file contents. """

        self.file = zipfile.ZipFile(io.BytesIO(self.resp.content))
        self.filename = self.file.namelist()[0]
        if (self.filename == 'INVALID_REQUEST.xml'): 
            raise ValueError('Invalid response from CAISO API. Please check request and try again.')
    

    def extract_and_parse(self): 
        """ Calls appropriate function to parse based on self.report_type. """
        response = {}

        response['header'] = self._construct_header()

        # calls parser depending on report type
        if (self.report_type == 'ENE_SLRS'): 
            response['reports'] = self._parse_ENE_SLRS()
        
        if (self.report_type == 'PRC_LMP' or self.report_type == 'PRC_INTVL_LMP'): 
            response['reports'] = self._parse_PRC_LMP()

        if (self.report_type == 'ENE_TRANS_LOSS'): 
            response['reports'] = self._parse_ENE_TRANS_LOSS()

        response['reports'] = self.sort_reports_by_interval_start(response['reports'])
        return response


    def _get_xmlns(self, tag): 
        """ Gets and returns xmlns from tag as string. """

        tuple = tag.partition('}')
        uri = tuple[0] + '}'
        return uri


    def _construct_header(self): 
        """ Parses file to construct response header.
            Returns: 
                header: {
                    report: 'ENE_SLRS',
                    mkt_type: 'RTM',
                    UOM: 'MW'
                    update_interval: 300000,
                },
        """

        with self.file.open(self.filename) as my_file:
            tree = ET.parse(my_file)
            root = tree.getroot()
            uri = self._get_xmlns(root.tag)

            header = {}

            # parses and collects metadata into dict entry 'header'
            for metadata in root.iter(f'{uri}REPORT_HEADER'):
                header['REPORT'] = metadata.find(f'{uri}REPORT').text
                header['MKT_TYPE'] = metadata.find(f'{uri}MKT_TYPE').text

                # some reports (e.g. trans_loss) do not include a UOM
                uom = metadata.find(f'{uri}UOM')
                if (uom != None): 
                    header['UOM'] = uom.text

                break

            header['update_interval'] = CaisoRequest.intervals[header['MKT_TYPE']]

            return header
    

    def _parse_ENE_SLRS(self): 
        """ Extracts and parses file for System Load and Resource
            Schedules(ENE_SLRS). Replaces data item names with common names
            (e.g. TOT_GEN_MW -> Generation) Returns dictionary with data.

            Returns: reports: {
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
        """

        ENE_SLRS_aliases = {
            'ISO_TOT_EXP_MW': 'Export',
            'ISO_TOT_GEN_MW': 'Generation',
            'ISO_TOT_IMP_MW': 'Import',
            'TOT_EXP_MW': 'Export',
            'TOT_GEN_MW': 'Generation',
            'TOT_IMP_MW': 'Import',
            'TOT_LOAD_MW': 'Load',
        }

        with self.file.open(self.filename) as my_file:
            tree = ET.parse(my_file)
            root = tree.getroot()
            uri = self._get_xmlns(root.tag)

            include_totals = 'Caiso_Totals' in self.url
            reports = {}
            
            # parses and collects report data into dict entry 'reports'
            for entry in root.iter(f'{uri}REPORT_DATA'): 
                resource_name = entry.find(f'{uri}RESOURCE_NAME').text

                # if caiso_totals is not to be included, skip any iteration with
                # resource name of 'caiso_totals'
                if not include_totals and resource_name == 'Caiso_Totals': 
                    continue

                if (resource_name not in reports): 
                    reports[resource_name] = {}

                raw_data_item = entry.find(f'{uri}DATA_ITEM').text
                data_item = ENE_SLRS_aliases[raw_data_item]
                if (data_item not in reports[resource_name]):
                    reports[resource_name][data_item] = []


                
                report_data = {}
                report_data['interval_start_gmt'] = entry.find(f'{uri}INTERVAL_START_GMT').text
                report_data['interval'] = entry.find(f'{uri}INTERVAL_NUM').text
                report_data['value'] = entry.find(f'{uri}VALUE').text
                reports[resource_name][data_item].append(report_data)
        
            return reports

    def _parse_PRC_LMP(self): 
        """ Extracts and parses file. Returns dictionary with data.
        Returns: response = {
            header: {
                report: 'ENE_SLRS',
                mkt_type: 'RTM',
                UOM: 'MW'
            },
            reports: {
                0096WD_7_N001: {
                    Congestion: [
                        {interval, interval_start_gmt, value},
                        {interval, interval_start_gmt, value},
                        ...
                        ],
                    Energy: [
                        {interval, interval_start_gmt, value},
                        {interval, interval_start_gmt, value},
                        ...
                        ]
                    }
                }
            }
        """

        PRC_LMP_aliases = {
            'LMP_PRC': 'LMP',
            'LMP_CONG_PRC': 'Congestion',
            'LMP_ENE_PRC': 'Energy',
            'LMP_LOSS_PRC': 'Loss',
            'LMP_GHG_PRC': 'Greenhouse Gas'
        }


        with self.file.open(self.filename) as my_file:
            tree = ET.parse(my_file)
            root = tree.getroot()
            uri = self._get_xmlns(root.tag)

            reports = {}

            # parses and collects report data into dict entry 'reports'
            for entry in root.iter(f'{uri}REPORT_DATA'): 
                resource_name = entry.find(f'{uri}RESOURCE_NAME').text
                if (resource_name not in reports): 
                    reports[resource_name] = {}

                raw_data_item = entry.find(f'{uri}DATA_ITEM').text
                data_item = PRC_LMP_aliases[raw_data_item]
                if (data_item not in reports[resource_name]):
                    reports[resource_name][data_item] = []
                
                report_data = {}
                report_data['interval_start_gmt'] = entry.find(f'{uri}INTERVAL_START_GMT').text
                report_data['interval'] = entry.find(f'{uri}INTERVAL_NUM').text
                report_data['value'] = entry.find(f'{uri}VALUE').text
                reports[resource_name][data_item].append(report_data)
        
        return reports


    def _parse_ENE_TRANS_LOSS(self): 
        """ Extracts and parses file for System Load and Resource
            Schedules(ENE_SLRS). Replaces data item names with common names
            (e.g. TOT_GEN_MW -> Generation) Returns dictionary with data.

            Returns: reports: {
                    AZPS: {
                        LOSS_MW: [
                            {interval_start_gmt, value},
                            {interval_start_gmt, value},
                            ...
                            ],
                        LOSS_MW: [
                            {interval_start_gmt, value},
                            {interval_start_gmt, value},
                            ...
                            ]
                        }
                    }
                }
        """

        with self.file.open(self.filename) as my_file:
            tree = ET.parse(my_file)
            root = tree.getroot()
            uri = self._get_xmlns(root.tag)

            reports = {}
            
            # parses and collects report data into dict entry 'reports'
            for entry in root.iter(f'{uri}REPORT_DATA'): 
                baa_id = entry.find(f'{uri}BAA_ID').text

                if (baa_id not in reports): 
                    reports[baa_id] = {}

                data_item = entry.find(f'{uri}DATA_ITEM').text
                if (data_item not in reports[baa_id]):
                    reports[baa_id][data_item] = []


                
                report_data = {}
                report_data['interval_start_gmt'] = entry.find(f'{uri}INTERVAL_START_GMT').text
                report_data['value'] = entry.find(f'{uri}VALUE').text
                reports[baa_id][data_item].append(report_data)
        
            return reports


    def sort_reports_by_interval_start(self, reports): 
        """ Sorts data by interval_num. """

        for resource_name in reports:
            for data_item in reports[resource_name]: 
                reports[resource_name][data_item].sort(key=self._sort_criteria)

        return reports


    def _sort_criteria(self, e):
        """ Defines sorting criteria. """

        return (e['interval_start_gmt'])