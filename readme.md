# Wonderwall Backend

Wonderwall is a full-stack application that redesigns and updates the CAISO OASIS application. Wonderwall utilizes a React frontend and a Flask RESTful backend API. For ease of deployment, the frontend repository has been separated and can be accessed [here](https://github.com/mykeychain/wonderwall-frontend). 

The Wonderwall backend is a RESTful API that makes requests to the CAISO OASIS API and receives data as zipped XML. The backend then extracts and parses the data, returning relevant information in JSON format. 

You can view the deployed website [here](https://mikechang-wonderwall.surge.sh/).

<br>

## Setup Instructions 
1. Create a virtual environment `python -m venv venv`
2. Activate the virtual environment `source venv/bin/activate`
3. Install dependencies `pip install -r requirements.txt`
4. Start server locally `flask run`
    - The server will run on port 5000 by default
5. Clone and install the frontend repository [here](https://github.com/mykeychain/wonderwall-frontend).

<br>

## Future Directions
- Add ability to download data as XML or CSV

<br>

## Technologies Used
- [React](https://reactjs.org/) - Javascript frontend framework
- [Flask](https://flask.palletsprojects.com/en/2.0.x/) - Python backend framework
- [Apex Charts](https://apexcharts.com/) - charting library