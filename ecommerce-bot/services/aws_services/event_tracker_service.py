import boto3
import os
from dotenv import load_dotenv
from typing import Dict, Tuple

# Load environment variables
load_dotenv()

# Configuration
AWS_REGION = os.getenv('AWS_REGION', 'ap-south-1')

# Create boto3 client
personalize = boto3.client('personalize', region_name=AWS_REGION)


def create_event_tracker(name: str, dataset_group_arn: str) -> Tuple[str, str]:
    """
    Creates an event tracker for recording user interactions.
    
    Args:
        name (str): Name for the event tracker
        dataset_group_arn (str): ARN of the dataset group to receive event data
    
    Returns:
        Tuple[str, str]: (event_tracker_arn, tracking_id)
    """
    try:
        response = personalize.create_event_tracker(
            name=name,
            datasetGroupArn=dataset_group_arn
        )
        
        return response['eventTrackerArn'], response['trackingId']
        
    except Exception as e:
        raise Exception(f"Error creating event tracker: {str(e)}")


def get_event_tracker_status(event_tracker_arn: str) -> Dict:
    """
    Get the status of an event tracker.
    
    Args:
        event_tracker_arn (str): ARN of the event tracker
    
    Returns:
        Dict: Event tracker details including status
    """
    try:
        response = personalize.describe_event_tracker(
            eventTrackerArn=event_tracker_arn
        )
        
        return {
            'name': response['eventTracker']['name'],
            'status': response['eventTracker']['status'],
            'trackingId': response['eventTracker'].get('trackingId', ''),
            'arn': response['eventTracker']['eventTrackerArn']
        }
        
    except Exception as e:
        raise Exception(f"Error getting event tracker status: {str(e)}")


def list_event_trackers(dataset_group_arn: str = None) -> list:
    """
    List all event trackers, optionally filtered by dataset group.
    
    Args:
        dataset_group_arn (str, optional): Filter by dataset group ARN
    
    Returns:
        list: List of event trackers
    """
    try:
        params = {}
        if dataset_group_arn:
            params['datasetGroupArn'] = dataset_group_arn
            
        response = personalize.list_event_trackers(**params)
        
        return response['eventTrackers']
        
    except Exception as e:
        raise Exception(f"Error listing event trackers: {str(e)}")


if __name__ == "__main__":
    # Example usage
    print("Event Tracker Service")
    print("-" * 50)
    
    dataset_group_arn = input("Enter Dataset Group ARN: ")
    tracker_name = input("Enter Event Tracker Name: ")
    
    try:
        # Create event tracker
        event_tracker_arn, tracking_id = create_event_tracker(tracker_name, dataset_group_arn)
        
        print(f"\nEvent Tracker created successfully!")
        print(f"ARN: {event_tracker_arn}")
        print(f"Tracking ID: {tracking_id}")
        
        # Check status
        status = get_event_tracker_status(event_tracker_arn)
        print(f"\nStatus: {status['status']}")
        print("\nNote: The event tracker must be ACTIVE before using the tracking ID")
        
    except Exception as e:
        print(f"Error: {e}")