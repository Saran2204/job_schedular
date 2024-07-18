from flask import Flask, request, jsonify
from azure_connector import batch_client
import azure.batch.models as batchmodels
from flask_restx import Api, Resource, fields
import logging
import uuid

logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


app = Flask(__name__)
api = Api(app, version='1.0', doc='/swagger', title='Job Scheduler API', description='A simple job scheduler API')

# A namespace for job management
jobmanager= api.namespace('jobs', description='Job operations')

job_schedule_model = api.model('JobSchedule', {
    'do_not_run_until': fields.String(required=True, description='Do not run until time in ISO 8601 format'),
    'do_not_run_after': fields.String(required=True, description='Do not run after time in ISO 8601 format'),
    'timezone': fields.String(required=True, description='Timezone'),
})
# Define request headers
tenant_id_header = api.parser().add_argument('tenant-id', location='headers', required=True, help='The tenant ID')
app_id_header = api.parser().add_argument('app-id', location='headers', required=True, help='The application ID')

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
    return str(uuid.uuid4())  # Generate a unique ID"

@jobmanager.route('/create')
class JobScheduleList(Resource):
    @jobmanager.doc('create_jobschedule')
    @jobmanager.expect(job_schedule_model, validate = True)
    def post(self):
        '''Create a new job schedule'''
        data = request.json
        logger.info('Received data:', data)  
        
        # Extract and validate the fields
        job_schedule_id = GetTenantInfo.job_schedule_id
        do_not_run_until = data['do_not_run_until']
        do_not_run_after = data['do_not_run_after']
        recurrence_interval = data.get['recurrence_interval','']
        priority = data.get('priority', 0)
        max_wall_clock_time = data.get('max_wall_clock_time', 'PT0S')
        max_task_retry_count = data.get('max_task_retry_count', 0)
        job_action_message = data['job_action_message']
        timezone = data['timezone']
        job_manager_command_line = data['job_manager_command_line']

        # Define the recurrence schedule
        recurrence = batchmodels.Schedule(
            do_not_run_until=do_not_run_until,
            do_not_run_after=do_not_run_after,
            recurrence_interval=recurrence_interval
        )
        # Define the job manager task
        job_manager_task = batchmodels.JobManagerTask(
            id='JobManagerTask',
            command_line=job_manager_command_line,
            display_name=job_action_message
        )
        # Define the job specification
        job_spec = batchmodels.JobSpecification(
            priority=priority,
            pool_info=batchmodels.PoolInformation(pool_id='mypool'),
            job_manager_task=job_manager_task,
            constraints=batchmodels.JobConstraints(
                max_wall_clock_time=max_wall_clock_time,
                max_task_retry_count=max_task_retry_count
            )
        )
        # Define the job schedule
        job_schedule = batchmodels.JobScheduleAddParameter(
            id = job_schedule_id,
            schedule=recurrence,
            job_specification=job_spec,
        )
        # Add the job schedule to the Batch service
        result = batch_client.job_schedule.add(job_schedule)

    @jobmanager.doc('list_jobs')
    def get(self):
        '''List all job schedules'''
        try:
            # Retrieve the list of job schedules
            job_schedules = batch_client.job_schedule.list()
            # Format the job schedules into a list of dictionaries
            jobs = [{'job_schedule_id': job.id,
                      'display_name': job.display_name,
                      } for job in job_schedules]
            return jsonify({'jobs': jobs})  
        except Exception as e:
            logger.error('Error listing job schedules:', e)
            return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
