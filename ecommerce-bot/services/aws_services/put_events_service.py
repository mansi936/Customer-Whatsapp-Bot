import boto3
import os
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, List, Optional
import uuid

# Load environment variables
load_dotenv()

# Configuration
AWS_REGION = os.getenv('AWS_REGION', 'ap-south-1')

# Create boto3 client for PersonalizeEvents
personalize_events = boto3.client('personalize-events', region_name=AWS_REGION)


def put_event(
    tracking_id: str,
    user_id: str,
    session_id: str,
    item_id: str,
    event_type: str,
    event_value: Optional[float] = None,
    properties: Optional[Dict] = None,
    recommendation_id: Optional[str] = None,
    impression: Optional[List[str]] = None
) -> None:
    """
    Record a single user interaction event.
    
    Args:
        tracking_id (str): The tracking ID from the event tracker
        user_id (str): The user ID
        session_id (str): The session ID
        item_id (str): The item ID the user interacted with
        event_type (str): Type of event (e.g., 'click', 'view', 'purchase')
        event_value (float, optional): Event value (e.g., rating, price)
        properties (dict, optional): Additional event properties
        recommendation_id (str, optional): ID of recommendation that led to this event
        impression (list, optional): List of item IDs shown to the user
    """
    try:
        # Build event
        event = {
            'eventId': str(uuid.uuid4()),
            'eventType': event_type,
            'itemId': item_id,
            'sentAt': datetime.now()
        }
        
        if event_value is not None:
            event['eventValue'] = event_value
            
        if properties:
            import json
            event['properties'] = json.dumps(properties)
            
        if recommendation_id:
            event['recommendationId'] = recommendation_id
            
        if impression:
            event['impression'] = impression
        
        # Send event
        personalize_events.put_events(
            trackingId=tracking_id,
            userId=user_id,
            sessionId=session_id,
            eventList=[event]
        )
        
    except Exception as e:
        raise Exception(f"Error putting event: {str(e)}")


def put_events_batch(
    tracking_id: str,
    user_id: str,
    session_id: str,
    events: List[Dict]
) -> None:
    """
    Record multiple user interaction events in a batch.
    
    Args:
        tracking_id (str): The tracking ID from the event tracker
        user_id (str): The user ID
        session_id (str): The session ID
        events (list): List of event dictionaries
    
    Each event dictionary should contain:
        - item_id (required)
        - event_type (required)
        - event_value (optional)
        - properties (optional)
        - recommendation_id (optional)
        - impression (optional)
    """
    try:
        event_list = []
        
        for event_data in events:
            event = {
                'eventId': str(uuid.uuid4()),
                'eventType': event_data['event_type'],
                'itemId': event_data['item_id'],
                'sentAt': datetime.now()
            }
            
            # Add optional fields
            if 'event_value' in event_data:
                event['eventValue'] = event_data['event_value']
                
            if 'properties' in event_data:
                import json
                event['properties'] = json.dumps(event_data['properties'])
                
            if 'recommendation_id' in event_data:
                event['recommendationId'] = event_data['recommendation_id']
                
            if 'impression' in event_data:
                event['impression'] = event_data['impression']
                
            event_list.append(event)
        
        # Send events
        personalize_events.put_events(
            trackingId=tracking_id,
            userId=user_id,
            sessionId=session_id,
            eventList=event_list
        )
        
    except Exception as e:
        raise Exception(f"Error putting events batch: {str(e)}")


if __name__ == "__main__":
    # Example usage
    print("Put Events Service")
    print("-" * 50)
    
    tracking_id = input("Enter Tracking ID: ")
    user_id = input("Enter User ID: ")
    session_id = input("Enter Session ID (or press Enter to generate): ")
    
    if not session_id:
        session_id = str(uuid.uuid4())
        print(f"Generated Session ID: {session_id}")
    
    # Example single event
    print("\nSending a single event...")
    try:
        put_event(
            tracking_id=tracking_id,
            user_id=user_id,
            session_id=session_id,
            item_id="item123",
            event_type="click",
            event_value=1.0,
            properties={"category": "electronics", "price": "299.99"}
        )
        print("✅ Event sent successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Example batch events
    print("\nSending batch events...")
    try:
        events = [
            {
                'item_id': 'item456',
                'event_type': 'view',
                'properties': {'duration': '30'}
            },
            {
                'item_id': 'item789',
                'event_type': 'purchase',
                'event_value': 49.99,
                'properties': {'quantity': '1'}
            }
        ]
        
        put_events_batch(
            tracking_id=tracking_id,
            user_id=user_id,
            session_id=session_id,
            events=events
        )
        print("✅ Batch events sent successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")