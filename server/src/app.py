import os
from sanic import Sanic
from sanic.response import json
from sanic_cors import CORS
from sanic_gzip import Compress
from configparser import ConfigParser
from threading import Timer
from datetime import datetime
from multiprocessing import cpu_count

from services.timeToCloseService import TimeToCloseService
from services.frequencyService import FrequencyService
from services.pinService import PinService
from services.requestCountsService import RequestCountsService
from services.requestDetailService import RequestDetailService
from services.ingress_service import ingress_service
from services.sqlIngest import DataHandler

app = Sanic(__name__)
CORS(app)
compress = Compress()


def environment_overrides():
    if os.environ.get('DB_CONNECTION_STRING', None):
        app.config['Settings']['Database']['DB_CONNECTION_STRING'] =\
            os.environ.get('DB_CONNECTION_STRING')
    if os.environ.get('PORT', None):
        app.config['Settings']['Server']['PORT'] =\
            os.environ.get('PORT')
    if os.environ.get('TOKEN', None):
        app.config['Settings']['Socrata']['TOKEN'] =\
            os.environ.get('TOKEN')


def configure_app():
    # Settings initialization
    config = ConfigParser()
    settings_file = os.path.join(os.getcwd(), 'settings.cfg')
    config.read(settings_file)
    app.config['Settings'] = config
    environment_overrides()
    app.config["STATIC_DIR"] = os.path.join(os.getcwd(), "static")
    os.makedirs(os.path.join(app.config["STATIC_DIR"], "temp"), exist_ok=True)


@app.route('/')
@compress.compress()
async def index(request):
    return json('You hit the index')


@app.route('/timetoclose', methods=["POST"])
@compress.compress()
async def timetoclose(request):
    ttc_worker = TimeToCloseService(app.config['Settings'])

    postArgs = request.json
    start = postArgs.get('startDate', None)
    end = postArgs.get('endDate', None)
    ncs = postArgs.get('ncList', [])
    requests = postArgs.get('requestTypes', [])

    data = await ttc_worker.get_ttc(startDate=start,
                                    endDate=end,
                                    ncList=ncs,
                                    requestTypes=requests)
    return json(data)


@app.route('/requestfrequency', methods=["POST"])
@compress.compress()
async def requestfrequency(request):
    freq_worker = FrequencyService(app.config['Settings'])

    postArgs = request.json
    start = postArgs.get('startDate', None)
    end = postArgs.get('endDate', None)
    ncs = postArgs.get('ncList', [])
    requests = postArgs.get('requestTypes', [])

    data = await freq_worker.get_frequency(startDate=start,
                                           endDate=end,
                                           ncList=ncs,
                                           requestTypes=requests)
    return json(data)


@app.route('/sample-data')
@compress.compress()
async def sample_route(request):
    sample_dataset = {'cool_key': ['value1', 'value2'],
                      app.config['REDACTED']: app.config['REDACTED']}
    return json(sample_dataset)


@app.route('/ingest', methods=["POST"])
@compress.compress()
async def ingest(request):
    """
    Query parameters:
        years:
            a comma-separated list of years to import.
            Ex. '/ingest?years=2015,2016,2017'
            defaults to range(2015, 2021)
        limit:
            the max number of records per year
            defaults to 2000000
        querySize:
            the number of records per request to socrata
            defaults to 50000

    Counts:
        These are the counts you can expect if you do the full ingest:

        2015: 237305
        2016: 952486
        2017: 1131558
        2018: 1210075
        2019: 1308093
        2020: 319628 (and counting)

        GET https://data.lacity.org/resource/{ID}.json?$select=count(srnumber)

    Hint:
        Run /ingest without params to get all socrata data
    """
    # parse params
    years = request.args.get('years', None)
    limit = request.args.get('limit', None)
    querySize = request.args.get('querySize', None)

    # validate params
    if years is None:
        years = range(2015, 2021)
    else:
        current_year = datetime.now().year
        allowed_years = [year for year in range(2015, current_year+1)]
        years = set([int(year) for year in years.split(',')])
        if not all(year in allowed_years for year in years):
            return json({
                'error': f"'years' param values must be one of {allowed_years}"
            })

    limit = int(limit) if limit else 2000000
    querySize = int(querySize) if querySize else 50000
    querySize = min([limit, querySize])

    # get data
    loader = DataHandler(app.config['Settings'])
    data = await loader.populateDatabase(years=years,
                                         limit=limit,
                                         querySize=querySize)
    return json(data)


@app.route('/update')
@compress.compress()
async def update(request):
    ingress_worker = ingress_service()
    return_data = ingress_worker.update()
    return json(return_data)


@app.route('/delete')
@compress.compress()
async def delete(request):
    ingress_worker = ingress_service()
    return_data = ingress_worker.delete()
    return json(return_data)


@app.route('/pins', methods=["POST"])
@compress.compress()
async def pinMap(request):
    pin_worker = PinService(app.config['Settings'])
    postArgs = request.json
    start = postArgs.get('startDate', '2015-01-01')
    end = postArgs.get('endDate', '2015-12-31 01:01:01')
    ncs = postArgs.get('ncList', ['SHERMAN OAKS NC'])
    requests = postArgs.get('requestTypes', ['Bulky Items'])

    return_data = await pin_worker.get_base_pins(startDate=start,
                                                 endDate=end,
                                                 ncList=ncs,
                                                 requestTypes=requests)
    return json(return_data)


@app.route('/requestcounts', methods=["POST"])
@compress.compress()
async def requestCounts(request):
    counts_worker = RequestCountsService(app.config['Settings'])
    postArgs = request.json
    start = postArgs.get('startDate', None)
    end = postArgs.get('endDate', None)
    ncs = postArgs.get('ncList', [])
    requests = postArgs.get('requestTypes', [])
    countFields = postArgs.get('countFields', [])

    return_data = await counts_worker.get_req_counts(startDate=start,
                                                     endDate=end,
                                                     ncList=ncs,
                                                     requestTypes=requests,
                                                     countFields=countFields)
    return json(return_data)


@app.route('/servicerequest/<srnumber>', methods=["GET"])
async def requestDetails(request, srnumber):
    detail_worker = RequestDetailService(app.config['Settings'])

    return_data = await detail_worker.get_request_detail(srnumber)
    return json(return_data)


@app.route('/test_multiple_workers')
@compress.compress()
async def test_multiple_workers(request):
    Timer(10.0, print, ["Timer Test."]).start()
    return json("Done")


if __name__ == '__main__':
    configure_app()
    worker_count = max(cpu_count()//2, 1)
    app.run(host=app.config['Settings']['Server']['HOST'],
            port=int(app.config['Settings']['Server']['PORT']),
            workers=worker_count,
            debug=app.config['Settings']['Server']['DEBUG'])
