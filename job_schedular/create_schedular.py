from flask import Flask, request, jsonify
from azure_connector import batch_client
import azure.batch.models as batchmodels
from flask_restx import Api, Resource, fields
import logging
import uuid

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
api = Api(app, version='1.0', doc='/swagger', title='Job Scheduler API', description='A simple job scheduler API')

# A namespace for job management
jobmanager = api.namespace('jobs', description='Job operations')

job_schedule_model = api.model('JobSchedule', {
    'do_not_run_until': fields.String(required=True, description='Do not run until time in ISO 8601 format'),
    'do_not_run_after': fields.String(required=True, description='Do not run after time in ISO 8601 format'),
    'cron_expression': fields.String(required=True, description='Cron expression for scheduling')
})

# Define request headers
tenant_id_header = api.parser().add_argument('tenant-id', location='headers', required=True, help='The tenant ID')
app_id_header = api.parser().add_argument('app-id', location='headers', required=True, help='The application ID')

def parse_day_of_week(day_of_week):
    days = {
        '0': 'Sunday',
        '1': 'Monday',
        '2': 'Tuesday',
        '3': 'Wednesday',
        '4': 'Thursday',
        '5': 'Friday',
        '6': 'Saturday',
        '7': 'Sunday'
    }
    day_list = day_of_week.split(',')
    return [days.get(day, day) for day in day_list]

def extract_recurrence_interval(part):
    if '*/' in part:
        return int(part.split('*/')[1])
    return None

def parse_cron_expression(expression):
    parts = expression.split()
    if len(parts) != 5:
        raise ValueError("Cron expression must have 5 parts")
    
    parsed_expression = {
        'minute': parts[0],
        'hour': parts[1],
        'day_of_month': parts[2],
        'month': parts[3],
        'day_of_week': parse_day_of_week(parts[4]),
    }
    
    return parsed_expression

@jobmanager.route('/info')
class GetTenantInfo(Resource):
    @api.doc(headers={
        'tenant-id': 'The tenant ID',
        'app-id': 'The application ID'
    })
    @api.expect(tenant_id_header, app_id_header)
    def post(self):
        tenant_id = request.headers.get('tenant-id')
        app_id = request.headers.get('app-id')
        if not tenant_id or not app_id:
            return {'message': 'Missing tenant-id or app-id in headers'}, 400
        GetTenantInfo.job_schedule_id = generate_job_schedule_id(tenant_id, app_id)
        return GetTenantInfo.job_schedule_id

# Helper function to generate job_schedule_id
def generate_job_schedule_id(tenant_id, app_id):
    return str(uuid.uuid4())  # Generate a unique ID

@jobmanager.route('/create')
class JobScheduleList(Resource):
    @jobmanager.doc('create_jobschedule')
    @jobmanager.expect(job_schedule_model, validate=True)
    def post(self):
        '''Create a new job schedule'''
        data = request.json
        logger.info('Received data: %s', data)

        # Extract and validate the fields
        job_schedule_id = GetTenantInfo.job_schedule_id
        do_not_run_until = data['do_not_run_until']
        do_not_run_after = data['do_not_run_after']
        cron_expression = data['cron_expression']

        # Parse the cron expression
        parsed_cron = parse_cron_expression(cron_expression)

        # Define the recurrence schedule
        recurrence = batchmodels.Schedule(
            do_not_run_until=do_not_run_until,
            do_not_run_after=do_not_run_after,
            recurrence_interval=None  # Recurrence interval is not used as we are using cron expression
        )
        
        # Define the job manager task
        job_manager_task = batchmodels.JobManagerTask(
            id='JobManagerTask',
            command_line='your_command_line_here',  # Placeholder
            display_name='your_display_name_here'  # Placeholder
        )

        # Define the job specification
        job_spec = batchmodels.JobSpecification(
            priority=0,  # Default priority
            pool_info=batchmodels.PoolInformation(pool_id='mypool'),
            job_manager_task=job_manager_task,
            constraints=batchmodels.JobConstraints(
                max_wall_clock_time='PT0S',
                max_task_retry_count=0
            )
        )

        # Define the job schedule
        job_schedule = batchmodels.JobScheduleAddParameter(
            id=job_schedule_id,
            schedule=recurrence,
            job_specification=job_spec,
        )

        # Add the job schedule to the Batch service
        result = batch_client.job_schedule.add(job_schedule)
        return {'message': 'Job schedule created successfully', 'job_schedule_id': job_schedule_id}, 201

    @jobmanager.doc('list_jobs')
    def get(self):
        '''List all job schedules'''
        try:
            # Retrieve the list of job schedules
            job_schedules = batch_client.job_schedule.list()
            # Format the job schedules into a list of dictionaries
            jobs = [{'job_schedule_id': job.id, 'display_name': job.display_name} for job in job_schedules]
            return jsonify({'jobs': jobs})
        except Exception as e:
            logger.error('Error listing job schedules: %s', e)
            return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
