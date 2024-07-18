import os
from dotenv import load_dotenv
from azure.batch import BatchServiceClient
from azure.batch.batch_auth import SharedKeyCredentials


load_dotenv()

# Azure Batch account details
batch_account_name = os.getenv('batch_account')
batch_account_key = os.getenv('batch_key')
batch_account_url = os.getenv('batch_url')

#Batch service client
credentials = SharedKeyCredentials(batch_account_name, batch_account_key)
batch_client = BatchServiceClient(credentials, batch_url=batch_account_url)
