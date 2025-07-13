# memorial/management/commands/test_s3.py
from django.core.management.base import BaseCommand
from django.conf import settings
import boto3
from botocore.exceptions import ClientError


class Command(BaseCommand):
    help = 'Test S3 connection and configuration'

    def handle(self, *args, **kwargs):
        self.stdout.write('Testing S3 connection...\n')
        
        try:
            # Create S3 client
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )
            
            # Try to list objects in the bucket
            response = s3_client.list_objects_v2(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                MaxKeys=5
            )
            
            self.stdout.write(self.style.SUCCESS('✓ Successfully connected to S3!'))
            self.stdout.write(f'✓ Bucket: {settings.AWS_STORAGE_BUCKET_NAME}')
            self.stdout.write(f'✓ Region: {settings.AWS_S3_REGION_NAME}')
            
            # List any existing files
            if 'Contents' in response:
                self.stdout.write('\nExisting files in bucket:')
                for obj in response['Contents']:
                    self.stdout.write(f"  - {obj['Key']} ({obj['Size']} bytes)")
            else:
                self.stdout.write('\nBucket is empty')
                
            # Test upload permission
            test_key = 'test/connection-test.txt'
            try:
                s3_client.put_object(
                    Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                    Key=test_key,
                    Body=b'VMI Memorial S3 connection test successful!',
                    ContentType='text/plain'
                )
                self.stdout.write(self.style.SUCCESS(f'\n✓ Successfully uploaded test file: {test_key}'))
                
                # Clean up test file
                s3_client.delete_object(
                    Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                    Key=test_key
                )
                self.stdout.write('✓ Cleaned up test file')
                
            except ClientError as e:
                self.stdout.write(self.style.ERROR(f'\n✗ Failed to upload test file: {e}'))
                
        except ClientError as e:
            self.stdout.write(self.style.ERROR(f'✗ S3 connection failed: {e}'))
            self.stdout.write('\nPlease check:')
            self.stdout.write('  1. AWS credentials are correct')
            self.stdout.write('  2. Bucket name is correct')
            self.stdout.write('  3. IAM policy has proper permissions')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Unexpected error: {e}'))